"""Semantic validation for the strict interactive worker protocol."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import NoReturn

from .errors import WorkerProtocolSemanticError
from .hashing import verify_content_hash
from .validate import validate_payload

_ALLOWED_AFTER: dict[str, frozenset[str]] = {
    "HELLO": frozenset({"LOAD_ARTIFACT"}),
    "LOAD_ARTIFACT": frozenset({"INIT_RUN"}),
    "INIT_RUN": frozenset({"BAR_BEGIN", "RESTORE", "FINALIZE"}),
    "BAR_BEGIN": frozenset({"INTENT_BATCH"}),
    "INTENT_BATCH": frozenset({"BROKER_EVENT_BATCH", "BAR_COMMIT"}),
    "BROKER_EVENT_BATCH": frozenset({"RECALC_REQUEST", "BAR_COMMIT"}),
    "RECALC_REQUEST": frozenset({"RECALC_RESULT"}),
    "RECALC_RESULT": frozenset({"INTENT_BATCH"}),
    "BAR_COMMIT": frozenset({"BAR_BEGIN", "CHECKPOINT", "FINALIZE"}),
    "CHECKPOINT": frozenset({"BAR_BEGIN", "RESTORE", "FINALIZE"}),
    "RESTORE": frozenset({"BAR_BEGIN", "FINALIZE"}),
    "FINALIZE": frozenset(),
    "ABORT": frozenset(),
}


def _fail(reason: str, message: str, **details: object) -> NoReturn:
    raise WorkerProtocolSemanticError(message, details={"reason": reason, **details})


def _verify_nested_hashes(kind: str, body: Mapping[str, object], index: int) -> None:
    singletons = {
        "INIT_RUN": (("execution_context", "openpine.execution_context.v1"),),
        "BAR_BEGIN": (
            ("bar", "openpine.marketdata.bar.v2"),
            ("broker_projection", "openpine.broker_projection.v1"),
        ),
    }
    for field, schema_id in singletons.get(kind, ()):
        nested = body.get(field)
        if not isinstance(nested, Mapping) or not verify_content_hash(nested, schema_id=schema_id):
            _fail(
                "NESTED_CONTENT_HASH_MISMATCH",
                "worker protocol nested content hash is invalid",
                index=index,
                field=field,
                schema_id=schema_id,
            )

    collections = {
        "INTENT_BATCH": ("intents", "openpine.intent.v2"),
        "BROKER_EVENT_BATCH": ("broker_events", "openpine.broker.v2"),
    }
    collection = collections.get(kind)
    if collection is not None:
        field, schema_id = collection
        nested_items = body.get(field)
        if isinstance(nested_items, list):
            for item_index, nested in enumerate(nested_items):
                if not isinstance(nested, Mapping) or not verify_content_hash(
                    nested, schema_id=schema_id
                ):
                    _fail(
                        "NESTED_CONTENT_HASH_MISMATCH",
                        "worker protocol nested collection content hash is invalid",
                        index=index,
                        field=field,
                        item_index=item_index,
                        schema_id=schema_id,
                    )


def validate_worker_protocol_sequence(messages: Sequence[Mapping[str, object]]) -> None:
    """Validate one complete, identity-stable worker protocol sequence.

    JSON Schema validates individual messages. This function enforces invariants that
    span messages: state transitions, monotonic sequence numbers, immutable execution
    identity, and root/body run identity.
    """

    if not messages:
        _fail("EMPTY_SEQUENCE", "worker protocol sequence is empty")

    first = messages[0]
    baseline = {
        field: first.get(field) for field in ("session_id", "run_id", "stack_id", "correlation_id")
    }
    previous_kind: str | None = None
    execution_context: Mapping[str, object] | None = None
    current_bar: dict[str, object] | None = None
    last_bar_commit_sequence: object = None
    checkpoints: dict[str, tuple[object, object]] = {}

    for index, message in enumerate(messages):
        validate_payload("openpine.worker.protocol.v2", message)
        if not verify_content_hash(message, schema_id="openpine.worker.protocol.v2"):
            _fail(
                "CONTENT_HASH_MISMATCH",
                "worker protocol content hash does not match the message",
                index=index,
            )
        sequence = message.get("sequence")
        if sequence != index:
            _fail(
                "SEQUENCE_GAP",
                "worker protocol sequence must start at zero and be contiguous",
                index=index,
                expected=index,
                actual=sequence,
            )

        for field, expected in baseline.items():
            actual = message.get(field)
            if actual != expected:
                _fail(
                    f"{field.upper()}_MISMATCH",
                    f"worker protocol {field} changed within one session",
                    index=index,
                    expected=expected,
                    actual=actual,
                )

        expected_causation = None if index == 0 else baseline["correlation_id"]
        actual_causation = message.get("causation_id")
        if actual_causation != expected_causation:
            _fail(
                "CAUSATION_ID_MISMATCH",
                "worker protocol causation identity is inconsistent",
                index=index,
                expected=expected_causation,
                actual=actual_causation,
            )

        kind = str(message["kind"])
        if previous_kind is None:
            if kind != "HELLO":
                _fail(
                    "INVALID_TRANSITION",
                    "worker protocol must begin with HELLO",
                    index=index,
                    previous=None,
                    current=kind,
                )
        elif previous_kind in {"FINALIZE", "ABORT"} or (
            kind != "ABORT" and kind not in _ALLOWED_AFTER[previous_kind]
        ):
            _fail(
                "INVALID_TRANSITION",
                "worker protocol transition is not allowed",
                index=index,
                previous=previous_kind,
                current=kind,
            )

        body = message.get("body")
        if isinstance(body, Mapping) and "run_id" in body:
            body_run_id = body.get("run_id")
            if body_run_id != baseline["run_id"]:
                _fail(
                    "BODY_RUN_ID_MISMATCH",
                    "worker body run_id differs from the admitted run",
                    index=index,
                    expected=baseline["run_id"],
                    actual=body_run_id,
                )
        if isinstance(body, Mapping):
            _verify_nested_hashes(kind, body, index)
            if kind == "INIT_RUN":
                admitted_context = body.get("execution_context")
                if isinstance(admitted_context, Mapping) and body.get(
                    "execution_context_hash"
                ) != admitted_context.get("content_hash"):
                    _fail(
                        "EXECUTION_CONTEXT_HASH_MISMATCH",
                        "INIT_RUN execution_context_hash does not identify its payload",
                        index=index,
                    )
                if isinstance(admitted_context, Mapping):
                    expected_context_identity = {
                        "run_id": baseline["run_id"],
                        "session_id": baseline["session_id"],
                        "stack_manifest_hash": baseline["stack_id"],
                    }
                    for field, expected in expected_context_identity.items():
                        if admitted_context.get(field) != expected:
                            _fail(
                                "EXECUTION_CONTEXT_IDENTITY_MISMATCH",
                                "INIT_RUN execution context differs from the admitted session",
                                index=index,
                                field=field,
                                expected=expected,
                                actual=admitted_context.get(field),
                            )
                    execution_context = admitted_context
            elif kind == "BAR_BEGIN":
                bar = body.get("bar")
                projection = body.get("broker_projection")
                if isinstance(bar, Mapping) and body.get("bar_hash") != bar.get("bar_content_hash"):
                    _fail(
                        "BAR_HASH_MISMATCH",
                        "BAR_BEGIN bar_hash does not identify its canonical bar",
                        index=index,
                    )
                current_bar = {
                    "bar_index": body.get("bar_index"),
                    "bar_open_time_utc_ms": body.get("bar_open_time_utc_ms"),
                    "recalc_iteration": body.get("recalc_iteration"),
                }
                if isinstance(bar, Mapping):
                    bar_expectations = {
                        "series_id": execution_context.get("series_id")
                        if execution_context is not None
                        else None,
                        "instrument_id": execution_context.get("instrument_id")
                        if execution_context is not None
                        else None,
                        "timeframe": execution_context.get("timeframe")
                        if execution_context is not None
                        else None,
                        "open_time_utc_ms": current_bar["bar_open_time_utc_ms"],
                    }
                    for field, expected in bar_expectations.items():
                        if bar.get(field) != expected:
                            _fail(
                                "BAR_IDENTITY_MISMATCH",
                                "BAR_BEGIN canonical bar differs from the execution context",
                                index=index,
                                field=field,
                                expected=expected,
                                actual=bar.get(field),
                            )
                if isinstance(projection, Mapping):
                    projection_expectations = {
                        "run_id": baseline["run_id"],
                        "series_id": execution_context.get("series_id")
                        if execution_context is not None
                        else None,
                        "instrument_id": execution_context.get("instrument_id")
                        if execution_context is not None
                        else None,
                        "bar_index": current_bar["bar_index"],
                        "bar_open_time_utc_ms": current_bar["bar_open_time_utc_ms"],
                        "recalc_iteration": current_bar["recalc_iteration"],
                    }
                    for field, expected in projection_expectations.items():
                        if projection.get(field) != expected:
                            _fail(
                                "PROJECTION_IDENTITY_MISMATCH",
                                "BAR_BEGIN broker projection differs from the current callback",
                                index=index,
                                field=field,
                                expected=expected,
                                actual=projection.get(field),
                            )
            elif kind in {"INTENT_BATCH", "BROKER_EVENT_BATCH", "RECALC_RESULT", "BAR_COMMIT"}:
                if current_bar is None or any(
                    body.get(field) != current_bar[field]
                    for field in ("bar_index", "recalc_iteration")
                ):
                    _fail(
                        "BAR_IDENTITY_MISMATCH",
                        "worker message differs from the current bar/recalculation identity",
                        index=index,
                    )
                if kind == "INTENT_BATCH" and execution_context is not None:
                    intents = body.get("intents")
                    if isinstance(intents, list):
                        for item_index, intent in enumerate(intents):
                            if not isinstance(intent, Mapping):
                                continue
                            intent_expectations = {
                                "run_id": baseline["run_id"],
                                "strategy_id": execution_context.get("strategy_id"),
                                "series_id": execution_context.get("series_id"),
                                "instrument_id": execution_context.get("instrument_id"),
                                "timeframe": execution_context.get("timeframe"),
                                "semantic_profile": execution_context.get("semantic_profile"),
                                "bar_index": current_bar["bar_index"],
                                "bar_open_time_utc_ms": current_bar["bar_open_time_utc_ms"],
                                "recalc_iteration": current_bar["recalc_iteration"],
                            }
                            for field, expected in intent_expectations.items():
                                if intent.get(field) != expected:
                                    _fail(
                                        "INTENT_IDENTITY_MISMATCH",
                                        "intent differs from the admitted execution callback",
                                        index=index,
                                        item_index=item_index,
                                        field=field,
                                        expected=expected,
                                        actual=intent.get(field),
                                    )
                if kind == "BAR_COMMIT":
                    last_bar_commit_sequence = sequence
            elif kind == "RECALC_REQUEST":
                if current_bar is None:
                    _fail(
                        "BAR_IDENTITY_MISMATCH",
                        "RECALC_REQUEST has no active bar",
                        index=index,
                    )
                current_recalc = current_bar["recalc_iteration"]
                if not isinstance(current_recalc, int):
                    _fail(
                        "BAR_IDENTITY_MISMATCH",
                        "current recalculation identity is not an integer",
                        index=index,
                    )
                expected_recalc = current_recalc + 1
                if (
                    body.get("bar_index") != current_bar["bar_index"]
                    or body.get("recalc_iteration") != expected_recalc
                ):
                    _fail(
                        "BAR_IDENTITY_MISMATCH",
                        "RECALC_REQUEST does not advance the current bar exactly once",
                        index=index,
                    )
                if body.get("cause_sequence") != index - 1:
                    _fail(
                        "CAUSE_SEQUENCE_MISMATCH",
                        "RECALC_REQUEST cause_sequence must identify the preceding broker batch",
                        index=index,
                        expected=index - 1,
                        actual=body.get("cause_sequence"),
                    )
                current_bar["recalc_iteration"] = expected_recalc
            elif kind == "CHECKPOINT":
                if body.get("committed_sequence") != last_bar_commit_sequence:
                    _fail(
                        "CHECKPOINT_COMMIT_MISMATCH",
                        "checkpoint must bind the most recent BAR_COMMIT sequence",
                        index=index,
                        expected=last_bar_commit_sequence,
                        actual=body.get("committed_sequence"),
                    )
                checkpoint_id = body.get("checkpoint_id")
                if isinstance(checkpoint_id, str):
                    checkpoints[checkpoint_id] = (
                        body.get("checkpoint_hash"),
                        body.get("committed_sequence"),
                    )
            elif kind == "RESTORE":
                checkpoint_id = body.get("checkpoint_id")
                known_checkpoint = (
                    checkpoints.get(checkpoint_id) if isinstance(checkpoint_id, str) else None
                )
                if known_checkpoint is not None and known_checkpoint != (
                    body.get("checkpoint_hash"),
                    body.get("committed_sequence"),
                ):
                    _fail(
                        "RESTORE_CHECKPOINT_MISMATCH",
                        "RESTORE differs from its session checkpoint identity",
                        index=index,
                    )
            elif kind == "FINALIZE" and body.get("final_sequence") != index - 1:
                _fail(
                    "FINAL_SEQUENCE_MISMATCH",
                    "FINALIZE final_sequence must identify the preceding message",
                    index=index,
                    expected=index - 1,
                    actual=body.get("final_sequence"),
                )

        previous_kind = kind

    if previous_kind not in {"FINALIZE", "ABORT"}:
        _fail(
            "TRUNCATED_SEQUENCE",
            "worker protocol sequence did not reach FINALIZE or ABORT",
            final_kind=previous_kind,
        )
