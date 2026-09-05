from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import Any

import pytest

import openpine_contracts as contracts
from openpine_contracts import SchemaValidationError, list_schema_ids, validate_payload

HASH_A = "sha256:" + ("a" * 64)
HASH_B = "sha256:" + ("b" * 64)
HASH_C = "sha256:" + ("c" * 64)
HASH_D = "sha256:" + ("d" * 64)
COMMIT_A = "a" * 40
COMMIT_B = "b" * 40
COMMIT_C = "c" * 40
COMMIT_D = "d" * 40
COMMIT_E = "e" * 40
COMMIT_F = "f" * 40
COMMIT_1 = "1" * 40
COMMIT_2 = "2" * 40
RC4_IDS = (
    "openpine.execution_context.v1",
    "openpine.broker_projection.v1",
    "openpine.checkpoint.v1",
    "openpine.checkpoint.proof.v1",
    "openpine.trial.identity.v1",
)
STACK_COMPONENTS = (
    "openpine-contracts",
    "marketdata-provider",
    "pinelib",
    "pine2ast",
    "ast2python",
    "backtest_engine",
    "optimizer",
    "openpine",
)


def _envelope(schema_id: str, schema_version: str) -> dict[str, Any]:
    return {
        "schema_id": schema_id,
        "schema_version": schema_version,
        "producer": "openpine-contract-tests",
        "producer_version": "5.0.0-rc.5",
        "producer_commit": COMMIT_D,
        "stack_id": HASH_D,
        "created_at_utc_ms": 0,
        "serializer_id": "openpine.canonical.json.v1",
        "content_hash_alg": "sha256",
        "content_hash": HASH_A,
    }


def _assert_invalid(schema_id: str, payload: dict[str, Any]) -> None:
    with pytest.raises(SchemaValidationError):
        validate_payload(schema_id, payload)


def _source_known() -> dict[str, Any]:
    return {
        "known": True,
        "source_hash": HASH_C,
        "start_offset": 10,
        "end_offset": 20,
        "start_line": 2,
        "start_col": 4,
        "end_line": 2,
        "end_col": 14,
    }


def _source_unknown() -> dict[str, Any]:
    return {
        "known": False,
        "source_hash": None,
        "start_offset": None,
        "end_offset": None,
        "start_line": None,
        "start_col": None,
        "end_line": None,
        "end_col": None,
    }


INTENT_FIELDS: dict[str, dict[str, Any]] = {
    "entry": {"order_id": "long", "direction": "LONG", "qty": "1"},
    "order": {
        "order_id": "scale",
        "direction": "SHORT",
        "qty": "0.5",
        "limit": "101.25",
    },
    "exit": {
        "order_id": "take-profit",
        "from_entry": "long",
        "profit": "10",
        "loss": "5",
        "trail_price": None,
        "trail_points": None,
        "trail_offset": None,
    },
    "close": {"from_entry": "long", "qty_percent": "50", "immediately": False},
    "close_all": {"comment": "flatten", "immediately": True},
    "cancel": {"order_id": "scale"},
    "cancel_all": {},
    "risk": {
        "risk_rule": "max_drawdown",
        "risk_value": "10",
        "risk_unit": "percent",
        "risk_scope": "strategy",
    },
}


def _intent(kind: str, **overrides: Any) -> dict[str, Any]:
    payload = _envelope("openpine.intent.v2", "2.2.0")
    payload.update(
        {
            "producer": "backtest_engine",
            "producer_version": "5.0.0-rc.5",
            "producer_commit": COMMIT_F,
            "stack_id": HASH_D,
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
            "source_span": _source_known(),
            "idempotency_key": "run-1:7:0:cmd-1",
            **INTENT_FIELDS[kind],
        }
    )
    payload.update(overrides)
    return contracts.seal_content_hash(payload, schema_id="openpine.intent.v2")


def _execution_context() -> dict[str, Any]:
    payload = _envelope("openpine.execution_context.v1", "1.0.0")
    payload.update(
        {
            "run_id": "run-1",
            "strategy_id": "strategy-1",
            "session_id": "session-1",
            "stack_manifest_hash": HASH_D,
            "wheel_identities": [
                {"name": name, "version": "5.0.0rc5", "content_hash": HASH_B}
                for name in STACK_COMPONENTS
            ],
            "schema_hashes": {
                "openpine.execution_context.v1": HASH_A,
                "openpine.intent.v2": HASH_B,
                "openpine.worker.protocol.v2": HASH_C,
                "openpine.checkpoint.v1": HASH_D,
                "openpine.checkpoint.proof.v1": HASH_A,
            },
            "generated_artifact_hash": HASH_B,
            "source_hash": HASH_C,
            "emitted_module_hash": HASH_D,
            "data_snapshot_hash": HASH_A,
            "series_id": "binance:BTCUSDT:15m",
            "instrument_id": "binance:BTCUSDT",
            "exchange": "binance",
            "market": "spot",
            "symbol": "BTCUSDT",
            "timeframe": "15m",
            "timezone": "UTC",
            "currency": "USDT",
            "mintick": "0.01",
            "pointvalue": "1",
            "session_policy": "24x7",
            "semantic_profile": "strict_5x",
            "finality_policy": "CLOSED_BAR_ONLY",
            "warmup_policy": "CALC_ONLY",
            "score_policy": "ALL_BARS",
            "end_policy": "LIQUIDATE_ON_LAST_BAR",
            "capabilities": ["closed_bar", "deterministic_clock"],
            "policy_registry_version": "openpine.policies.rc4.v1",
            "schema_registry_version": "openpine.schemas.rc4.v1",
            "capability_registry_version": "openpine.capabilities.rc4.v1",
            "producer_commits": {
                "openpine-contracts": COMMIT_A,
                "pine2ast": COMMIT_B,
                "ast2python": COMMIT_C,
                "pinelib": COMMIT_D,
                "marketdata-provider": COMMIT_E,
                "backtest_engine": COMMIT_F,
                "optimizer": COMMIT_2,
                "openpine": COMMIT_1,
            },
        }
    )
    return contracts.seal_content_hash(payload, schema_id="openpine.execution_context.v1")


def _broker_projection(recalc_iteration: int = 0) -> dict[str, Any]:
    payload = _envelope("openpine.broker_projection.v1", "1.0.0")
    payload.update(
        {
            "producer": "backtest_engine",
            "producer_version": "5.0.0-rc.5",
            "producer_commit": COMMIT_F,
            "stack_id": HASH_D,
            "run_id": "run-1",
            "series_id": "binance:BTCUSDT:15m",
            "instrument_id": "binance:BTCUSDT",
            "bar_index": 7,
            "bar_open_time_utc_ms": 6_300_000,
            "recalc_iteration": recalc_iteration,
            "position": {
                "direction": "LONG",
                "qty": "1",
                "avg_price": "100",
                "entry_name": "long",
            },
            "orders": [
                {
                    "order_id": "exit-1",
                    "entry_name": "long",
                    "state": "OPEN",
                    "direction": "SHORT",
                    "order_type": "LIMIT",
                    "qty": "1",
                    "filled_qty": "0",
                    "limit_price": "110",
                    "stop_price": None,
                    "created_bar_index": 7,
                    "updated_bar_index": 7,
                }
            ],
            "fills": [
                {
                    "fill_id": "fill-1",
                    "order_id": "long",
                    "trade_id": "trade-1",
                    "direction": "LONG",
                    "qty": "1",
                    "price": "100",
                    "commission": "0.1",
                    "bar_index": 7,
                    "occurred_at_utc_ms": 6_300_001,
                }
            ],
            "open_trades": [
                {
                    "trade_id": "trade-1",
                    "entry_name": "long",
                    "direction": "LONG",
                    "qty": "1",
                    "entry_price": "100",
                    "entry_bar_index": 7,
                    "entry_time_utc_ms": 6_300_001,
                    "unrealized_pnl": "2",
                }
            ],
            "closed_trades": [
                {
                    "trade_id": "trade-0",
                    "entry_name": "prior",
                    "direction": "LONG",
                    "qty": "1",
                    "entry_price": "90",
                    "entry_bar_index": 1,
                    "entry_time_utc_ms": 900_000,
                    "exit_price": "95",
                    "exit_bar_index": 2,
                    "exit_time_utc_ms": 1_800_000,
                    "realized_pnl": "5",
                    "commission": "0.2",
                }
            ],
            "realized_pnl": "5",
            "unrealized_pnl": "2",
            "gross_profit": "5",
            "gross_loss": "0",
            "max_drawdown": "1.5",
            "max_runup": "7",
            "commission": "0.3",
            "winning_trades": 1,
            "losing_trades": 0,
            "even_trades": 0,
            "cash": "10004.7",
            "equity": "10006.7",
            "currency": "USDT",
        }
    )
    return contracts.seal_content_hash(payload, schema_id="openpine.broker_projection.v1")


