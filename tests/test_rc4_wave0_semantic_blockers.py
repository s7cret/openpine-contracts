from collections.abc import Mapping

import pytest

from openpine_contracts import (
    SchemaValidationError,
    get_schema,
    list_schema_ids,
    validate_payload,
)

HASH = "sha256:" + ("a" * 64)
RC4_STANDALONE_SCHEMA_IDS = {
    "openpine.execution_context.v1",
    "openpine.broker_projection.v1",
    "openpine.checkpoint.v1",
    "openpine.trial.identity.v1",
}
RC4_WORKER_ENVELOPE_FIELDS = {
    "session_id",
    "run_id",
    "sequence",
    "correlation_id",
    "causation_id",
}
RC4_PROVENANCE_ENVELOPE_FIELDS = {
    "producer",
    "producer_version",
    "producer_commit",
    "stack_id",
    "created_at_utc_ms",
    "serializer_id",
    "content_hash_alg",
    "content_hash",
}


def _intent(kind: str, **fields: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "schema_id": "openpine.intent.v2",
        "schema_version": "2.2.0",
        "producer": "openpine-contract-tests",
        "producer_version": "5.0.0-rc.4",
        "producer_commit": "d" * 40,
        "stack_id": "sha256:" + ("b" * 64),
        "created_at_utc_ms": 0,
        "serializer_id": "openpine.canonical.json.v1",
        "content_hash_alg": "sha256",
        "content_hash": HASH,
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
            "start_offset": 10,
            "end_offset": 20,
            "start_line": 2,
            "start_col": 4,
            "end_line": 2,
            "end_col": 14,
        },
        "idempotency_key": "run-1:7:0:cmd-1",
    }
    payload.update(fields)
    return payload


def test_worker_protocol_v2_1_uses_causal_state_machine_envelope() -> None:
    schema = get_schema("openpine.worker.protocol.v2")
    required = schema["required"]
    properties = schema["properties"]
    assert isinstance(required, list)
    assert isinstance(properties, dict)
    required_fields = set(required)

    assert {
        "schema_version": properties["schema_version"],
        "missing_state_machine_fields": sorted(RC4_WORKER_ENVELOPE_FIELDS - required_fields),
        "missing_provenance_fields": sorted(RC4_PROVENANCE_ENVELOPE_FIELDS - required_fields),
    } == {
        "schema_version": {"const": "2.1.0"},
        "missing_state_machine_fields": [],
        "missing_provenance_fields": [],
    }


def test_catalog_registers_rc4_standalone_contracts() -> None:
    catalog = set(list_schema_ids(include_aliases=False))
    missing = RC4_STANDALONE_SCHEMA_IDS - catalog
    assert not missing, f"missing standalone RC.4 schemas: {sorted(missing)}"

    for schema_id in RC4_STANDALONE_SCHEMA_IDS:
        assert get_schema(schema_id)["$id"] == schema_id


@pytest.mark.parametrize(
    ("kind", "fields"),
    [
        (
            "entry",
            {
                "order_id": "long",
                "direction": "LONG",
                "qty": "1",
                "risk_rule": "max_drawdown",
                "risk_value": "10",
            },
        ),
        ("close_all", {"order_id": "long"}),
    ],
)
def test_intent_rejects_fields_from_a_contradictory_kind(
    kind: str, fields: Mapping[str, object]
) -> None:
    with pytest.raises(SchemaValidationError):
        validate_payload("openpine.intent.v2", _intent(kind, **fields))
