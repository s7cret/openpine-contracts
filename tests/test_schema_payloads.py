from openpine_contracts import SchemaValidationError, validate_payload
from openpine_contracts.hashing import SERIALIZER_ID, content_hash


def _envelope(schema_id: str, extra: dict[str, object]) -> dict[str, object]:
    payload: dict[str, object] = {
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
    if schema_id in {"openpine.marketdata.v2", "openpine.marketdata.bar.v2"}:
        payload.update(
            {
                "schema_version": "2.1.0",
                "producer": "marketdata-provider",
                "producer_version": "5.0.0-rc.5",
                "producer_commit": "a" * 40,
                "stack_id": "sha256:" + ("b" * 64),
            }
        )
    payload.update(extra)
    payload["content_hash"] = content_hash(payload, schema_id=schema_id)
    return payload


def test_marketdata_bar_kind_rejects_empty_body() -> None:
    payload = _envelope("openpine.marketdata.v2", {"kind": "bar", "body": {}})
    try:
        validate_payload("openpine.marketdata.v2", payload)
    except SchemaValidationError as exc:
        assert exc.code == "SCHEMA_VALIDATION_ERROR"
    else:
        raise AssertionError("kind=bar must require CanonicalBar, not any object")


def test_marketdata_bar_kind_accepts_canonical_bar() -> None:
    body = {
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
        "provider_revision": {"known": True, "revision": "binance-r1"},
        "snapshot_id": "snap-1",
        "bar_content_hash": "sha256:" + ("ef" * 32),
        "superseded_bar_hash": None,
    }
    payload = _envelope("openpine.marketdata.v2", {"kind": "bar", "body": body})
    validate_payload("openpine.marketdata.v2", payload)


def test_broker_command_rejects_empty_body() -> None:
    payload = _envelope("openpine.broker.v2", {"kind": "command", "body": {}})
    try:
        validate_payload("openpine.broker.v2", payload)
    except SchemaValidationError as exc:
        assert exc.code == "SCHEMA_VALIDATION_ERROR"
    else:
        raise AssertionError("kind=command must require BrokerCommand")


def test_intent_price_must_be_decimal_string() -> None:
    payload = _envelope(
        "openpine.intent.v2",
        {
            "kind": "entry",
            "run_id": "run-1",
            "strategy_id": "s-1",
            "bar_index": 0,
            "phase": "score",
            "idempotency_key": "k1",
            "price": "not-a-decimal",
        },
    )
    try:
        validate_payload("openpine.intent.v2", payload)
    except SchemaValidationError as exc:
        assert exc.code == "SCHEMA_VALIDATION_ERROR"
    else:
        raise AssertionError("intent.price must use canonical decimal pattern")


def test_event_payload_rejects_float() -> None:
    payload = {
        "schema_id": "openpine.event.v1",
        "schema_version": "1.0.0-rc.1",
        "producer": "openpine-contracts-tests",
        "producer_version": "5.0.0-rc.3",
        "producer_commit": "deadbeef",
        "stack_id": "stack-test",
        "created_at_utc_ms": 0,
        "serializer_id": SERIALIZER_ID,
        "content_hash_alg": "sha256",
        "content_hash": "sha256:" + ("ab" * 32),
        "event_id": "evt-1",
        "event_type": "intent.entry",
        "sequence": 0,
        "occurred_at_utc_ms": 1,
        "observed_at_utc_ms": 2,
        "payload_hash": "sha256:" + ("cd" * 32),
        "payload": {"qty": 1.25},
    }
    try:
        validate_payload("openpine.event.v1", payload)
    except SchemaValidationError as exc:
        assert exc.code == "SCHEMA_VALIDATION_ERROR"
    else:
        raise AssertionError("event.payload must not accept JSON numbers")
