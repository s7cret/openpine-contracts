from collections.abc import Mapping

import pytest

from openpine_contracts import SchemaValidationError, list_schema_ids, validate_payload

HASH_A = "sha256:" + ("a" * 64)
HASH_B = "sha256:" + ("b" * 64)
HASH_C = "sha256:" + ("c" * 64)


def _envelope(schema_id: str, schema_version: str = "2.0.0") -> dict[str, object]:
    return {
        "schema_id": schema_id,
        "schema_version": schema_version,
        "producer": "openpine-contract-tests",
        "producer_version": "5.0.0-rc.5",
        "producer_commit": "d" * 40,
        "stack_id": HASH_C,
        "created_at_utc_ms": 0,
        "serializer_id": "openpine.canonical.json.v1",
        "content_hash_alg": "sha256",
        "content_hash": HASH_A,
    }


def _assert_invalid(schema_id: str, payload: Mapping[str, object]) -> None:
    with pytest.raises(SchemaValidationError):
        validate_payload(schema_id, dict(payload))


def _intent(kind: str, **fields: object) -> dict[str, object]:
    payload = _envelope("openpine.intent.v2", "2.2.0")
    payload.update(
        {
            "event_id": "evt-1",
            "sequence": 0,
            "command_id": "cmd-1",
            "kind": kind,
            "run_id": "run-1",
            "strategy_id": "strategy-1",
            "series_id": "binance:BTCUSDT:15m",
            "instrument_id": "binance:BTCUSDT",
            "timeframe": "15m",
            "bar_index": 7,
            "bar_open_time_utc_ms": 6_300_000,
            "phase": "score",
            "recalc_iteration": 0,
            "semantic_profile": "strict_5x",
            "source_span": {
                "known": True,
                "source_hash": HASH_B,
                "start_offset": 10,
                "end_offset": 20,
                "start_line": 2,
                "start_col": 4,
                "end_line": 2,
                "end_col": 14,
            },
            "idempotency_key": "run-1:7:0:cmd-1",
        }
    )
    payload.update(fields)
    return payload


INTENT_CASES = {
    "entry": {"order_id": "long", "direction": "LONG", "qty": "1"},
    "order": {"order_id": "scale", "direction": "SHORT", "qty": "0.5"},
    "exit": {"order_id": "take-profit", "from_entry": "long", "limit": "101.5"},
    "close": {"from_entry": "long"},
    "close_all": {},
    "cancel": {"order_id": "scale"},
    "cancel_all": {},
    "risk": {
        "risk_rule": "max_drawdown",
        "risk_value": "10",
        "risk_unit": "percent",
        "risk_scope": "strategy",
    },
}


@pytest.mark.parametrize(("kind", "fields"), INTENT_CASES.items())
def test_intent_v2_2_accepts_each_strict_kind(kind: str, fields: dict[str, object]) -> None:
    validate_payload("openpine.intent.v2", _intent(kind, **fields))


@pytest.mark.parametrize(
    ("kind", "missing"),
    [
        ("entry", "direction"),
        ("entry", "order_id"),
        ("entry", "qty"),
        ("order", "direction"),
        ("order", "order_id"),
        ("order", "qty"),
        ("exit", "order_id"),
        ("exit", "from_entry"),
        ("close", "from_entry"),
        ("cancel", "order_id"),
        ("risk", "risk_rule"),
        ("risk", "risk_value"),
        ("risk", "risk_unit"),
        ("risk", "risk_scope"),
    ],
)
def test_intent_kind_rejects_missing_kind_specific_identity(kind: str, missing: str) -> None:
    fields = dict(INTENT_CASES[kind])
    fields.pop(missing)
    _assert_invalid("openpine.intent.v2", _intent(kind, **fields))


@pytest.mark.parametrize(
    "missing",
    [
        "event_id",
        "sequence",
        "command_id",
        "series_id",
        "instrument_id",
        "timeframe",
        "bar_index",
        "bar_open_time_utc_ms",
        "phase",
        "recalc_iteration",
        "semantic_profile",
        "source_span",
        "idempotency_key",
        "content_hash",
    ],
)
def test_intent_rejects_missing_source_of_truth_fields(missing: str) -> None:
    payload = _intent("entry", **INTENT_CASES["entry"])
    payload.pop(missing)
    _assert_invalid("openpine.intent.v2", payload)


def test_intent_requires_schema_version_2_2_0() -> None:
    payload = _intent("close_all")
    payload["schema_version"] = "2.0.0"
    _assert_invalid("openpine.intent.v2", payload)