def _checkpoint() -> dict[str, Any]:
    payload = _envelope("openpine.checkpoint.v1", "1.0.0")
    payload.update(
        {
            "checkpoint_id": "checkpoint-1",
            "run_id": "run-1",
            "session_id": "session-1",
            "bar_index": 7,
            "bar_open_time_utc_ms": 6_300_000,
            "recalc_iteration": 1,
            "committed_sequence": 11,
            "bar_commit_hash": HASH_A,
            "generated_artifact_hash": HASH_B,
            "data_snapshot_hash": HASH_C,
            "stack_manifest_hash": HASH_D,
            "engine_checkpoint_hash": HASH_A,
            "worker_checkpoint_hash": HASH_B,
            "combined_hash": HASH_C,
            "checkpoint_hash": HASH_C,
            "payload_ref": {
                "codec": "msgpack",
                "compression": "zstd",
                "size_bytes": 4096,
                "segment_schema_hashes": {
                    "openpine.execution_context.v1": HASH_A,
                    "openpine.broker_projection.v1": HASH_B,
                },
                "uri": "s3://openpine-checkpoints/checkpoint-1.bin",
            },
        }
    )
    return contracts.seal_content_hash(payload, schema_id="openpine.checkpoint.v1")


def _trial_identity() -> dict[str, Any]:
    payload = _envelope("openpine.trial.identity.v1", "1.0.0")
    payload.update(
        {
            "optimizer_id": "optimizer-1",
            "strategy_id": "strategy-1",
            "generated_artifact_hash": HASH_A,
            "source_hash": HASH_B,
            "emitted_module_hash": HASH_C,
            "data_snapshot_hash": HASH_D,
            "stack_manifest_hash": HASH_A,
            "runner_fingerprint": HASH_B,
            "parameters": {"length": 14, "threshold": "0.5"},
            "policies": {
                "semantic_profile": "strict_5x",
                "finality_policy": "CLOSED_BAR_ONLY",
                "warmup_policy": "CALC_ONLY",
                "score_policy": "ALL_BARS",
                "end_policy": "LIQUIDATE_ON_LAST_BAR",
                "numeric_policy": "decimal-string-v1",
                "fill_policy": "ohlc-path-v1",
            },
            "schema_set": [
                {"schema_id": "openpine.intent.v2", "schema_hash": HASH_C},
                {"schema_id": "openpine.run.v2", "schema_hash": HASH_D},
            ],
            "seed": 42,
            "fold": {
                "fold_id": "fold-1",
                "train_start_utc_ms": 0,
                "train_end_utc_ms": 10_000,
                "test_start_utc_ms": 10_001,
                "test_end_utc_ms": 20_000,
            },
            "walk_forward": {
                "enabled": True,
                "window_size": 100,
                "step_size": 25,
                "anchored": False,
            },
            "objective": {
                "metric": "net_profit",
                "direction": "MAXIMIZE",
                "aggregation": "MEAN",
            },
            "constraints": [{"name": "max_drawdown", "operator": "LTE", "value": "20"}],
        }
    )
    return contracts.seal_content_hash(payload, schema_id="openpine.trial.identity.v1")


def _trial_lifecycle() -> dict[str, Any]:
    payload = _envelope("openpine.trial.v2", "2.1.0")
    payload.update(
        {
            "trial_key": "trial-1",
            "trial_identity_hash": HASH_D,
            "lifecycle": "QUEUED",
            "retry_count": 0,
            "metrics": {},
            "artifacts": [],
        }
    )
    return contracts.seal_content_hash(payload, schema_id="openpine.trial.v2")


def _canonical_bar() -> dict[str, Any]:
    payload = _envelope("openpine.marketdata.bar.v2", "2.1.0")
    payload.update(
        {
            "producer": "marketdata-provider",
            "producer_version": "5.0.0-rc.5",
            "producer_commit": COMMIT_E,
            "stack_id": HASH_D,
            "series_id": "binance:BTCUSDT:15m",
            "instrument_id": "binance:BTCUSDT",
            "timeframe": "15m",
            "open_time_utc_ms": 6_300_000,
            "close_time_utc_ms": 7_199_999,
            "open": "100",
            "high": "102",
            "low": "99",
            "close": "101",
            "volume": "12.5",
            "finality": "FINAL",
            "revision_state": "ORIGINAL",
            "revision": 0,
            "provider": "binance",
            "provider_revision": _provider_revision(),
            "snapshot_id": "snapshot-1",
            "bar_content_hash": HASH_A,
            "superseded_bar_hash": None,
        }
    )
    return contracts.seal_content_hash(payload, schema_id="openpine.marketdata.bar.v2")


_MARKETDATA_ENVELOPE_FIELDS = {
    "schema_id",
    "schema_version",
    "producer",
    "producer_version",
    "producer_commit",
    "stack_id",
    "created_at_utc_ms",
    "serializer_id",
    "content_hash_alg",
    "content_hash",
}


def _canonical_bar_body() -> dict[str, Any]:
    return {
        key: deepcopy(value)
        for key, value in _canonical_bar().items()
        if key not in _MARKETDATA_ENVELOPE_FIELDS
    }


def _legacy_data_snapshot() -> dict[str, Any]:
    return {
        "snapshot_id": "snapshot-1",
        "query": {
            "instrument_id": "binance:BTCUSDT",
            "timeframe": "15m",
            "start_utc_ms": 6_300_000,
            "end_utc_ms": 7_199_999,
            "finality_policy": "CLOSED_BAR_ONLY",
        },
        "bar_count": 1,
        "series_hash": HASH_A,
        "coverage": [],
        "gaps": [],
        "conflicts": [],
        "provider_revision": None,
        "created_at_utc_ms": 7_200_000,
    }


def _marketdata_message(kind: str, body: dict[str, Any]) -> dict[str, Any]:
    payload = _envelope("openpine.marketdata.v2", "2.1.0")
    payload.update(
        {
            "producer": "marketdata-provider",
            "producer_version": "5.0.0-rc.5",
            "producer_commit": COMMIT_E,
            "stack_id": HASH_D,
            "kind": kind,
            "body": deepcopy(body),
        }
    )
    return contracts.seal_content_hash(payload, schema_id="openpine.marketdata.v2")


def _provider_revision(known: bool = True) -> dict[str, Any]:
    return {"known": known, "revision": "binance-42" if known else None}


