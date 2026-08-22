#!/usr/bin/env python3
"""Generate packaged JSON Schema catalog for openpine-contracts."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "openpine_contracts" / "schemas"
SEMVER_PATTERN = (
    r"^(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)"
    r"(?:-[0-9A-Za-z.-]+)?(?:\+[0-9A-Za-z.-]+)?$"
)

ENVELOPE_PROPS = {
    "schema_id": {"type": "string", "minLength": 1},
    "schema_version": {
        "type": "string",
        "pattern": SEMVER_PATTERN,
    },
    "producer": {"type": "string", "minLength": 1},
    "producer_version": {
        "type": "string",
        "pattern": SEMVER_PATTERN,
    },
    "producer_commit": {"type": "string", "minLength": 1},
    "stack_id": {"type": "string", "minLength": 1},
    "created_at_utc_ms": {"type": "integer", "minimum": 0},
    "serializer_id": {"const": "openpine.canonical.json.v1"},
    "content_hash_alg": {"const": "sha256"},
    "content_hash": {"type": "string", "pattern": "^sha256:[0-9a-f]{64}$"},
}
ENVELOPE_REQUIRED = list(ENVELOPE_PROPS)

DECIMAL = {"type": "string", "minLength": 1, "pattern": r"^-?(?:0|[1-9][0-9]*)(?:\.[0-9]+)?$"}
DECIMAL_OR_NULL = {"anyOf": [DECIMAL, {"type": "null"}]}
SHA = {"type": "string", "pattern": r"^sha256:[0-9a-f]{64}$"}
GIT_SHA = {"type": "string", "pattern": r"^[0-9a-f]{40}$"}
NONEMPTY_STRING = {"type": "string", "minLength": 1}
SUPPORT = {"enum": ["SUPPORTED", "CONDITIONAL", "VISUAL_ONLY", "UNSUPPORTED", "NOT_APPLICABLE"]}
JSON_NO_FLOAT = {
    "anyOf": [
        {"type": "null"},
        {"type": "boolean"},
        {"type": "integer"},
        {"type": "string"},
        {"type": "array", "items": {"$ref": "#/$defs/JsonNoFloat"}},
        {
            "type": "object",
            "additionalProperties": {"$ref": "#/$defs/JsonNoFloat"},
        },
    ]
}


def schema(
    schema_id: str,
    *,
    required: list[str],
    properties: dict,
    defs: dict | None = None,
    extra: dict | None = None,
) -> dict:
    props = dict(ENVELOPE_PROPS)
    props["schema_id"] = {"const": schema_id}
    props.update(properties)
    required_fields = list(dict.fromkeys(ENVELOPE_REQUIRED + required))
    out = {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "$id": schema_id,
        "type": "object",
        "additionalProperties": False,
        "required": required_fields,
        "properties": props,
    }
    if defs:
        out["$defs"] = defs
    if extra:
        out.update(extra)
    return out


def kind_if_then(kind: str, def_name: str) -> dict:
    return {
        "if": {"properties": {"kind": {"const": kind}}, "required": ["kind"]},
        "then": {"properties": {"body": {"$ref": f"#/$defs/{def_name}"}}},
    }


def kind_require(kind: str, *required: str) -> dict:
    return {
        "if": {"properties": {"kind": {"const": kind}}, "required": ["kind"]},
        "then": {"required": list(required)},
    }


def strict_object(required: list[str], properties: dict) -> dict:
    return {
        "type": "object",
        "additionalProperties": False,
        "required": required,
        "properties": properties,
    }


def write(name: str, payload: dict) -> None:
    path = OUT / name
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)

    write(
        "openpine.event.v1.json",
        schema(
            "openpine.event.v1",
            required=[
                "event_id",
                "event_type",
                "sequence",
                "occurred_at_utc_ms",
                "observed_at_utc_ms",
                "payload_hash",
                "payload",
            ],
            properties={
                "event_id": {"type": "string", "minLength": 1},
                "event_type": {"type": "string", "minLength": 1},
                "run_id": {"type": ["string", "null"]},
                "sequence": {"type": "integer", "minimum": 0},
                "correlation_id": {"type": ["string", "null"]},
                "causation_id": {"type": ["string", "null"]},
                "idempotency_key": {"type": ["string", "null"]},
                "occurred_at_utc_ms": {"type": "integer"},
                "observed_at_utc_ms": {"type": "integer"},
                "phase": {"type": ["string", "null"]},
                "payload_hash": SHA,
                "payload": {"$ref": "#/$defs/JsonObjectNoFloat"},
            },
            defs={
                "JsonNoFloat": JSON_NO_FLOAT,
                "JsonObjectNoFloat": {
                    "type": "object",
                    "additionalProperties": {"$ref": "#/$defs/JsonNoFloat"},
                },
            },
        ),
    )

    support_dims = {
        name: SUPPORT
        for name in (
            "parse",
            "bind_type",
            "lower",
            "runtime",
            "data_mtf",
            "simulation",
            "live_safe",
            "visual",
            "numeric_parity",
        )
    }
    write(
        "openpine.support_profile.v2.json",
        schema(
            "openpine.support_profile.v2",
            required=["features"],
            properties={
                "features": {
                    "type": "array",
                    "items": {"$ref": "#/$defs/FeatureSupport"},
                }
            },
            defs={
                "FeatureSupport": {
                    "type": "object",
                    "additionalProperties": False,
                    "required": ["feature_id", *support_dims],
                    "properties": {
                        "feature_id": {"type": "string", "minLength": 1},
                        **support_dims,
                        "capability_predicate": {"type": ["string", "null"]},
                        "limitation_code": {"type": ["string", "null"]},
                        "fixture_id": {"type": ["string", "null"]},
                    },
                }
            },
        ),
    )

    write(
        "pine.ast.v1.json",
        schema(
            "pine.ast.v1",
            required=["pine_version", "nodes", "diagnostics"],
            properties={
                "pine_version": {"type": "string", "minLength": 1},
                "source_hash": SHA,
                "nodes": {
                    "type": "array",
                    "items": {"$ref": "#/$defs/AstNode"},
                },
                "diagnostics": {
                    "type": "array",
                    "items": {"$ref": "#/$defs/Diagnostic"},
                },
            },
            defs={
                "Span": {
                    "type": "object",
                    "additionalProperties": False,
                    "required": ["start_line", "start_col", "end_line", "end_col"],
                    "properties": {
                        "start_line": {"type": "integer", "minimum": 1},
                        "start_col": {"type": "integer", "minimum": 0},
                        "end_line": {"type": "integer", "minimum": 1},
                        "end_col": {"type": "integer", "minimum": 0},
                    },
                },
                "AstNode": {
                    "type": "object",
                    "additionalProperties": False,
                    "required": ["node_id", "kind", "span"],
                    "properties": {
                        "node_id": {"type": "string", "minLength": 1},
                        "kind": {"type": "string", "minLength": 1},
                        "span": {"$ref": "#/$defs/Span"},
                        "children": {"type": "array", "items": {"type": "string"}},
                    },
                },
                "Diagnostic": {
                    "type": "object",
                    "additionalProperties": False,
                    "required": ["code", "message"],
                    "properties": {
                        "code": {"type": "string"},
                        "message": {"type": "string"},
                        "node_id": {"type": ["string", "null"]},
                    },
                },
            },
        ),
    )

    write(
        "openpine.frontend.v2.json",
        schema(
            "openpine.frontend.v2",
            required=["declarations", "inputs", "support_profile_ref"],
            properties={
                "declarations": {"type": "object"},
                "inputs": {"type": "array", "items": {"type": "object"}},
                "strategy_settings": {"type": "object"},
                "referenced_builtins": {"type": "array", "items": {"type": "string"}},
                "request_usage": {"type": "array", "items": {"type": "string"}},
                "visual_requirements": {"type": "array", "items": {"type": "string"}},
                "static_resource_budgets": {"type": "object"},
                "support_profile_ref": SHA,
                "semantic_profile": {"enum": ["legacy_4x", "strict_5x"]},
            },
        ),
    )

    write(
        "openpine.generated_artifact.v2.json",
        schema(
            "openpine.generated_artifact.v2",
            required=[
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
            properties={
                "source_hash": SHA,
                "frontend_artifact_hash": SHA,
                "ast_hash": SHA,
                "emitted_module_hash": SHA,
                "source_map_hash": SHA,
                "support_profile_hash": SHA,
                "lowering_version": {"type": "string", "minLength": 1},
                "producer_commits": {
                    "type": "object",
                    "additionalProperties": False,
                    "required": [
                        "pine2ast",
                        "ast2python",
                        "pinelib",
                        "openpine-contracts",
                    ],
                    "properties": {
                        "pine2ast": GIT_SHA,
                        "ast2python": GIT_SHA,
                        "pinelib": GIT_SHA,
                        "openpine-contracts": GIT_SHA,
                    },
                },
                "semantic_profile": {"enum": ["legacy_4x", "strict_5x"]},
                "numeric_policy": {"type": "string"},
                "required_runtime_capabilities": {
                    "type": "array",
                    "uniqueItems": True,
                    "items": NONEMPTY_STRING,
                },
                "import_allowlist": {
                    "type": "array",
                    "uniqueItems": True,
                    "items": {
                        "type": "string",
                        "pattern": r"^[A-Za-z_][A-Za-z0-9_]*(?:\.[A-Za-z_][A-Za-z0-9_]*)*$",
                    },
                },
                "entrypoint_module": {
                    "type": "string",
                    "pattern": r"^[A-Za-z_][A-Za-z0-9_]*(?:\.[A-Za-z_][A-Za-z0-9_]*)*$",
                },
                "entrypoint_class": {
                    "type": "string",
                    "pattern": r"^[A-Za-z_][A-Za-z0-9_]*$",
                },
                "resource_estimate": {"type": "object"},
                "signature_ref": {"type": ["string", "null"]},
            },
        ),
    )

    write(
        "openpine.runtime.v2.json",
        schema(
            "openpine.runtime.v2",
            required=["available_capabilities", "bar_update_mode"],
            properties={
                "available_capabilities": {"type": "array", "items": {"type": "string"}},
                "bar_update_mode": {"type": "string", "minLength": 1},
                "mtf_provider_port": {"type": ["string", "null"]},
                "deterministic_clock": {"type": "boolean"},
                "deterministic_rng": {"type": "boolean"},
                "intent_sink": {"type": "string"},
                "visual_sink": {"type": ["string", "null"]},
                "resource_limits": {"type": "object"},
                "fills_api_present": {"const": False},
            },
        ),
    )

    bar_props = {
        "series_id": {"type": "string", "minLength": 1},
        "instrument_id": {"type": "string", "minLength": 1},
        "timeframe": {"type": "string", "minLength": 1},
        "open_time_utc_ms": {"type": "integer"},
        "close_time_utc_ms": {"type": "integer"},
        "open": DECIMAL,
        "high": DECIMAL,
        "low": DECIMAL,
        "close": DECIMAL,
        "volume": DECIMAL,
        "volume_scale": {"type": ["integer", "null"], "minimum": 0},
        "finality": {"enum": ["OPEN", "FINAL"]},
        "revision_state": {"enum": ["ORIGINAL", "CORRECTED", "REVOKED"]},
        "revision": {"type": "integer", "minimum": 0},
        "provider": {"type": "string", "minLength": 1},
        "snapshot_id": {"type": "string", "minLength": 1},
        "provider_revision": {"type": ["string", "null"]},
        "observed_at_utc_ms": {"type": ["integer", "null"]},
        "ingested_at_utc_ms": {"type": ["integer", "null"]},
        "session_id": {"type": ["string", "null"]},
        "bar_content_hash": SHA,
        "superseded_bar_hash": {"type": ["string", "null"]},
    }
    bar_required = [
        "series_id",
        "instrument_id",
        "timeframe",
        "open_time_utc_ms",
        "close_time_utc_ms",
        "open",
        "high",
        "low",
        "close",
        "volume",
        "finality",
        "revision_state",
        "revision",
        "provider",
        "snapshot_id",
        "bar_content_hash",
    ]

    write(
        "openpine.marketdata.bar.v2.json",
        schema("openpine.marketdata.bar.v2", required=bar_required, properties=bar_props),
    )

    write(
        "openpine.marketdata.v2.json",
        schema(
            "openpine.marketdata.v2",
            required=["kind", "body"],
            properties={
                "kind": {
                    "enum": [
                        "instrument",
                        "instrument_rules",
                        "timeframe",
                        "bar",
                        "query",
                        "snapshot",
                        "coverage",
                        "gap",
                        "conflict",
                        "provider_revision",
                        "stream_cursor",
                    ]
                },
                "body": {"type": "object"},
            },
            defs={
                "CanonicalBar": {
                    "type": "object",
                    "additionalProperties": False,
                    "required": bar_required,
                    "properties": bar_props,
                },
                "DataQuery": {
                    "type": "object",
                    "additionalProperties": False,
                    "required": [
                        "instrument_id",
                        "timeframe",
                        "start_utc_ms",
                        "end_utc_ms",
                        "finality_policy",
                    ],
                    "properties": {
                        "instrument_id": {"type": "string"},
                        "timeframe": {"type": "string"},
                        "start_utc_ms": {"type": "integer"},
                        "end_utc_ms": {"type": "integer"},
                        "finality_policy": {"enum": ["CLOSED_BAR_ONLY", "ALLOW_OPEN"]},
                        "provider": {"type": ["string", "null"]},
                        "session_policy": {"type": ["string", "null"]},
                        "adjustment_policy": {"type": ["string", "null"]},
                        "requested_snapshot_id": {"type": ["string", "null"]},
                    },
                },
                "DataSnapshot": {
                    "type": "object",
                    "additionalProperties": False,
                    "required": [
                        "snapshot_id",
                        "query",
                        "bar_count",
                        "series_hash",
                        "created_at_utc_ms",
                    ],
                    "properties": {
                        "snapshot_id": {"type": "string"},
                        "query": {"$ref": "#/$defs/DataQuery"},
                        "bar_count": {"type": "integer", "minimum": 0},
                        "series_hash": SHA,
                        "coverage": {"type": "array", "items": {"type": "object"}},
                        "gaps": {"type": "array", "items": {"type": "object"}},
                        "conflicts": {"type": "array", "items": {"type": "object"}},
                        "provider_revision": {"type": ["string", "null"]},
                        "created_at_utc_ms": {"type": "integer", "minimum": 0},
                    },
                },
                "Instrument": {
                    "type": "object",
                    "additionalProperties": False,
                    "required": ["instrument_id"],
                    "properties": {
                        "instrument_id": {"type": "string", "minLength": 1},
                        "symbol": {"type": "string"},
                        "exchange": {"type": "string"},
                    },
                },
                "InstrumentRules": {
                    "type": "object",
                    "additionalProperties": False,
                    "required": ["instrument_id", "tick_size"],
                    "properties": {
                        "instrument_id": {"type": "string", "minLength": 1},
                        "tick_size": DECIMAL,
                        "qty_step": DECIMAL_OR_NULL,
                    },
                },
                "Timeframe": {
                    "type": "object",
                    "additionalProperties": False,
                    "required": ["timeframe"],
                    "properties": {"timeframe": {"type": "string", "minLength": 1}},
                },
                "Coverage": {
                    "type": "object",
                    "additionalProperties": False,
                    "required": ["instrument_id", "timeframe", "start_utc_ms", "end_utc_ms"],
                    "properties": {
                        "instrument_id": {"type": "string"},
                        "timeframe": {"type": "string"},
                        "start_utc_ms": {"type": "integer"},
                        "end_utc_ms": {"type": "integer"},
                    },
                },
                "Gap": {
                    "type": "object",
                    "additionalProperties": False,
                    "required": ["start_utc_ms", "end_utc_ms"],
                    "properties": {
                        "start_utc_ms": {"type": "integer"},
                        "end_utc_ms": {"type": "integer"},
                        "reason": {"type": ["string", "null"]},
                    },
                },
                "Conflict": {
                    "type": "object",
                    "additionalProperties": False,
                    "required": ["instrument_id", "open_time_utc_ms"],
                    "properties": {
                        "instrument_id": {"type": "string"},
                        "open_time_utc_ms": {"type": "integer"},
                        "left_hash": SHA,
                        "right_hash": SHA,
                    },
                },
                "ProviderRevision": {
                    "type": "object",
                    "additionalProperties": False,
                    "required": ["revision"],
                    "properties": {
                        "revision": {"type": "string", "minLength": 1},
                        "provider": {"type": ["string", "null"]},
                    },
                },
                "StreamCursor": {
                    "type": "object",
                    "additionalProperties": False,
                    "required": ["cursor"],
                    "properties": {
                        "cursor": {"type": "string", "minLength": 1},
                        "instrument_id": {"type": ["string", "null"]},
                    },
                },
            },
            extra={
                "allOf": [
                    kind_if_then("instrument", "Instrument"),
                    kind_if_then("instrument_rules", "InstrumentRules"),
                    kind_if_then("timeframe", "Timeframe"),
                    kind_if_then("bar", "CanonicalBar"),
                    kind_if_then("query", "DataQuery"),
                    kind_if_then("snapshot", "DataSnapshot"),
                    kind_if_then("coverage", "Coverage"),
                    kind_if_then("gap", "Gap"),
                    kind_if_then("conflict", "Conflict"),
                    kind_if_then("provider_revision", "ProviderRevision"),
                    kind_if_then("stream_cursor", "StreamCursor"),
                ]
            },
        ),
    )

    write(
        "openpine.intent.v2.json",
        schema(
            "openpine.intent.v2",
            required=[
                "event_id",
                "sequence",
                "command_id",
                "kind",
                "run_id",
                "strategy_id",
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
            ],
            properties={
                "schema_version": {"const": "2.1.0"},
                "event_id": NONEMPTY_STRING,
                "sequence": {"type": "integer", "minimum": 0},
                "command_id": NONEMPTY_STRING,
                "kind": {
                    "enum": [
                        "entry",
                        "order",
                        "exit",
                        "close",
                        "close_all",
                        "cancel",
                        "cancel_all",
                        "risk",
                    ]
                },
                "run_id": NONEMPTY_STRING,
                "strategy_id": NONEMPTY_STRING,
                "series_id": NONEMPTY_STRING,
                "instrument_id": NONEMPTY_STRING,
                "timeframe": NONEMPTY_STRING,
                "bar_index": {"type": "integer", "minimum": 0},
                "bar_open_time_utc_ms": {"type": "integer", "minimum": 0},
                "phase": NONEMPTY_STRING,
                "recalc_iteration": {"type": "integer", "minimum": 0},
                "source_span": {"$ref": "#/$defs/SourceSpan"},
                "semantic_profile": {"enum": ["legacy_4x", "strict_5x"]},
                "idempotency_key": NONEMPTY_STRING,
                "origin_command_kind": {"type": "string"},
                "order_id": NONEMPTY_STRING,
                "direction": {"enum": ["LONG", "SHORT", "long", "short"]},
                "qty": DECIMAL,
                "qty_percent": DECIMAL,
                "price": DECIMAL_OR_NULL,
                "stop": DECIMAL_OR_NULL,
                "limit": DECIMAL_OR_NULL,
                "profit": DECIMAL_OR_NULL,
                "loss": DECIMAL_OR_NULL,
                "trail_price": DECIMAL_OR_NULL,
                "trail_points": DECIMAL_OR_NULL,
                "trail_offset": DECIMAL_OR_NULL,
                "from_entry": NONEMPTY_STRING,
                "oca_name": {"type": ["string", "null"]},
                "oca_type": {"type": ["string", "null"]},
                "comment": {"type": ["string", "null"]},
                "immediately": {"type": "boolean"},
                "risk_rule": NONEMPTY_STRING,
                "risk_value": DECIMAL,
                "risk_unit": NONEMPTY_STRING,
                "risk_scope": NONEMPTY_STRING,
            },
            defs={
                "SourceSpan": {
                    "type": "object",
                    "additionalProperties": False,
                    "required": [
                        "start_offset",
                        "end_offset",
                        "start_line",
                        "start_col",
                        "end_line",
                        "end_col",
                    ],
                    "properties": {
                        "start_offset": {"type": "integer", "minimum": 0},
                        "end_offset": {"type": "integer", "minimum": 0},
                        "start_line": {"type": "integer", "minimum": 1},
                        "start_col": {"type": "integer", "minimum": 0},
                        "end_line": {"type": "integer", "minimum": 1},
                        "end_col": {"type": "integer", "minimum": 0},
                    },
                }
            },
            extra={
                "allOf": [
                    kind_require("entry", "order_id", "direction", "qty"),
                    kind_require("order", "order_id", "direction", "qty"),
                    kind_require("exit", "order_id", "from_entry"),
                    kind_require("close", "from_entry"),
                    kind_require("close_all"),
                    kind_require("cancel", "order_id"),
                    kind_require("cancel_all"),
                    kind_require("risk", "risk_rule", "risk_value", "risk_unit", "risk_scope"),
                ]
            },
        ),
    )

    write(
        "openpine.broker.v2.json",
        schema(
            "openpine.broker.v2",
            required=["kind", "body"],
            properties={
                "kind": {
                    "enum": [
                        "command",
                        "event",
                        "order_projection",
                        "position_projection",
                        "account_snapshot",
                        "reconciliation_report",
                    ]
                },
                "body": {"type": "object"},
            },
            defs={
                "BrokerCommand": {
                    "type": "object",
                    "additionalProperties": False,
                    "required": ["command_id", "command_kind", "idempotency_key"],
                    "properties": {
                        "command_id": {"type": "string"},
                        "command_kind": {"type": "string"},
                        "idempotency_key": {"type": "string"},
                        "intent_id": {"type": ["string", "null"]},
                    },
                },
                "BrokerEvent": {
                    "type": "object",
                    "additionalProperties": False,
                    "required": ["event_kind", "order_id"],
                    "properties": {
                        "event_kind": {
                            "enum": [
                                "accepted",
                                "rejected",
                                "partial",
                                "fill",
                                "cancel",
                                "expire",
                            ]
                        },
                        "order_id": {"type": "string"},
                        "qty": DECIMAL,
                        "price": DECIMAL,
                    },
                },
                "OrderProjection": {
                    "type": "object",
                    "additionalProperties": False,
                    "required": ["order_id", "state"],
                    "properties": {
                        "order_id": {"type": "string", "minLength": 1},
                        "state": {"type": "string", "minLength": 1},
                        "qty": DECIMAL,
                        "price": DECIMAL_OR_NULL,
                    },
                },
                "PositionProjection": {
                    "type": "object",
                    "additionalProperties": False,
                    "required": ["instrument_id", "qty"],
                    "properties": {
                        "instrument_id": {"type": "string", "minLength": 1},
                        "qty": DECIMAL,
                        "avg_price": DECIMAL_OR_NULL,
                    },
                },
                "AccountSnapshot": {
                    "type": "object",
                    "additionalProperties": False,
                    "required": ["cash", "equity"],
                    "properties": {
                        "cash": DECIMAL,
                        "equity": DECIMAL,
                        "currency": {"type": "string", "minLength": 1},
                    },
                },
                "ReconciliationReport": {
                    "type": "object",
                    "additionalProperties": False,
                    "required": ["ok"],
                    "properties": {
                        "ok": {"type": "boolean"},
                        "conflicts": {"type": "array", "items": {"type": "string"}},
                    },
                },
            },
            extra={
                "allOf": [
                    kind_if_then("command", "BrokerCommand"),
                    kind_if_then("event", "BrokerEvent"),
                    kind_if_then("order_projection", "OrderProjection"),
                    kind_if_then("position_projection", "PositionProjection"),
                    kind_if_then("account_snapshot", "AccountSnapshot"),
                    kind_if_then("reconciliation_report", "ReconciliationReport"),
                ]
            },
        ),
    )

    write(
        "openpine.worker.protocol.v2.json",
        schema(
            "openpine.worker.protocol.v2",
            required=["kind", "body"],
            properties={
                "kind": {
                    "enum": [
                        "HELLO",
                        "LOAD_ARTIFACT",
                        "INIT_RUN",
                        "BAR_BEGIN",
                        "INTENT_BATCH",
                        "BROKER_EVENT_BATCH",
                        "RECALC_REQUEST",
                        "RECALC_RESULT",
                        "BAR_COMMIT",
                        "CHECKPOINT",
                        "RESTORE",
                        "FINALIZE",
                        "ABORT",
                    ]
                },
                "body": {"type": "object"},
            },
            defs={
                "Hello": strict_object(
                    ["worker_id", "protocol_version", "capabilities"],
                    {
                        "worker_id": NONEMPTY_STRING,
                        "protocol_version": NONEMPTY_STRING,
                        "capabilities": {"type": "array", "items": NONEMPTY_STRING},
                    },
                ),
                "LoadArtifact": strict_object(
                    ["artifact_hash", "module_hash", "entrypoint_module", "entrypoint_class"],
                    {
                        "artifact_hash": SHA,
                        "module_hash": SHA,
                        "entrypoint_module": NONEMPTY_STRING,
                        "entrypoint_class": NONEMPTY_STRING,
                    },
                ),
                "InitRun": strict_object(
                    ["run_id", "run_hash", "semantic_profile", "capabilities"],
                    {
                        "run_id": NONEMPTY_STRING,
                        "run_hash": SHA,
                        "semantic_profile": {"enum": ["legacy_4x", "strict_5x"]},
                        "capabilities": {"type": "array", "items": NONEMPTY_STRING},
                    },
                ),
                "BarBegin": strict_object(
                    [
                        "run_id",
                        "bar_index",
                        "bar_open_time_utc_ms",
                        "recalc_iteration",
                        "bar_hash",
                    ],
                    {
                        "run_id": NONEMPTY_STRING,
                        "bar_index": {"type": "integer", "minimum": 0},
                        "bar_open_time_utc_ms": {"type": "integer", "minimum": 0},
                        "recalc_iteration": {"type": "integer", "minimum": 0},
                        "bar_hash": SHA,
                    },
                ),
                "IntentBatch": strict_object(
                    ["run_id", "bar_index", "recalc_iteration", "intents"],
                    {
                        "run_id": NONEMPTY_STRING,
                        "bar_index": {"type": "integer", "minimum": 0},
                        "recalc_iteration": {"type": "integer", "minimum": 0},
                        "intents": {"type": "array", "items": {"type": "object"}},
                    },
                ),
                "BrokerEventBatch": strict_object(
                    ["run_id", "bar_index", "recalc_iteration", "broker_events"],
                    {
                        "run_id": NONEMPTY_STRING,
                        "bar_index": {"type": "integer", "minimum": 0},
                        "recalc_iteration": {"type": "integer", "minimum": 0},
                        "broker_events": {"type": "array", "items": {"type": "object"}},
                    },
                ),
                "RecalcRequest": strict_object(
                    ["run_id", "bar_index", "recalc_iteration", "cause_sequence"],
                    {
                        "run_id": NONEMPTY_STRING,
                        "bar_index": {"type": "integer", "minimum": 0},
                        "recalc_iteration": {"type": "integer", "minimum": 1},
                        "cause_sequence": {"type": "integer", "minimum": 0},
                    },
                ),
                "RecalcResult": strict_object(
                    ["run_id", "bar_index", "recalc_iteration", "intent_batch_hash"],
                    {
                        "run_id": NONEMPTY_STRING,
                        "bar_index": {"type": "integer", "minimum": 0},
                        "recalc_iteration": {"type": "integer", "minimum": 1},
                        "intent_batch_hash": SHA,
                    },
                ),
                "BarCommit": strict_object(
                    ["run_id", "bar_index", "recalc_iteration", "state_hash"],
                    {
                        "run_id": NONEMPTY_STRING,
                        "bar_index": {"type": "integer", "minimum": 0},
                        "recalc_iteration": {"type": "integer", "minimum": 0},
                        "state_hash": SHA,
                    },
                ),
                "Checkpoint": strict_object(
                    ["run_id", "checkpoint_id", "checkpoint_hash"],
                    {
                        "run_id": NONEMPTY_STRING,
                        "checkpoint_id": NONEMPTY_STRING,
                        "checkpoint_hash": SHA,
                    },
                ),
                "Restore": strict_object(
                    ["run_id", "checkpoint_id", "checkpoint_hash"],
                    {
                        "run_id": NONEMPTY_STRING,
                        "checkpoint_id": NONEMPTY_STRING,
                        "checkpoint_hash": SHA,
                    },
                ),
                "Finalize": strict_object(
                    ["run_id", "final_sequence"],
                    {
                        "run_id": NONEMPTY_STRING,
                        "final_sequence": {"type": "integer", "minimum": 0},
                    },
                ),
                "Abort": strict_object(
                    ["run_id", "error_code", "reason"],
                    {
                        "run_id": NONEMPTY_STRING,
                        "error_code": NONEMPTY_STRING,
                        "reason": NONEMPTY_STRING,
                    },
                ),
            },
            extra={
                "allOf": [
                    kind_if_then("HELLO", "Hello"),
                    kind_if_then("LOAD_ARTIFACT", "LoadArtifact"),
                    kind_if_then("INIT_RUN", "InitRun"),
                    kind_if_then("BAR_BEGIN", "BarBegin"),
                    kind_if_then("INTENT_BATCH", "IntentBatch"),
                    kind_if_then("BROKER_EVENT_BATCH", "BrokerEventBatch"),
                    kind_if_then("RECALC_REQUEST", "RecalcRequest"),
                    kind_if_then("RECALC_RESULT", "RecalcResult"),
                    kind_if_then("BAR_COMMIT", "BarCommit"),
                    kind_if_then("CHECKPOINT", "Checkpoint"),
                    kind_if_then("RESTORE", "Restore"),
                    kind_if_then("FINALIZE", "Finalize"),
                    kind_if_then("ABORT", "Abort"),
                ]
            },
        ),
    )

    write(
        "openpine.run.v2.json",
        schema(
            "openpine.run.v2",
            required=[
                "run_id",
                "run_mode",
                "state",
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
            properties={
                "schema_version": {"const": "2.1.0"},
                "run_id": NONEMPTY_STRING,
                "run_mode": {
                    "enum": [
                        "COMPILE",
                        "BACKTEST",
                        "OPTIMIZE",
                        "PARITY",
                        "PAPER",
                        "LIVE",
                        "BACKFILL",
                    ]
                },
                "state": NONEMPTY_STRING,
                "stack_manifest_hash": SHA,
                "wheel_identities": {
                    "type": "array",
                    "minItems": 1,
                    "items": {"$ref": "#/$defs/WheelIdentity"},
                },
                "schema_hashes": {
                    "type": "object",
                    "minProperties": 1,
                    "additionalProperties": SHA,
                },
                "source_hash": SHA,
                "ast_hash": SHA,
                "generated_artifact_hash": SHA,
                "config_hash": SHA,
                "data_snapshot_hash": SHA,
                "semantic_profile": {"enum": ["legacy_4x", "strict_5x"]},
                "finality_policy": {"enum": ["CLOSED_BAR_ONLY", "ALLOW_OPEN"]},
                "numeric_policy": {"type": "string"},
                "fill_policy": {"type": "string"},
                "warmup_policy": {
                    "enum": ["CALC_ONLY", "TRADE_THROUGH_UNSCORED", "CALC_THEN_RESET_BROKER"]
                },
                "score_policy": NONEMPTY_STRING,
                "required_capabilities": {
                    "type": "array",
                    "items": NONEMPTY_STRING,
                    "uniqueItems": True,
                },
                "broker_adapter_ref": NONEMPTY_STRING,
                "broker_account_ref": NONEMPTY_STRING,
                "score_window": {"type": "object"},
                "seed": {"type": ["integer", "null"]},
                "input_artifacts": {"type": "array", "items": {"type": "object"}},
                "output_artifacts": {"type": "array", "items": {"type": "object"}},
                "diagnostics": {"type": "array", "items": {"type": "object"}},
                "completed_at_utc_ms": {"type": ["integer", "null"]},
            },
            defs={
                "WheelIdentity": strict_object(
                    ["name", "version", "content_hash"],
                    {
                        "name": NONEMPTY_STRING,
                        "version": NONEMPTY_STRING,
                        "content_hash": SHA,
                    },
                )
            },
            extra={
                "allOf": [
                    {
                        "if": {
                            "properties": {"run_mode": {"enum": ["PAPER", "LIVE"]}},
                            "required": ["run_mode"],
                        },
                        "then": {"required": ["broker_adapter_ref", "broker_account_ref"]},
                    }
                ]
            },
        ),
    )

    write(
        "openpine.trial.v2.json",
        schema(
            "openpine.trial.v2",
            required=["trial_key", "parameters", "lifecycle"],
            properties={
                "trial_key": {"type": "string", "minLength": 1},
                "parameters": {"type": "object"},
                "fold_window": {"type": ["object", "null"]},
                "runner_fingerprint": SHA,
                "constraints": {"type": "object"},
                "seed": {"type": ["integer", "null"]},
                "metrics": {"type": "object"},
                "artifacts": {"type": "array", "items": {"type": "object"}},
                "lifecycle": {"type": "string"},
                "retry_count": {"type": "integer", "minimum": 0},
            },
        ),
    )

    write(
        "openpine.job.v1.json",
        schema(
            "openpine.job.v1",
            required=["job_id", "kind", "state", "version"],
            properties={
                "job_id": {"type": "string", "minLength": 1},
                "kind": {"type": "string", "minLength": 1},
                "version": {"type": "integer", "minimum": 1},
                "state": {
                    "enum": [
                        "QUEUED",
                        "RUNNING",
                        "SUCCEEDED",
                        "FAILED",
                        "CANCELED",
                        "RETRY_WAIT",
                        "LOST",
                    ]
                },
                "progress": {"type": ["integer", "null"], "minimum": 0, "maximum": 100},
                "started_at_utc_ms": {"type": ["integer", "null"]},
                "updated_at_utc_ms": {"type": ["integer", "null"]},
                "finished_at_utc_ms": {"type": ["integer", "null"]},
                "actor": {"type": ["string", "null"]},
                "input_artifact_refs": {"type": "array", "items": {"type": "string"}},
                "result_artifact_refs": {"type": "array", "items": {"type": "string"}},
                "error_code": {"type": ["string", "null"]},
                "idempotency_key": {"type": ["string", "null"]},
                "lease_owner": {"type": ["string", "null"]},
                "lease_deadline_utc_ms": {"type": ["integer", "null"]},
                "retry_count": {"type": "integer", "minimum": 0},
                "max_retries": {"type": ["integer", "null"]},
                "parent_job_id": {"type": ["string", "null"]},
                "child_job_ids": {"type": "array", "items": {"type": "string"}},
                "event_cursor": {"type": ["string", "null"]},
                "run_id": {"type": ["string", "null"]},
            },
        ),
    )

    write(
        "openpine.audit.v1.json",
        schema(
            "openpine.audit.v1",
            required=["actor", "action", "target", "sequence"],
            properties={
                "actor": {"type": "string", "minLength": 1},
                "action": {"type": "string", "minLength": 1},
                "target": {"type": "string", "minLength": 1},
                "correlation_id": {"type": ["string", "null"]},
                "causation_id": {"type": ["string", "null"]},
                "before_hash": SHA,
                "after_hash": SHA,
                "security_decision": {"type": "string"},
                "sequence": {"type": "integer", "minimum": 0},
            },
        ),
    )


if __name__ == "__main__":
    main()
