from importlib import resources

from openpine_contracts import (
    ArtifactEnvelope,
    SchemaNotFoundError,
    SchemaValidationError,
    get_schema,
    list_schema_ids,
    schema_bytes,
    schema_hash,
    validate_payload,
)
from openpine_contracts.hashing import SERIALIZER_ID, content_hash
from openpine_contracts.registry import CATALOG


def _envelope(schema_id: str, extra: dict[str, object]) -> dict[str, object]:
    payload = {
        "schema_id": schema_id,
        "schema_version": "1.0.0-rc.1",
        "producer": "openpine-contracts-tests",
        "producer_version": "5.0.0-rc.3",
        "producer_commit": "deadbeef",
        "stack_id": "stack-test",
        "created_at_utc_ms": 0,
        "serializer_id": SERIALIZER_ID,
        "content_hash_alg": "sha256",
        "content_hash": "sha256:" + ("ab" * 32),
    }
    payload.update(extra)
    payload["content_hash"] = content_hash(payload, schema_id=schema_id)
    return payload


def test_catalog_is_complete_and_packaged() -> None:
    ids = list_schema_ids(include_aliases=True)
    assert set(CATALOG).issubset(ids)
    assert "openpine.marketdata.v2" in ids
    assert "openpine.marketdata.bar.v2" in ids
    root = resources.files("openpine_contracts.schemas")
    for schema_id in ids:
        raw = schema_bytes(schema_id)
        assert raw.startswith(b"{")
        schema = get_schema(schema_id)
        assert schema["$id"] == schema_id
        assert schema_hash(schema_id).startswith("sha256:")
        assert root.joinpath(f"{schema_id}.json").is_file()


def test_unknown_schema_fails() -> None:
    try:
        get_schema("openpine.missing.v9")
    except SchemaNotFoundError as exc:
        assert exc.code == "SCHEMA_NOT_FOUND"
    else:
        raise AssertionError("expected SchemaNotFoundError")


def test_validate_event_and_bar() -> None:
    event = _envelope(
        "openpine.event.v1",
        {
            "event_id": "evt-1",
            "event_type": "intent.entry",
            "sequence": 0,
            "occurred_at_utc_ms": 1,
            "observed_at_utc_ms": 2,
            "payload_hash": "sha256:" + ("cd" * 32),
            "payload": {"kind": "entry"},
        },
    )
    validate_payload("openpine.event.v1", event)
    ArtifactEnvelope.from_mapping(event)

    bar = _envelope(
        "openpine.marketdata.bar.v2",
        {
            "series_id": "binance:BTCUSDT:15m",
            "instrument_id": "binance:BTCUSDT",
            "timeframe": "15m",
            "open_time_utc_ms": 0,
            "close_time_utc_ms": 900000,
            "open": "1.0",
            "high": "2.0",
            "low": "0.5",
            "close": "1.5",
            "volume": "10",
            "finality": "FINAL",
            "revision_state": "ORIGINAL",
            "revision": 0,
            "provider": "binance",
            "snapshot_id": "snap-1",
            "bar_content_hash": "sha256:" + ("ef" * 32),
        },
    )
    validate_payload("openpine.marketdata.bar.v2", bar)


def test_breaking_schema_rejected() -> None:
    try:
        validate_payload("openpine.run.v2", {"schema_id": "nope"})
    except SchemaValidationError as exc:
        assert exc.code == "SCHEMA_VALIDATION_ERROR"
    else:
        raise AssertionError("expected SchemaValidationError")