def _rc4_data_snapshot() -> dict[str, Any]:
    snapshot = _legacy_data_snapshot()
    snapshot.update(
        {
            "coverage": [
                {
                    "instrument_id": "binance:BTCUSDT",
                    "timeframe": "15m",
                    "start_utc_ms": 6_300_000,
                    "end_utc_ms": 7_199_999,
                }
            ],
            "gaps": [],
            "conflicts": [],
            "provider_revision": _provider_revision(),
        }
    )
    return snapshot


def _broker_event() -> dict[str, Any]:
    payload = _envelope("openpine.broker.v2", "2.0.0")
    payload.update(
        {
            "producer": "backtest_engine",
            "producer_version": "5.0.0-rc.5",
            "producer_commit": COMMIT_F,
            "stack_id": HASH_D,
            "kind": "event",
            "body": {
                "event_kind": "fill",
                "order_id": "long",
                "qty": "1",
                "price": "100",
            },
        }
    )
    return contracts.seal_content_hash(payload, schema_id="openpine.broker.v2")


_INTENT_BATCH_ITEMS = [_intent("close_all")]
_BROKER_EVENT_BATCH_ITEMS = [_broker_event()]
_STATE_REF = {
    "artifact_hash": HASH_A,
    "schema_id": "openpine.runtime.state.v1",
    "codec": "msgpack",
    "size_bytes": 4096,
    "uri": "file:///immutable/openpine/state-7.msgpack",
}
_PROJECTION_REF = {
    "artifact_hash": HASH_B,
    "schema_id": "openpine.broker_projection.v1",
    "codec": "json",
    "size_bytes": 2048,
    "uri": "file:///immutable/openpine/projection-7.json",
}


def _checkpoint_payload_ref() -> dict[str, Any]:
    return {
        "codec": "msgpack",
        "compression": "zstd",
        "size_bytes": 8192,
        "segment_schema_hashes": {
            "openpine.checkpoint.v1": HASH_A,
            "openpine.broker_projection.v1": HASH_B,
        },
        "uri": "s3://openpine-checkpoints/checkpoint-1.msgpack.zst",
    }


def _checkpoint_proof(
    *,
    checkpoint_id: str = "checkpoint-1",
    checkpoint_hash: str = HASH_C,
    committed_sequence: int = 9,
    committed_message_id: str = "msg-9",
    state_hash: str = HASH_A,
    broker_projection_hash: str = HASH_B,
) -> dict[str, Any]:
    payload = _envelope("openpine.checkpoint.proof.v1", "1.0.0")
    payload.update(
        {
            "producer": "openpine",
            "producer_version": "5.0.0-rc.5",
            "producer_commit": COMMIT_1,
            "stack_id": HASH_D,
            "checkpoint_id": checkpoint_id,
            "checkpoint_hash": checkpoint_hash,
            "committed_sequence": committed_sequence,
            "committed_message_id": committed_message_id,
            "state_hash": state_hash,
            "broker_projection_hash": broker_projection_hash,
            "payload_ref": _checkpoint_payload_ref(),
        }
    )
    return contracts.seal_content_hash(payload, schema_id="openpine.checkpoint.proof.v1")


WORKER_BODIES: dict[str, dict[str, Any]] = {
    "HELLO": {
        "worker_id": "worker-1",
        "protocol_version": "2.3.0",
        "capabilities": ["closed_bar", "checkpoint_v1"],
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
        "execution_context_hash": _execution_context()["content_hash"],
        "execution_context": _execution_context(),
        "semantic_profile": "strict_5x",
        "capabilities": ["closed_bar", "checkpoint_v1"],
    },
    "BAR_BEGIN": {
        "run_id": "run-1",
        "bar_index": 7,
        "bar_open_time_utc_ms": 6_300_000,
        "recalc_iteration": 0,
        "bar_hash": HASH_A,
        "bar": _canonical_bar(),
        "broker_projection": _broker_projection(),
    },
    "INTENT_BATCH": {
        "run_id": "run-1",
        "bar_index": 7,
        "recalc_iteration": 0,
        "intent_batch_hash": contracts.aggregate_batch_hash(
            _INTENT_BATCH_ITEMS,
            batch_kind="INTENT_BATCH",
            item_schema_id="openpine.intent.v2",
        ),
        "intents": _INTENT_BATCH_ITEMS,
    },
    "BROKER_EVENT_BATCH": {
        "run_id": "run-1",
        "bar_index": 7,
        "recalc_iteration": 0,
        "broker_event_batch_hash": contracts.aggregate_batch_hash(
            _BROKER_EVENT_BATCH_ITEMS,
            batch_kind="BROKER_EVENT_BATCH",
            item_schema_id="openpine.broker.v2",
        ),
        "broker_events": _BROKER_EVENT_BATCH_ITEMS,
    },
    "RECALC_REQUEST": {
        "run_id": "run-1",
        "bar_index": 7,
        "recalc_iteration": 1,
        "cause_sequence": 5,
        "broker_projection_hash": _broker_projection(1)["content_hash"],
        "broker_projection": _broker_projection(1),
    },
    "RECALC_RESULT": {
        "run_id": "run-1",
        "bar_index": 7,
        "recalc_iteration": 1,
        "intent_batch_message_id": "msg-4",
        "intent_batch_hash": contracts.aggregate_batch_hash(
            _INTENT_BATCH_ITEMS,
            batch_kind="INTENT_BATCH",
            item_schema_id="openpine.intent.v2",
        ),
    },
    "BAR_COMMIT": {
        "run_id": "run-1",
        "bar_index": 7,
        "recalc_iteration": 1,
        "state_hash": HASH_A,
        "broker_projection_hash": HASH_B,
        "state_ref": _STATE_REF,
        "broker_projection_ref": _PROJECTION_REF,
    },
    "CHECKPOINT": {
        "run_id": "run-1",
        "checkpoint_id": "checkpoint-1",
        "checkpoint_hash": HASH_C,
        "committed_sequence": 9,
        "checkpoint_ref": _checkpoint_proof(),
    },
    "RESTORE": {
        "run_id": "run-1",
        "checkpoint_id": "checkpoint-1",
        "checkpoint_hash": HASH_C,
        "committed_sequence": 9,
    },
    "FINALIZE": {
        "run_id": "run-1",
        "final_sequence": 10,
        "final_state_hash": HASH_A,
        "broker_projection_hash": HASH_B,
        "last_commit_message_id": "msg-9",
        "last_committed_sequence": 9,
    },
    "ABORT": {
        "run_id": "run-1",
        "error_code": "RUNTIME_ABORT",
        "reason": "stopped",
    },
}

_ROLE_BY_KIND = {
    "HELLO": "worker",
    "LOAD_ARTIFACT": "parent",
    "INIT_RUN": "parent",
    "BAR_BEGIN": "parent",
    "INTENT_BATCH": "worker",
    "BROKER_EVENT_BATCH": "engine",
    "RECALC_REQUEST": "engine",
    "RECALC_RESULT": "worker",
    "BAR_COMMIT": "engine",
    "CHECKPOINT": "parent",
    "RESTORE": "parent",
    "FINALIZE": "parent",
    "ABORT": "parent",
}
_COMPONENT_BY_KIND = {
    "HELLO": ("openpine", COMMIT_1),
    "LOAD_ARTIFACT": ("openpine", COMMIT_1),
    "INIT_RUN": ("openpine", COMMIT_1),
    "BAR_BEGIN": ("openpine", COMMIT_1),
    "INTENT_BATCH": ("backtest_engine", COMMIT_F),
    "BROKER_EVENT_BATCH": ("backtest_engine", COMMIT_F),
    "RECALC_REQUEST": ("backtest_engine", COMMIT_F),
    "RECALC_RESULT": ("pinelib", COMMIT_D),
    "BAR_COMMIT": ("backtest_engine", COMMIT_F),
    "CHECKPOINT": ("openpine", COMMIT_1),
    "RESTORE": ("openpine", COMMIT_1),
    "FINALIZE": ("openpine", COMMIT_1),
    "ABORT": ("openpine", COMMIT_1),
}