def _generated_artifact() -> dict[str, object]:
    payload = _envelope("openpine.generated_artifact.v2", "2.1.0")
    payload.update(
        {
            "source_hash": HASH_A,
            "frontend_artifact_hash": HASH_B,
            "ast_hash": HASH_C,
            "emitted_module_hash": HASH_A,
            "source_map_hash": HASH_B,
            "support_profile_hash": HASH_C,
            "lowering_version": "2.1.0",
            "producer_commits": {
                "pine2ast": "a" * 40,
                "ast2python": "b" * 40,
                "pinelib": "c" * 40,
                "openpine-contracts": "d" * 40,
            },
            "semantic_profile": "strict_5x",
            "required_runtime_capabilities": ["closed_bar", "recalc_after_fill"],
            "import_allowlist": ["openpine_runtime.api", "openpine_runtime.series"],
            "entrypoint_module": "generated.strategy",
            "entrypoint_class": "GeneratedStrategy",
        }
    )
    return payload


@pytest.mark.parametrize(
    "missing",
    [
        "source_hash",
        "frontend_artifact_hash",
        "ast_hash",
        "emitted_module_hash",
        "source_map_hash",
        "support_profile_hash",
        "lowering_version",
        "producer_commits",
        "semantic_profile",
        "required_runtime_capabilities",
        "import_allowlist",
        "entrypoint_module",
        "entrypoint_class",
    ],
)
def test_generated_artifact_requires_every_provenance_binding(missing: str) -> None:
    payload = _generated_artifact()
    payload.pop(missing)
    _assert_invalid("openpine.generated_artifact.v2", payload)


def test_generated_artifact_accepts_complete_provenance_binding() -> None:
    validate_payload("openpine.generated_artifact.v2", _generated_artifact())


def test_generated_artifact_rejects_abbreviated_producer_commit() -> None:
    payload = _generated_artifact()
    payload["producer_commits"] = {"pine2ast": "deadbeef"}
    _assert_invalid("openpine.generated_artifact.v2", payload)


def test_generated_artifact_requires_all_exact_producer_commits() -> None:
    payload = _generated_artifact()
    payload["producer_commits"] = {"pine2ast": "a" * 40}
    _assert_invalid("openpine.generated_artifact.v2", payload)


def _worker_message(kind: str, body: dict[str, object]) -> dict[str, object]:
    payload = _envelope("openpine.worker.protocol.v2", "2.1.0")
    payload.update(
        {
            "session_id": "session-1",
            "run_id": "run-1",
            "sequence": 0,
            "correlation_id": "correlation-1",
            "causation_id": None,
            "kind": kind,
            "body": body,
        }
    )
    return payload


WORKER_CASES = {
    "HELLO": {
        "worker_id": "worker-1",
        "protocol_version": "2.1.0",
        "capabilities": ["closed_bar"],
    },
    "LOAD_ARTIFACT": {
        "artifact_hash": HASH_A,
        "module_hash": HASH_B,
        "entrypoint_module": "generated.strategy",
        "entrypoint_class": "GeneratedStrategy",
    },
    "INIT_RUN": {
        "run_id": "run-1",
        "run_hash": HASH_A,
        "execution_context_hash": HASH_B,
        "semantic_profile": "strict_5x",
        "capabilities": ["closed_bar"],
    },
    "BAR_BEGIN": {
        "run_id": "run-1",
        "bar_index": 1,
        "bar_open_time_utc_ms": 900_000,
        "recalc_iteration": 0,
        "bar_hash": HASH_A,
    },
    "INTENT_BATCH": {
        "run_id": "run-1",
        "bar_index": 1,
        "recalc_iteration": 0,
        "intent_batch_hash": HASH_A,
        "intents": [],
    },
    "BROKER_EVENT_BATCH": {
        "run_id": "run-1",
        "bar_index": 1,
        "recalc_iteration": 0,
        "broker_event_batch_hash": HASH_B,
        "broker_events": [],
    },
    "RECALC_REQUEST": {
        "run_id": "run-1",
        "bar_index": 1,
        "recalc_iteration": 1,
        "cause_sequence": 4,
    },
    "RECALC_RESULT": {
        "run_id": "run-1",
        "bar_index": 1,
        "recalc_iteration": 1,
        "intent_batch_hash": HASH_A,
    },
    "BAR_COMMIT": {
        "run_id": "run-1",
        "bar_index": 1,
        "recalc_iteration": 1,
        "state_hash": HASH_A,
        "broker_projection_hash": HASH_B,
    },
    "CHECKPOINT": {
        "run_id": "run-1",
        "checkpoint_id": "cp-1",
        "checkpoint_hash": HASH_A,
        "committed_sequence": 9,
    },
    "RESTORE": {
        "run_id": "run-1",
        "checkpoint_id": "cp-1",
        "checkpoint_hash": HASH_A,
        "committed_sequence": 9,
    },
    "FINALIZE": {
        "run_id": "run-1",
        "final_sequence": 9,
        "final_state_hash": HASH_A,
        "broker_projection_hash": HASH_B,
    },
    "ABORT": {"run_id": "run-1", "error_code": "RUNTIME_ABORT", "reason": "stopped"},
}


