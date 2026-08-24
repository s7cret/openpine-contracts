"""Semantic validation for the strict interactive worker protocol."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import NoReturn, cast

from .errors import WorkerProtocolSemanticError
from .hashing import content_hash, verify_content_hash
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

_KIND_ROLES: dict[str, frozenset[str]] = {
    "HELLO": frozenset({"worker"}),
    "LOAD_ARTIFACT": frozenset({"parent"}),
    "INIT_RUN": frozenset({"parent"}),
    "BAR_BEGIN": frozenset({"parent"}),
    "INTENT_BATCH": frozenset({"worker"}),
    "BROKER_EVENT_BATCH": frozenset({"engine"}),
    "RECALC_REQUEST": frozenset({"engine"}),
    "RECALC_RESULT": frozenset({"worker"}),
    "BAR_COMMIT": frozenset({"engine"}),
    "CHECKPOINT": frozenset({"parent"}),
    "RESTORE": frozenset({"parent"}),
    "FINALIZE": frozenset({"parent"}),
    "ABORT": frozenset({"parent", "worker", "engine"}),
}
_KIND_COMPONENT = {
    "HELLO": "openpine",
    "LOAD_ARTIFACT": "openpine",
    "INIT_RUN": "openpine",
    "BAR_BEGIN": "openpine",
    "INTENT_BATCH": "pinelib",
    "BROKER_EVENT_BATCH": "backtest_engine",
    "RECALC_REQUEST": "backtest_engine",
    "RECALC_RESULT": "pinelib",
    "BAR_COMMIT": "backtest_engine",
    "CHECKPOINT": "openpine",
    "RESTORE": "openpine",
    "FINALIZE": "openpine",
}


def aggregate_batch_hash(
    items: Sequence[Mapping[str, object]], *, batch_kind: str, item_schema_id: str
) -> str:
    """Hash an ordered batch by each item's verified semantic content identity."""

    item_content_hashes: list[str] = []
    for item_index, item in enumerate(items):
        if item.get("schema_id") != item_schema_id or not verify_content_hash(
            item, schema_id=item_schema_id
        ):
            raise ValueError(f"batch item {item_index} is not a verified {item_schema_id} payload")
        item_content_hashes.append(cast(str, item["content_hash"]))

    return content_hash(
        {
            "domain": "openpine.worker.aggregate-batch.v1",
            "batch_kind": batch_kind,
            "item_schema_id": item_schema_id,
            "ordered_item_content_hashes": item_content_hashes,
        },
        schema_id="openpine.worker.batch.v1",
    )


def _fail(reason: str, message: str, **details: object) -> NoReturn:
    raise WorkerProtocolSemanticError(message, details={"reason": reason, **details})