def _worker_message(
    kind: str,
    sequence: int = 0,
    *,
    body: dict[str, Any] | None = None,
    causation_id: str | None = None,
    **overrides: Any,
) -> dict[str, Any]:
    producer, producer_commit = _COMPONENT_BY_KIND[kind]
    payload = _envelope("openpine.worker.protocol.v2", "2.3.0")
    payload.update(
        {
            "producer": producer,
            "producer_version": "5.0.0-rc.5",
            "producer_commit": producer_commit,
            "stack_id": HASH_D,
            "message_id": f"msg-{sequence}",
            "sender_role": _ROLE_BY_KIND[kind],
            "session_id": "session-1",
            "run_id": "run-1",
            "sequence": sequence,
            "correlation_id": "correlation-1",
            "causation_id": (
                causation_id
                if causation_id is not None
                else (None if sequence == 0 else f"msg-{sequence - 1}")
            ),
            "kind": kind,
            "body": deepcopy(WORKER_BODIES[kind] if body is None else body),
        }
    )
    payload.update(overrides)
    return contracts.seal_content_hash(payload, schema_id="openpine.worker.protocol.v2")


def _valid_worker_sequence() -> list[dict[str, Any]]:
    kinds = [
        "HELLO",
        "LOAD_ARTIFACT",
        "INIT_RUN",
        "BAR_BEGIN",
        "INTENT_BATCH",
        "BROKER_EVENT_BATCH",
        "RECALC_REQUEST",
        "RECALC_RESULT",
        "INTENT_BATCH",
        "BAR_COMMIT",
        "CHECKPOINT",
        "FINALIZE",
    ]
    messages = [_worker_message(kind, index) for index, kind in enumerate(kinds)]
    second_intents = [_intent("close_all", recalc_iteration=1)]
    messages[7]["body"] = deepcopy(WORKER_BODIES["RECALC_RESULT"])
    messages[8]["body"] = dict(
        WORKER_BODIES["INTENT_BATCH"],
        recalc_iteration=1,
        intents=second_intents,
        intent_batch_hash=contracts.aggregate_batch_hash(
            second_intents,
            batch_kind="INTENT_BATCH",
            item_schema_id="openpine.intent.v2",
        ),
    )
    messages[7]["body"].update(
        intent_batch_message_id="msg-8",
        intent_batch_hash=messages[8]["body"]["intent_batch_hash"],
    )
    messages[9]["body"] = deepcopy(WORKER_BODIES["BAR_COMMIT"])
    messages[9]["body"]["recalc_iteration"] = 1
    messages[10]["body"] = deepcopy(WORKER_BODIES["CHECKPOINT"])
    messages[10]["body"].update(
        {
            "committed_sequence": 9,
            "checkpoint_ref": _checkpoint_proof(),
        }
    )
    messages[11]["body"] = deepcopy(WORKER_BODIES["FINALIZE"])
    messages[11]["body"].update(
        {
            "final_sequence": 10,
            "last_commit_message_id": "msg-9",
            "last_committed_sequence": 9,
        }
    )
    return [
        contracts.seal_content_hash(message, schema_id="openpine.worker.protocol.v2")
        for message in messages
    ]


@pytest.mark.parametrize(
    ("schema_id", "payload"),
    [
        ("openpine.execution_context.v1", _execution_context()),
        ("openpine.broker_projection.v1", _broker_projection()),
        ("openpine.checkpoint.v1", _checkpoint()),
        ("openpine.trial.identity.v1", _trial_identity()),
        ("openpine.trial.v2", _trial_lifecycle()),
    ],
)
def test_rc4_standalone_positive_fixtures_validate(schema_id: str, payload: dict[str, Any]) -> None:
    validate_payload(schema_id, payload)


def test_rc4_standalone_catalog_is_complete() -> None:
    assert set(RC4_IDS).issubset(list_schema_ids(include_aliases=False))


@pytest.mark.parametrize(
    ("schema_id", "payload"),
    [
        ("openpine.execution_context.v1", _execution_context()),
        ("openpine.broker_projection.v1", _broker_projection()),
        ("openpine.checkpoint.v1", _checkpoint()),
        ("openpine.trial.identity.v1", _trial_identity()),
    ],
)
def test_rc4_standalone_schemas_reject_unknown_root_fields(
    schema_id: str, payload: dict[str, Any]
) -> None:
    payload["unexpected"] = True
    _assert_invalid(schema_id, payload)


@pytest.mark.parametrize(
    ("schema_id", "payload"),
    [
        ("openpine.execution_context.v1", _execution_context()),
        ("openpine.broker_projection.v1", _broker_projection()),
        ("openpine.checkpoint.v1", _checkpoint()),
        ("openpine.trial.identity.v1", _trial_identity()),
        ("openpine.intent.v2", _intent("close_all")),
        ("openpine.worker.protocol.v2", _worker_message("HELLO")),
    ],
)
def test_rc4_contracts_require_exact_producer_commit(
    schema_id: str, payload: dict[str, Any]
) -> None:
    payload["producer_commit"] = "deadbeef"
    _assert_invalid(schema_id, payload)


@pytest.mark.parametrize(
    ("schema_id", "payload"),
    [
        ("openpine.execution_context.v1", _execution_context()),
        ("openpine.broker_projection.v1", _broker_projection()),
        ("openpine.checkpoint.v1", _checkpoint()),
        ("openpine.trial.identity.v1", _trial_identity()),
        ("openpine.intent.v2", _intent("close_all")),
        ("openpine.worker.protocol.v2", _worker_message("HELLO")),
        ("openpine.trial.v2", _trial_lifecycle()),
    ],
)
def test_rc4_contracts_reject_zero_envelope_hashes(schema_id: str, payload: dict[str, Any]) -> None:
    for field in ("stack_id", "content_hash"):
        invalid = deepcopy(payload)
        invalid[field] = "sha256:" + ("0" * 64)
        _assert_invalid(schema_id, invalid)


def test_execution_context_requires_complete_immutable_identity() -> None:
    for field in (
        "run_id",
        "strategy_id",
        "session_id",
        "stack_manifest_hash",
        "wheel_identities",
        "schema_hashes",
        "generated_artifact_hash",
        "source_hash",
        "emitted_module_hash",
        "data_snapshot_hash",
        "series_id",
        "instrument_id",
        "exchange",
        "market",
        "symbol",
        "timeframe",
        "timezone",
        "currency",
        "mintick",
        "pointvalue",
        "session_policy",
        "semantic_profile",
        "finality_policy",
        "warmup_policy",
        "score_policy",
        "end_policy",
        "capabilities",
        "producer_commits",
    ):
        payload = _execution_context()
        payload.pop(field)
        _assert_invalid("openpine.execution_context.v1", payload)


def test_execution_context_requires_exact_stack_wheel_identity_set() -> None:
    payload = _execution_context()
    payload["wheel_identities"] = payload["wheel_identities"][:-1]
    _assert_invalid("openpine.execution_context.v1", payload)

    payload = _execution_context()
    payload["wheel_identities"][-1] = dict(payload["wheel_identities"][0])
    _assert_invalid("openpine.execution_context.v1", payload)