def test_worker_protocol_is_registered() -> None:
    assert "openpine.worker.protocol.v2" in list_schema_ids(include_aliases=False)


def test_rc3_worker_protocol_envelope_is_rejected_by_v2_1_contract() -> None:
    payload = _worker_message("HELLO", dict(WORKER_CASES["HELLO"]))
    payload["schema_version"] = "2.0.0"
    body = payload["body"]
    assert isinstance(body, dict)
    body["protocol_version"] = "2.0.0"
    _assert_invalid("openpine.worker.protocol.v2", payload)


@pytest.mark.parametrize("kind", WORKER_CASES)
def test_worker_protocol_rejects_empty_message_body(kind: str) -> None:
    _assert_invalid("openpine.worker.protocol.v2", _worker_message(kind, {}))


def test_worker_protocol_rejects_unknown_body_fields() -> None:
    body: dict[str, object] = dict(WORKER_CASES["FINALIZE"], unexpected=True)
    _assert_invalid("openpine.worker.protocol.v2", _worker_message("FINALIZE", body))


def _run(run_mode: str = "BACKTEST") -> dict[str, object]:
    payload = _envelope("openpine.run.v2", "2.1.0")
    payload.update(
        {
            "run_id": "run-1",
            "run_mode": run_mode,
            "state": "CREATED",
            "stack_manifest_hash": HASH_A,
            "wheel_identities": [
                {
                    "name": "openpine-runtime",
                    "version": "5.0.0-rc.5",
                    "content_hash": HASH_B,
                }
            ],
            "schema_hashes": {
                "openpine.intent.v2": HASH_A,
                "openpine.worker.protocol.v2": HASH_B,
            },
            "generated_artifact_hash": HASH_B,
            "data_snapshot_hash": HASH_C,
            "semantic_profile": "strict_5x",
            "finality_policy": "CLOSED_BAR_ONLY",
            "warmup_policy": "CALC_ONLY",
            "score_policy": "ALL_BARS",
            "required_capabilities": ["closed_bar", "deterministic_clock"],
        }
    )
    return payload


@pytest.mark.parametrize(
    "missing",
    [
        "run_mode",
        "stack_manifest_hash",
        "wheel_identities",
        "schema_hashes",
        "generated_artifact_hash",
        "data_snapshot_hash",
        "semantic_profile",
        "finality_policy",
        "warmup_policy",
        "score_policy",
        "required_capabilities",
    ],
)
def test_run_requires_replay_identity_fields(missing: str) -> None:
    payload = _run()
    payload.pop(missing)
    _assert_invalid("openpine.run.v2", payload)


def test_run_accepts_complete_backtest_identity() -> None:
    validate_payload("openpine.run.v2", _run())


@pytest.mark.parametrize("run_mode", ["PAPER", "LIVE"])
def test_connected_run_modes_require_broker_references(run_mode: str) -> None:
    payload = _run(run_mode)
    _assert_invalid("openpine.run.v2", payload)

    payload.update(
        {
            "broker_adapter_ref": "broker-adapter-1",
            "broker_account_ref": "broker-account-1",
        }
    )
    validate_payload("openpine.run.v2", payload)


def test_marketdata_bar_still_rejects_empty_body() -> None:
    payload = _envelope("openpine.marketdata.v2")
    payload.update({"kind": "bar", "body": {}})
    _assert_invalid("openpine.marketdata.v2", payload)


def test_job_contract_requires_monotonic_cas_version() -> None:
    from openpine_contracts import get_schema

    schema = get_schema("openpine.job.v1")
    required = schema["required"]
    properties = schema["properties"]
    assert isinstance(required, list)
    assert isinstance(properties, dict)
    assert "version" in required
    assert properties["version"] == {"type": "integer", "minimum": 1}