def _verify_nested_hashes(kind: str, body: Mapping[str, object], index: int) -> None:
    singletons = {
        "INIT_RUN": (("execution_context", "openpine.execution_context.v1"),),
        "BAR_BEGIN": (
            ("bar", "openpine.marketdata.bar.v2"),
            ("broker_projection", "openpine.broker_projection.v1"),
        ),
        "RECALC_REQUEST": (("broker_projection", "openpine.broker_projection.v1"),),
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


def _validate_checkpoint_proof(
    proof: Mapping[str, object],
    *,
    execution_context: Mapping[str, object] | None,
    index: int,
) -> None:
    if not verify_content_hash(proof, schema_id="openpine.checkpoint.proof.v1"):
        _fail(
            "CHECKPOINT_PROOF_CONTENT_HASH_MISMATCH",
            "external checkpoint proof content hash is invalid",
            index=index,
        )
    if execution_context is not None:
        _validate_component_provenance(
            proof,
            execution_context=execution_context,
            component="openpine",
            reason="CHECKPOINT_PROOF_PROVENANCE_MISMATCH",
            message="external checkpoint proof provenance differs from the admitted stack",
            index=index,
        )


def _semver_from_wheel_version(value: object) -> object:
    if not isinstance(value, str) or "rc" not in value or "-rc." in value:
        return value
    base, marker, rc = value.partition("rc")
    if marker and base and rc.isdigit():
        return f"{base}-rc.{rc}"
    return value


def _component_identity(
    execution_context: Mapping[str, object], component: str
) -> tuple[object, object]:
    commits = execution_context.get("producer_commits")
    expected_commit = commits.get(component) if isinstance(commits, Mapping) else None
    expected_version: object = None
    wheels = execution_context.get("wheel_identities")
    if isinstance(wheels, list):
        for wheel in wheels:
            if isinstance(wheel, Mapping) and wheel.get("name") == component:
                expected_version = _semver_from_wheel_version(wheel.get("version"))
                break
    return expected_version, expected_commit


def _validate_component_provenance(
    payload: Mapping[str, object],
    *,
    execution_context: Mapping[str, object],
    component: str,
    reason: str,
    message: str,
    index: int,
    item_index: int | None = None,
) -> None:
    expected_version, expected_commit = _component_identity(execution_context, component)
    expectations = {
        "producer": component,
        "producer_version": expected_version,
        "producer_commit": expected_commit,
        "stack_id": execution_context.get("stack_manifest_hash"),
    }
    for field, expected in expectations.items():
        actual = payload.get(field)
        if expected is None or actual != expected:
            details: dict[str, object] = {
                "index": index,
                "field": field,
                "expected": expected,
                "actual": actual,
            }
            if item_index is not None:
                details["item_index"] = item_index
            _fail(reason, message, **details)


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
        field: first.get(field)
        for field in (
            "session_id",
            "run_id",
            "stack_id",
            "correlation_id",
        )
    }
    admitted_execution_context: Mapping[str, object] | None = None
    for candidate in messages:
        if candidate.get("kind") != "INIT_RUN":
            continue
        candidate_body = candidate.get("body")
        if isinstance(candidate_body, Mapping):
            candidate_context = candidate_body.get("execution_context")
            if isinstance(candidate_context, Mapping):
                admitted_execution_context = candidate_context
                break
    previous_kind: str | None = None
    previous_message_id: object = None
    message_ids: set[str] = set()
    execution_context: Mapping[str, object] | None = None
    current_bar: dict[str, object] | None = None
    last_intent_batch: tuple[object, object] | None = None
    last_bar_commit: dict[str, object] | None = None
    checkpoints: dict[str, tuple[object, object, object, object, object]] = {}

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

        kind = str(message["kind"])
        message_id = message.get("message_id")
        if not isinstance(message_id, str) or message_id in message_ids:
            _fail(
                "MESSAGE_ID_INVALID",
                "worker protocol message_id must be unique and nonempty",
                index=index,
                actual=message_id,
            )
        message_ids.add(message_id)

        sender_role = message.get("sender_role")
        allowed_roles = _KIND_ROLES[kind]
        if sender_role not in allowed_roles:
            _fail(
                "SENDER_ROLE_MISMATCH",
                "worker protocol kind was sent by the wrong role",
                index=index,
                expected=sorted(allowed_roles),
                actual=sender_role,
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

        if admitted_execution_context is not None:
            if kind == "ABORT":
                component = "backtest_engine" if sender_role == "engine" else "openpine"
            else:
                component = _KIND_COMPONENT[kind]
            _validate_component_provenance(
                message,
                execution_context=admitted_execution_context,
                component=component,
                reason="MESSAGE_PRODUCER_IDENTITY_MISMATCH",
                message="worker message producer differs from its admitted sender and kind",
                index=index,
            )

        expected_causation = None if index == 0 else previous_message_id
        actual_causation = message.get("causation_id")
        if actual_causation != expected_causation:
            _fail(
                "CAUSATION_ID_MISMATCH",
                "worker protocol causation identity is inconsistent",
                index=index,
                expected=expected_causation,
                actual=actual_causation,
            )

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
                    if execution_context is not None:
                        _validate_component_provenance(
                            bar,
                            execution_context=execution_context,
                            component="marketdata-provider",
                            reason="BAR_PROVENANCE_MISMATCH",
                            message=(
                                "BAR_BEGIN canonical bar provenance differs from the admitted stack"
                            ),
                            index=index,
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
                    if execution_context is not None:
                        _validate_component_provenance(
                            projection,
                            execution_context=execution_context,
                            component="backtest_engine",
                            reason="PROJECTION_PROVENANCE_MISMATCH",
                            message=(
                                "broker projection provenance differs from the admitted stack"
                            ),
                            index=index,
                        )
            elif kind in {"INTENT_BATCH", "BROKER_EVENT_BATCH", "RECALC_RESULT", "BAR_COMMIT"}:
                aggregate_spec = {
                    "INTENT_BATCH": ("intents", "intent_batch_hash", "openpine.intent.v2"),
                    "BROKER_EVENT_BATCH": (
                        "broker_events",
                        "broker_event_batch_hash",
                        "openpine.broker.v2",
                    ),
                }.get(kind)
                if aggregate_spec is not None:
                    items_field, hash_field, item_schema_id = aggregate_spec
                    items = body.get(items_field)
                    if isinstance(items, list):
                        batch_items: list[Mapping[str, object]] = []
                        for item_index, item in enumerate(items):
                            if not isinstance(item, Mapping):
                                _fail(
                                    "AGGREGATE_BATCH_ITEM_INVALID",
                                    "worker aggregate batch contains a non-object item",
                                    index=index,
                                    field=items_field,
                                    item_index=item_index,
                                )
                            batch_items.append(item)
                        expected_batch_hash = aggregate_batch_hash(
                            batch_items,
                            batch_kind=kind,
                            item_schema_id=item_schema_id,
                        )
                        if body.get(hash_field) != expected_batch_hash:
                            _fail(
                                "AGGREGATE_BATCH_HASH_MISMATCH",
                                "worker aggregate batch hash does not identify its canonical array",
                                index=index,
                                field=hash_field,
                                expected=expected_batch_hash,
                                actual=body.get(hash_field),
                            )
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
                            intent = cast(Mapping[str, object], intent)
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
                            _validate_component_provenance(
                                intent,
                                execution_context=execution_context,
                                component="pinelib",
                                reason="INTENT_PROVENANCE_MISMATCH",
                                message="intent provenance differs from the admitted stack",
                                index=index,
                                item_index=item_index,
                            )
                            source_span = intent.get("source_span")
                            if (
                                isinstance(source_span, Mapping)
                                and source_span.get("known") is True
                                and source_span.get("source_hash")
                                != execution_context.get("source_hash")
                            ):
                                _fail(
                                    "INTENT_PROVENANCE_MISMATCH",
                                    "known intent source differs from the admitted source",
                                    index=index,
                                    item_index=item_index,
                                    field="source_hash",
                                    expected=execution_context.get("source_hash"),
                                    actual=source_span.get("source_hash"),
                                )
                if kind == "INTENT_BATCH":
                    last_intent_batch = (message_id, body.get("intent_batch_hash"))
                if kind == "RECALC_RESULT":
                    expected_intent_binding = last_intent_batch
                    actual_intent_binding = (
                        body.get("intent_batch_message_id"),
                        body.get("intent_batch_hash"),
                    )
                    if (
                        expected_intent_binding is None
                        or actual_intent_binding != expected_intent_binding
                    ):
                        _fail(
                            "RECALC_INTENT_BINDING_MISMATCH",
                            "RECALC_RESULT must bind the specific preceding INTENT_BATCH",
                            index=index,
                            expected=expected_intent_binding,
                            actual=actual_intent_binding,
                        )
                if kind == "BROKER_EVENT_BATCH" and execution_context is not None:
                    broker_events = body.get("broker_events")
                    if isinstance(broker_events, list):
                        for item_index, broker_event in enumerate(broker_events):
                            _validate_component_provenance(
                                cast(Mapping[str, object], broker_event),
                                execution_context=execution_context,
                                component="backtest_engine",
                                reason="BROKER_EVENT_PROVENANCE_MISMATCH",
                                message=("broker event provenance differs from the admitted stack"),
                                index=index,
                                item_index=item_index,
                            )
                if kind == "BAR_COMMIT":
                    state_ref = body.get("state_ref")
                    projection_ref = body.get("broker_projection_ref")
                    if (
                        not isinstance(state_ref, Mapping)
                        or state_ref.get("artifact_hash") != body.get("state_hash")
                        or not isinstance(projection_ref, Mapping)
                        or projection_ref.get("artifact_hash") != body.get("broker_projection_hash")
                    ):
                        _fail(
                            "BAR_COMMIT_ARTIFACT_MISMATCH",
                            "BAR_COMMIT hashes must bind its sealed state/projection references",
                            index=index,
                        )
                    last_bar_commit = {
                        "message_id": message_id,
                        "sequence": sequence,
                        "state_hash": body.get("state_hash"),
                        "broker_projection_hash": body.get("broker_projection_hash"),
                    }
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
                projection = body.get("broker_projection")
                if not isinstance(projection, Mapping) or body.get(
                    "broker_projection_hash"
                ) != projection.get("content_hash"):
                    _fail(
                        "PROJECTION_HASH_MISMATCH",
                        "RECALC_REQUEST projection hash does not identify its payload",
                        index=index,
                    )
                projection_expectations = {
                    "run_id": baseline["run_id"],
                    "series_id": (
                        execution_context.get("series_id")
                        if execution_context is not None
                        else None
                    ),
                    "instrument_id": (
                        execution_context.get("instrument_id")
                        if execution_context is not None
                        else None
                    ),
                    "bar_index": current_bar["bar_index"],
                    "bar_open_time_utc_ms": current_bar["bar_open_time_utc_ms"],
                    "recalc_iteration": expected_recalc,
                }
                for field, expected in projection_expectations.items():
                    if projection.get(field) != expected:
                        _fail(
                            "PROJECTION_IDENTITY_MISMATCH",
                            "RECALC_REQUEST projection differs from the active callback",
                            index=index,
                            field=field,
                            expected=expected,
                            actual=projection.get(field),
                        )
                if execution_context is not None:
                    _validate_component_provenance(
                        projection,
                        execution_context=execution_context,
                        component="backtest_engine",
                        reason="PROJECTION_PROVENANCE_MISMATCH",
                        message="recalculation projection differs from the admitted stack",
                        index=index,
                    )
                current_bar["recalc_iteration"] = expected_recalc
            elif kind == "CHECKPOINT":
                if last_bar_commit is None or body.get("committed_sequence") != last_bar_commit.get(
                    "sequence"
                ):
                    _fail(
                        "CHECKPOINT_COMMIT_MISMATCH",
                        "checkpoint must bind the most recent BAR_COMMIT sequence",
                        index=index,
                        expected=(
                            None if last_bar_commit is None else last_bar_commit.get("sequence")
                        ),
                        actual=body.get("committed_sequence"),
                    )
                checkpoint_ref = body.get("checkpoint_ref")
                if isinstance(checkpoint_ref, Mapping):
                    _validate_checkpoint_proof(
                        checkpoint_ref,
                        execution_context=execution_context,
                        index=index,
                    )
                expected_ref = (
                    body.get("checkpoint_id"),
                    body.get("checkpoint_hash"),
                    body.get("committed_sequence"),
                    last_bar_commit.get("state_hash"),
                    last_bar_commit.get("broker_projection_hash"),
                    last_bar_commit.get("message_id"),
                )
                actual_ref = (
                    (
                        checkpoint_ref.get("checkpoint_id"),
                        checkpoint_ref.get("checkpoint_hash"),
                        checkpoint_ref.get("committed_sequence"),
                        checkpoint_ref.get("state_hash"),
                        checkpoint_ref.get("broker_projection_hash"),
                        checkpoint_ref.get("committed_message_id"),
                    )
                    if isinstance(checkpoint_ref, Mapping)
                    else None
                )
                if actual_ref != expected_ref:
                    _fail(
                        "CHECKPOINT_PROOF_MISMATCH",
                        "checkpoint proof must bind its checkpoint and last commit",
                        index=index,
                    )
                checkpoint_id = body.get("checkpoint_id")
                if isinstance(checkpoint_id, str):
                    checkpoints[checkpoint_id] = (
                        body.get("checkpoint_hash"),
                        body.get("committed_sequence"),
                        last_bar_commit.get("state_hash"),
                        last_bar_commit.get("broker_projection_hash"),
                        last_bar_commit.get("message_id"),
                    )
            elif kind == "RESTORE":
                checkpoint_id = body.get("checkpoint_id")
                known_checkpoint = (
                    checkpoints.get(checkpoint_id) if isinstance(checkpoint_id, str) else None
                )
                if known_checkpoint is not None:
                    if "external_checkpoint_proof" in body:
                        _fail(
                            "UNEXPECTED_EXTERNAL_CHECKPOINT_PROOF",
                            "session-local RESTORE must not override its admitted checkpoint proof",
                            index=index,
                        )
                    if known_checkpoint[:2] != (
                        body.get("checkpoint_hash"),
                        body.get("committed_sequence"),
                    ):
                        _fail(
                            "RESTORE_CHECKPOINT_MISMATCH",
                            "RESTORE differs from its session checkpoint identity",
                            index=index,
                        )
                    last_bar_commit = {
                        "message_id": known_checkpoint[4],
                        "sequence": known_checkpoint[1],
                        "state_hash": known_checkpoint[2],
                        "broker_projection_hash": known_checkpoint[3],
                    }
                else:
                    proof = body.get("external_checkpoint_proof")
                    if not isinstance(proof, Mapping):
                        _fail(
                            "EXTERNAL_CHECKPOINT_PROOF_REQUIRED",
                            "unknown RESTORE requires a sealed external checkpoint proof",
                            index=index,
                        )
                    _validate_checkpoint_proof(
                        proof,
                        execution_context=execution_context,
                        index=index,
                    )
                    expected_external = (
                        body.get("checkpoint_id"),
                        body.get("checkpoint_hash"),
                        body.get("committed_sequence"),
                    )
                    actual_external = (
                        proof.get("checkpoint_id"),
                        proof.get("checkpoint_hash"),
                        proof.get("committed_sequence"),
                    )
                    if actual_external != expected_external:
                        _fail(
                            "RESTORE_CHECKPOINT_MISMATCH",
                            "external RESTORE proof differs from requested checkpoint",
                            index=index,
                        )
                    last_bar_commit = {
                        "message_id": proof.get("committed_message_id"),
                        "sequence": proof.get("committed_sequence"),
                        "state_hash": proof.get("state_hash"),
                        "broker_projection_hash": proof.get("broker_projection_hash"),
                    }
            elif kind == "FINALIZE":
                if body.get("final_sequence") != index - 1:
                    _fail(
                        "FINAL_SEQUENCE_MISMATCH",
                        "FINALIZE final_sequence must identify the preceding message",
                        index=index,
                        expected=index - 1,
                        actual=body.get("final_sequence"),
                    )
                expected_final = (
                    None
                    if last_bar_commit is None
                    else (
                        last_bar_commit.get("message_id"),
                        last_bar_commit.get("sequence"),
                        last_bar_commit.get("state_hash"),
                        last_bar_commit.get("broker_projection_hash"),
                    )
                )
                actual_final = (
                    body.get("last_commit_message_id"),
                    body.get("last_committed_sequence"),
                    body.get("final_state_hash"),
                    body.get("broker_projection_hash"),
                )
                if expected_final is None or actual_final != expected_final:
                    _fail(
                        "FINALIZE_COMMIT_MISMATCH",
                        "FINALIZE must bind the most recent committed state",
                        index=index,
                        expected=expected_final,
                        actual=actual_final,
                    )

        previous_kind = kind
        previous_message_id = message_id

    if previous_kind not in {"FINALIZE", "ABORT"}:
        _fail(
            "TRUNCATED_SEQUENCE",
            "worker protocol sequence did not reach FINALIZE or ABORT",
            final_kind=previous_kind,
        )