def test_execution_context_rejects_bad_wheel_versions_and_placeholder_commits() -> None:
    payload = _execution_context()
    payload["wheel_identities"][0]["version"] = "latest"
    _assert_invalid("openpine.execution_context.v1", payload)

    payload = _execution_context()
    payload["producer_commits"]["openpine"] = "0" * 40
    _assert_invalid("openpine.execution_context.v1", payload)


def test_broker_projection_rejects_float_on_canonical_boundary() -> None:
    payload = _broker_projection()
    payload["cash"] = 10004.7
    _assert_invalid("openpine.broker_projection.v1", payload)

    payload = _broker_projection()
    payload["position"]["qty"] = 1.0
    _assert_invalid("openpine.broker_projection.v1", payload)


def test_broker_projection_requires_direction_and_entry_name() -> None:
    for field in ("direction", "entry_name"):
        payload = _broker_projection()
        payload["position"].pop(field)
        _assert_invalid("openpine.broker_projection.v1", payload)


def test_checkpoint_requires_atomic_pair_and_commit_boundary() -> None:
    for field in (
        "checkpoint_id",
        "run_id",
        "bar_index",
        "committed_sequence",
        "bar_commit_hash",
        "engine_checkpoint_hash",
        "worker_checkpoint_hash",
        "combined_hash",
    ):
        payload = _checkpoint()
        payload.pop(field)
        _assert_invalid("openpine.checkpoint.v1", payload)


def test_trial_identity_rejects_zero_critical_hashes_and_floats() -> None:
    payload = _trial_identity()
    payload["generated_artifact_hash"] = "sha256:" + ("0" * 64)
    _assert_invalid("openpine.trial.identity.v1", payload)

    payload = _trial_identity()
    payload["parameters"]["threshold"] = 0.5
    _assert_invalid("openpine.trial.identity.v1", payload)

    payload = _trial_identity()
    payload["parameters"]["threshold"] = 1.0
    _assert_invalid("openpine.trial.identity.v1", payload)


def test_trial_identity_rejects_duplicate_schema_ids_and_reversed_fold() -> None:
    payload = _trial_identity()
    payload["schema_set"].append({"schema_id": "openpine.intent.v2", "schema_hash": HASH_D})
    _assert_invalid("openpine.trial.identity.v1", payload)

    payload = _trial_identity()
    payload["fold"]["train_start_utc_ms"] = 20_000
    _assert_invalid("openpine.trial.identity.v1", payload)


def test_trial_identity_allows_explicit_no_fold_or_walk_forward() -> None:
    payload = _trial_identity()
    payload["fold"] = None
    payload["walk_forward"] = None
    validate_payload("openpine.trial.identity.v1", payload)


def test_trial_lifecycle_requires_identity_hash_without_identity_inputs() -> None:
    payload = _trial_lifecycle()
    payload.pop("trial_identity_hash")
    _assert_invalid("openpine.trial.v2", payload)

    payload = _trial_lifecycle()
    payload["parameters"] = {"length": 14}
    _assert_invalid("openpine.trial.v2", payload)

    payload = _trial_lifecycle()
    payload["lifecycle"] = "BOGUS"
    _assert_invalid("openpine.trial.v2", payload)

    for field, value in (
        ("runner_fingerprint", HASH_A),
        ("fold_window", {}),
        ("constraints", {}),
        ("seed", 42),
    ):
        payload = _trial_lifecycle()
        payload[field] = value
        _assert_invalid("openpine.trial.v2", payload)


@pytest.mark.parametrize(("kind", "fields"), INTENT_FIELDS.items())
def test_intent_v2_2_positive_kind_fixtures_validate(kind: str, fields: dict[str, Any]) -> None:
    validate_payload("openpine.intent.v2", _intent(kind, **fields))


FORBIDDEN_INTENT_FIELDS = {
    "entry": {"risk_rule": "max_drawdown"},
    "order": {"from_entry": "long"},
    "exit": {"direction": "SHORT"},
    "close": {"limit": "101"},
    "close_all": {"order_id": "long"},
    "cancel": {"qty": "1"},
    "cancel_all": {"order_id": "long"},
    "risk": {"order_id": "long"},
}


@pytest.mark.parametrize(("kind", "forbidden"), FORBIDDEN_INTENT_FIELDS.items())
def test_intent_v2_2_rejects_fields_from_every_other_kind(
    kind: str, forbidden: dict[str, Any]
) -> None:
    _assert_invalid("openpine.intent.v2", _intent(kind, **forbidden))


@pytest.mark.parametrize("kind", INTENT_FIELDS)
def test_intent_v2_2_rejects_unknown_fields_for_every_kind(kind: str) -> None:
    _assert_invalid("openpine.intent.v2", _intent(kind, unexpected=True))


def test_intent_source_provenance_is_exact_or_explicitly_unknown() -> None:
    validate_payload("openpine.intent.v2", _intent("close_all", source_span=_source_known()))
    validate_payload("openpine.intent.v2", _intent("close_all", source_span=_source_unknown()))

    fake_line_one = _source_unknown()
    fake_line_one.update({"start_line": 1, "end_line": 1})
    _assert_invalid("openpine.intent.v2", _intent("close_all", source_span=fake_line_one))

    missing_known = _source_known()
    missing_known.pop("start_offset")
    _assert_invalid("openpine.intent.v2", _intent("close_all", source_span=missing_known))

    reversed_span = _source_known()
    reversed_span.update({"start_offset": 20, "end_offset": 10})
    _assert_invalid("openpine.intent.v2", _intent("close_all", source_span=reversed_span))

    reversed_span = _source_known()
    reversed_span.update({"start_line": 3, "end_line": 2})
    _assert_invalid("openpine.intent.v2", _intent("close_all", source_span=reversed_span))


@pytest.mark.parametrize(
    ("target", "field", "value"),
    [
        ("bar_alias", "producer_commit", "deadbeef"),
        ("bar_alias", "producer_commit", "0" * 40),
        ("bar_alias", "stack_id", "stack-placeholder"),
        ("bar_alias", "stack_id", "sha256:" + ("0" * 64)),
        ("bar_alias", "content_hash", "sha256:abc"),
        ("bar_alias", "content_hash", "sha256:" + ("0" * 64)),
        ("bar_alias", "bar_content_hash", "sha256:abc"),
        ("bar_alias", "bar_content_hash", "sha256:" + ("0" * 64)),
        ("bar_family", "producer_commit", "deadbeef"),
        ("bar_family", "stack_id", "stack-placeholder"),
        ("bar_family", "content_hash", "sha256:" + ("0" * 64)),
        ("bar_family", "bar_content_hash", "sha256:" + ("0" * 64)),
        ("snapshot", "producer_commit", "deadbeef"),
        ("snapshot", "stack_id", "sha256:" + ("0" * 64)),
        ("snapshot", "content_hash", "sha256:" + ("0" * 64)),
        ("snapshot", "series_hash", "sha256:" + ("0" * 64)),
    ],
)
def test_marketdata_rc4_rejects_placeholder_identity_and_hashes(
    target: str, field: str, value: str
) -> None:
    if target == "bar_alias":
        schema_id = "openpine.marketdata.bar.v2"
        payload = _canonical_bar()
        payload[field] = value
    elif target == "bar_family":
        schema_id = "openpine.marketdata.v2"
        payload = _marketdata_message("bar", _canonical_bar_body())
        if field == "bar_content_hash":
            body = payload["body"]
            assert isinstance(body, dict)
            body[field] = value
        else:
            payload[field] = value
    else:
        schema_id = "openpine.marketdata.v2"
        payload = _marketdata_message("snapshot", _rc4_data_snapshot())
        if field == "series_hash":
            body = payload["body"]
            assert isinstance(body, dict)
            body[field] = value
        else:
            payload[field] = value

    _assert_invalid(schema_id, payload)


@pytest.mark.parametrize("target", ["bar_alias", "bar_family", "snapshot"])
@pytest.mark.parametrize("mode", ["omitted", "legacy_string"])
def test_marketdata_provider_revision_must_be_explicitly_discriminated(
    target: str, mode: str
) -> None:
    if target == "bar_alias":
        schema_id = "openpine.marketdata.bar.v2"
        payload = _canonical_bar()
        owner = payload
    elif target == "bar_family":
        schema_id = "openpine.marketdata.v2"
        payload = _marketdata_message("bar", _canonical_bar_body())
        owner = payload["body"]
        assert isinstance(owner, dict)
    else:
        schema_id = "openpine.marketdata.v2"
        payload = _marketdata_message("snapshot", _rc4_data_snapshot())
        owner = payload["body"]
        assert isinstance(owner, dict)

    if mode == "omitted":
        owner.pop("provider_revision", None)
    else:
        owner["provider_revision"] = "binance-42"
    _assert_invalid(schema_id, payload)


@pytest.mark.parametrize("known", [True, False])
def test_marketdata_provider_revision_accepts_only_known_or_unknown(known: bool) -> None:
    provider_revision = _provider_revision(known)

    bar = _canonical_bar()
    bar["schema_version"] = "2.1.0"
    bar["provider_revision"] = provider_revision
    bar["superseded_bar_hash"] = None
    validate_payload("openpine.marketdata.bar.v2", bar)

    bar_body = _canonical_bar_body()
    bar_body["provider_revision"] = provider_revision
    bar_body["superseded_bar_hash"] = None
    validate_payload("openpine.marketdata.v2", _marketdata_message("bar", bar_body))

    snapshot = _rc4_data_snapshot()
    snapshot["provider_revision"] = provider_revision
    validate_payload("openpine.marketdata.v2", _marketdata_message("snapshot", snapshot))


@pytest.mark.parametrize("field", ["coverage", "gaps", "conflicts"])
def test_data_snapshot_requires_typed_provenance_collections(field: str) -> None:
    snapshot = _rc4_data_snapshot()
    snapshot[field] = [{"unexpected": True}]
    _assert_invalid("openpine.marketdata.v2", _marketdata_message("snapshot", snapshot))


@pytest.mark.parametrize("field", ["coverage", "gaps", "conflicts"])
def test_data_snapshot_requires_all_provenance_collections(field: str) -> None:
    snapshot = _rc4_data_snapshot()
    snapshot.pop(field)
    _assert_invalid("openpine.marketdata.v2", _marketdata_message("snapshot", snapshot))


def test_data_snapshot_accepts_typed_coverage_gap_and_conflict_refs() -> None:
    snapshot = _rc4_data_snapshot()
    snapshot["gaps"] = [{"start_utc_ms": 6_750_000, "end_utc_ms": 6_759_999, "reason": None}]
    snapshot["conflicts"] = [
        {
            "instrument_id": "binance:BTCUSDT",
            "open_time_utc_ms": 6_300_000,
            "left_hash": HASH_A,
            "right_hash": HASH_B,
        }
    ]
    validate_payload("openpine.marketdata.v2", _marketdata_message("snapshot", snapshot))


@pytest.mark.parametrize(
    ("revision_state", "revision", "superseded_bar_hash"),
    [
        ("ORIGINAL", 1, None),
        ("ORIGINAL", 0, HASH_B),
        ("CORRECTED", 0, HASH_B),
        ("CORRECTED", 1, None),
        ("REVOKED", 0, HASH_B),
        ("REVOKED", 1, None),
    ],
)
def test_canonical_bar_rejects_invalid_revision_lineage(
    revision_state: str, revision: int, superseded_bar_hash: str | None
) -> None:
    bar = _canonical_bar()
    bar.update(
        {
            "revision_state": revision_state,
            "revision": revision,
            "superseded_bar_hash": superseded_bar_hash,
        }
    )
    _assert_invalid("openpine.marketdata.bar.v2", bar)


@pytest.mark.parametrize("revision_state", ["CORRECTED", "REVOKED"])
def test_canonical_bar_accepts_explicit_revision_lineage(revision_state: str) -> None:
    bar = _canonical_bar()
    bar.update(
        {
            "schema_version": "2.1.0",
            "provider_revision": _provider_revision(),
            "revision_state": revision_state,
            "revision": 1,
            "superseded_bar_hash": HASH_B,
        }
    )
    validate_payload("openpine.marketdata.bar.v2", bar)


@pytest.mark.parametrize(("kind", "body"), WORKER_BODIES.items())
def test_worker_v2_1_positive_kind_fixtures_validate(kind: str, body: dict[str, Any]) -> None:
    validate_payload("openpine.worker.protocol.v2", _worker_message(kind, body=body))


@pytest.mark.parametrize("kind", WORKER_BODIES)
def test_worker_v2_1_rejects_unknown_body_fields_for_every_kind(kind: str) -> None:
    body = dict(WORKER_BODIES[kind], unexpected=True)
    _assert_invalid("openpine.worker.protocol.v2", _worker_message(kind, body=body))


@pytest.mark.parametrize("kind", WORKER_BODIES)
def test_worker_v2_1_rejects_forbidden_kind_body_combinations(kind: str) -> None:
    other_kind = next(candidate for candidate in WORKER_BODIES if candidate != kind)
    _assert_invalid(
        "openpine.worker.protocol.v2",
        _worker_message(kind, body=WORKER_BODIES[other_kind]),
    )


@pytest.mark.parametrize("kind", ["PING", "PONG"])
def test_worker_v2_1_has_no_ping_or_pong(kind: str) -> None:
    payload = _worker_message("HELLO")
    payload["kind"] = kind
    _assert_invalid("openpine.worker.protocol.v2", payload)


def test_worker_v2_1_rejects_schema_invalid_nested_intent_and_broker_event() -> None:
    bad_intent = _intent("close_all", order_id="forbidden")
    body = dict(WORKER_BODIES["INTENT_BATCH"], intents=[bad_intent])
    _assert_invalid(
        "openpine.worker.protocol.v2",
        _worker_message("INTENT_BATCH", body=body),
    )

    bad_broker_event = _broker_event()
    bad_broker_body = bad_broker_event["body"]
    assert isinstance(bad_broker_body, dict)
    bad_broker_body["unexpected"] = True
    body = dict(WORKER_BODIES["BROKER_EVENT_BATCH"], broker_events=[bad_broker_event])
    _assert_invalid(
        "openpine.worker.protocol.v2",
        _worker_message("BROKER_EVENT_BATCH", body=body),
    )


def test_worker_protocol_semantic_sequence_accepts_canonical_state_machine() -> None:
    contracts.validate_worker_protocol_sequence(_valid_worker_sequence())


@pytest.mark.parametrize(
    ("mutate_index", "field", "value", "reason"),
    [
        (4, "sequence", 7, "SEQUENCE_GAP"),
        (4, "session_id", "other-session", "SESSION_ID_MISMATCH"),
        (4, "run_id", "other-run", "RUN_ID_MISMATCH"),
        (4, "stack_id", HASH_C, "STACK_ID_MISMATCH"),
        (4, "producer", "other-producer", "MESSAGE_PRODUCER_IDENTITY_MISMATCH"),
        (4, "producer_version", "5.0.1", "MESSAGE_PRODUCER_IDENTITY_MISMATCH"),
        (4, "producer_commit", COMMIT_A, "MESSAGE_PRODUCER_IDENTITY_MISMATCH"),
        (4, "correlation_id", "other-correlation", "CORRELATION_ID_MISMATCH"),
        (4, "causation_id", "other-causation", "CAUSATION_ID_MISMATCH"),
    ],
)
def test_worker_protocol_semantic_sequence_has_stable_identity_errors(
    mutate_index: int, field: str, value: Any, reason: str
) -> None:
    messages = _valid_worker_sequence()
    messages[mutate_index][field] = value
    messages[mutate_index] = contracts.seal_content_hash(
        messages[mutate_index], schema_id="openpine.worker.protocol.v2"
    )
    with pytest.raises(contracts.WorkerProtocolSemanticError) as caught:
        contracts.validate_worker_protocol_sequence(messages)
    assert caught.value.code == "WORKER_PROTOCOL_SEMANTIC_ERROR"
    assert caught.value.details["reason"] == reason


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("producer", "unknown-worker"),
        ("producer_version", "5.0.1"),
        ("producer_commit", COMMIT_A),
    ],
)
def test_worker_protocol_binds_root_producer_identity_to_execution_context(
    field: str, value: str
) -> None:
    messages = _valid_worker_sequence()
    for index, message in enumerate(messages):
        message[field] = value
        messages[index] = contracts.seal_content_hash(
            message, schema_id="openpine.worker.protocol.v2"
        )

    with pytest.raises(contracts.WorkerProtocolSemanticError) as caught:
        contracts.validate_worker_protocol_sequence(messages)

    assert caught.value.details["reason"] == "MESSAGE_PRODUCER_IDENTITY_MISMATCH"
    assert caught.value.details["field"] == field


@pytest.mark.parametrize(
    ("target", "field", "value", "reason"),
    [
        ("intent", "producer", "other-producer", "INTENT_PROVENANCE_MISMATCH"),
        ("intent", "producer_commit", COMMIT_A, "INTENT_PROVENANCE_MISMATCH"),
        ("intent", "stack_id", HASH_A, "INTENT_PROVENANCE_MISMATCH"),
        ("intent", "source_hash", HASH_A, "INTENT_PROVENANCE_MISMATCH"),
        ("bar", "producer", "other-producer", "BAR_PROVENANCE_MISMATCH"),
        ("bar", "producer_commit", COMMIT_A, "BAR_PROVENANCE_MISMATCH"),
        ("bar", "stack_id", HASH_A, "BAR_PROVENANCE_MISMATCH"),
        (
            "broker_projection",
            "producer",
            "other-producer",
            "PROJECTION_PROVENANCE_MISMATCH",
        ),
        (
            "broker_projection",
            "producer_commit",
            COMMIT_A,
            "PROJECTION_PROVENANCE_MISMATCH",
        ),
        (
            "broker_projection",
            "stack_id",
            HASH_A,
            "PROJECTION_PROVENANCE_MISMATCH",
        ),
        (
            "broker_event",
            "producer",
            "other-producer",
            "BROKER_EVENT_PROVENANCE_MISMATCH",
        ),
        (
            "broker_event",
            "producer_commit",
            COMMIT_A,
            "BROKER_EVENT_PROVENANCE_MISMATCH",
        ),
        (
            "broker_event",
            "stack_id",
            HASH_A,
            "BROKER_EVENT_PROVENANCE_MISMATCH",
        ),
    ],
)
def test_worker_protocol_rejects_nested_provenance_drift(
    target: str, field: str, value: str, reason: str
) -> None:
    messages = _valid_worker_sequence()
    if target == "intent":
        message_index = 4
        body = messages[message_index]["body"]
        assert isinstance(body, dict)
        items = body["intents"]
        assert isinstance(items, list) and items and isinstance(items[0], dict)
        nested = items[0]
        if field == "source_hash":
            source_span = nested["source_span"]
            assert isinstance(source_span, dict)
            source_span["source_hash"] = value
        else:
            nested[field] = value
        items[0] = contracts.seal_content_hash(nested, schema_id="openpine.intent.v2")
        body["intent_batch_hash"] = contracts.aggregate_batch_hash(
            items,
            batch_kind="INTENT_BATCH",
            item_schema_id="openpine.intent.v2",
        )
    elif target == "bar":
        message_index = 3
        body = messages[message_index]["body"]
        assert isinstance(body, dict)
        nested = body["bar"]
        assert isinstance(nested, dict)
        nested[field] = value
        body["bar"] = contracts.seal_content_hash(nested, schema_id="openpine.marketdata.bar.v2")
    elif target == "broker_projection":
        message_index = 3
        body = messages[message_index]["body"]
        assert isinstance(body, dict)
        nested = body["broker_projection"]
        assert isinstance(nested, dict)
        nested[field] = value
        body["broker_projection"] = contracts.seal_content_hash(
            nested, schema_id="openpine.broker_projection.v1"
        )
    else:
        message_index = 5
        body = messages[message_index]["body"]
        assert isinstance(body, dict)
        items = body["broker_events"]
        assert isinstance(items, list) and items and isinstance(items[0], dict)
        nested = items[0]
        nested[field] = value
        items[0] = contracts.seal_content_hash(nested, schema_id="openpine.broker.v2")
        body["broker_event_batch_hash"] = contracts.aggregate_batch_hash(
            items,
            batch_kind="BROKER_EVENT_BATCH",
            item_schema_id="openpine.broker.v2",
        )

    messages[message_index] = contracts.seal_content_hash(
        messages[message_index], schema_id="openpine.worker.protocol.v2"
    )
    with pytest.raises(contracts.WorkerProtocolSemanticError) as caught:
        contracts.validate_worker_protocol_sequence(messages)

    assert caught.value.details["reason"] == reason
    assert caught.value.details["field"] == field


def test_worker_protocol_semantic_sequence_rejects_forbidden_transition() -> None:
    messages = _valid_worker_sequence()
    messages[4] = _worker_message(
        "FINALIZE", 4, causation_id="msg-3", body=WORKER_BODIES["FINALIZE"]
    )
    with pytest.raises(contracts.WorkerProtocolSemanticError) as caught:
        contracts.validate_worker_protocol_sequence(messages[:5])
    assert caught.value.details["reason"] == "INVALID_TRANSITION"


def test_worker_protocol_semantic_sequence_rejects_tampered_content() -> None:
    messages = _valid_worker_sequence()
    body = messages[4]["body"]
    assert isinstance(body, dict)
    body["intent_batch_hash"] = HASH_D
    with pytest.raises(contracts.WorkerProtocolSemanticError) as caught:
        contracts.validate_worker_protocol_sequence(messages)
    assert caught.value.details["reason"] == "CONTENT_HASH_MISMATCH"


def test_worker_protocol_semantic_sequence_rejects_tampered_nested_content() -> None:
    messages = _valid_worker_sequence()
    body = messages[4]["body"]
    assert isinstance(body, dict)
    intents = body["intents"]
    assert isinstance(intents, list) and intents
    intent = intents[0]
    assert isinstance(intent, dict)
    intent["comment"] = "tampered"
    messages[4] = contracts.seal_content_hash(messages[4], schema_id="openpine.worker.protocol.v2")
    with pytest.raises(contracts.WorkerProtocolSemanticError) as caught:
        contracts.validate_worker_protocol_sequence(messages)
    assert caught.value.details["reason"] == "NESTED_CONTENT_HASH_MISMATCH"


def test_worker_protocol_semantic_sequence_rejects_truncation_and_post_terminal_messages() -> None:
    messages = _valid_worker_sequence()
    with pytest.raises(contracts.WorkerProtocolSemanticError) as caught:
        contracts.validate_worker_protocol_sequence(messages[:3])
    assert caught.value.details["reason"] == "TRUNCATED_SEQUENCE"

    messages.append(_worker_message("ABORT", 12, causation_id="msg-11"))
    with pytest.raises(contracts.WorkerProtocolSemanticError) as caught:
        contracts.validate_worker_protocol_sequence(messages)
    assert caught.value.details["reason"] == "INVALID_TRANSITION"

    messages = _valid_worker_sequence()[:3]
    messages.extend(
        [
            _worker_message("ABORT", 3, causation_id="msg-2"),
            _worker_message("ABORT", 4, causation_id="msg-3"),
        ]
    )
    with pytest.raises(contracts.WorkerProtocolSemanticError) as caught:
        contracts.validate_worker_protocol_sequence(messages)
    assert caught.value.details["reason"] == "INVALID_TRANSITION"


def test_worker_protocol_semantic_sequence_rejects_cross_message_identity_drift() -> None:
    messages = _valid_worker_sequence()
    body = messages[4]["body"]
    assert isinstance(body, dict)
    body["bar_index"] = 8
    messages[4] = contracts.seal_content_hash(messages[4], schema_id="openpine.worker.protocol.v2")
    with pytest.raises(contracts.WorkerProtocolSemanticError) as caught:
        contracts.validate_worker_protocol_sequence(messages)
    assert caught.value.details["reason"] == "BAR_IDENTITY_MISMATCH"

    messages = _valid_worker_sequence()
    body = messages[2]["body"]
    assert isinstance(body, dict)
    execution_context = body["execution_context"]
    assert isinstance(execution_context, dict)
    execution_context["run_id"] = "other-run"
    execution_context = contracts.seal_content_hash(
        execution_context, schema_id="openpine.execution_context.v1"
    )
    body["execution_context"] = execution_context
    body["execution_context_hash"] = execution_context["content_hash"]
    messages[2] = contracts.seal_content_hash(messages[2], schema_id="openpine.worker.protocol.v2")
    with pytest.raises(contracts.WorkerProtocolSemanticError) as caught:
        contracts.validate_worker_protocol_sequence(messages)
    assert caught.value.details["reason"] == "EXECUTION_CONTEXT_IDENTITY_MISMATCH"

    messages = _valid_worker_sequence()
    body = messages[4]["body"]
    assert isinstance(body, dict)
    intents = body["intents"]
    assert isinstance(intents, list) and intents
    intent = intents[0]
    assert isinstance(intent, dict)
    intent["run_id"] = "other-run"
    intents[0] = contracts.seal_content_hash(intent, schema_id="openpine.intent.v2")
    body["intent_batch_hash"] = contracts.aggregate_batch_hash(
        intents,
        batch_kind="INTENT_BATCH",
        item_schema_id="openpine.intent.v2",
    )
    messages[4] = contracts.seal_content_hash(messages[4], schema_id="openpine.worker.protocol.v2")
    with pytest.raises(contracts.WorkerProtocolSemanticError) as caught:
        contracts.validate_worker_protocol_sequence(messages)
    assert caught.value.details["reason"] == "INTENT_IDENTITY_MISMATCH"

    messages = _valid_worker_sequence()
    body = messages[3]["body"]
    assert isinstance(body, dict)
    projection = body["broker_projection"]
    assert isinstance(projection, dict)
    projection["bar_index"] = 8
    body["broker_projection"] = contracts.seal_content_hash(
        projection, schema_id="openpine.broker_projection.v1"
    )
    messages[3] = contracts.seal_content_hash(messages[3], schema_id="openpine.worker.protocol.v2")
    with pytest.raises(contracts.WorkerProtocolSemanticError) as caught:
        contracts.validate_worker_protocol_sequence(messages)
    assert caught.value.details["reason"] == "PROJECTION_IDENTITY_MISMATCH"


def test_worker_protocol_semantic_sequence_rejects_invalid_sequence_references() -> None:
    cases = [
        (6, "cause_sequence", 4, "CAUSE_SEQUENCE_MISMATCH"),
        (10, "committed_sequence", 8, "CHECKPOINT_COMMIT_MISMATCH"),
        (11, "final_sequence", 9, "FINAL_SEQUENCE_MISMATCH"),
    ]
    for index, field, value, reason in cases:
        messages = _valid_worker_sequence()
        body = messages[index]["body"]
        assert isinstance(body, dict)
        body[field] = value
        messages[index] = contracts.seal_content_hash(
            messages[index], schema_id="openpine.worker.protocol.v2"
        )
        with pytest.raises(contracts.WorkerProtocolSemanticError) as caught:
            contracts.validate_worker_protocol_sequence(messages)
        assert caught.value.details["reason"] == reason


def test_recalc_request_rejects_projection_hash_and_identity_drift() -> None:
    messages = _valid_worker_sequence()
    body = messages[6]["body"]
    assert isinstance(body, dict)
    body["broker_projection_hash"] = HASH_A
    messages[6] = contracts.seal_content_hash(messages[6], schema_id="openpine.worker.protocol.v2")
    with pytest.raises(contracts.WorkerProtocolSemanticError) as caught:
        contracts.validate_worker_protocol_sequence(messages)
    assert caught.value.details["reason"] == "PROJECTION_HASH_MISMATCH"

    messages = _valid_worker_sequence()
    body = messages[6]["body"]
    assert isinstance(body, dict)
    projection = body["broker_projection"]
    assert isinstance(projection, dict)
    projection["bar_index"] = 8
    projection = contracts.seal_content_hash(projection, schema_id="openpine.broker_projection.v1")
    body["broker_projection"] = projection
    body["broker_projection_hash"] = projection["content_hash"]
    messages[6] = contracts.seal_content_hash(messages[6], schema_id="openpine.worker.protocol.v2")
    with pytest.raises(contracts.WorkerProtocolSemanticError) as caught:
        contracts.validate_worker_protocol_sequence(messages)
    assert caught.value.details["reason"] == "PROJECTION_IDENTITY_MISMATCH"


def test_schema_generation_is_deterministic_and_idempotent(tmp_path: Path) -> None:
    import scripts.generate_schemas as generator

    generator.OUT = tmp_path
    generator.main()
    first = {path.name: path.read_bytes() for path in sorted(tmp_path.glob("*.json"))}
    generator.main()
    second = {path.name: path.read_bytes() for path in sorted(tmp_path.glob("*.json"))}
    committed = {
        path.name: path.read_bytes()
        for path in sorted(
            (Path(__file__).resolve().parents[1] / "openpine_contracts" / "schemas").glob("*.json")
        )
    }

    assert first == second
    assert first == committed


@pytest.mark.parametrize("fault", ["old_batch", "wrong_id", "wrong_hash"])
def test_recalc_result_binds_following_not_previous_batch(fault):
    messages = _valid_worker_sequence()
    body = messages[7]["body"]
    if fault == "old_batch":
        body["intent_batch_message_id"] = messages[4]["message_id"]
        body["intent_batch_hash"] = messages[4]["body"]["intent_batch_hash"]
    elif fault == "wrong_id":
        body["intent_batch_message_id"] = "not-the-next-message"
    else:
        body["intent_batch_hash"] = messages[4]["body"]["intent_batch_hash"]
    messages[7] = contracts.seal_content_hash(messages[7], schema_id="openpine.worker.protocol.v2")
    with pytest.raises(contracts.WorkerProtocolSemanticError) as error:
        contracts.validate_worker_protocol_sequence(messages)
    assert error.value.details["reason"] == "RECALC_INTENT_BINDING_MISMATCH"
