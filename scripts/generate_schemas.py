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
NONZERO_SHA = {
    "type": "string",
    "pattern": r"^sha256:(?!0{64}$)[0-9a-f]{64}$",
}
GIT_SHA = {"type": "string", "pattern": r"^[0-9a-f]{40}$"}
NONZERO_GIT_SHA = {"type": "string", "pattern": r"^(?!0{40}$)[0-9a-f]{40}$"}
WHEEL_VERSION = {
    "type": "string",
    "pattern": r"^(?:0|[1-9][0-9]*)\.(?:0|[1-9][0-9]*)\.(?:0|[1-9][0-9]*)(?:rc[1-9][0-9]*)?$",
}
NONEMPTY_STRING = {"type": "string", "minLength": 1}
NONNEGATIVE_DECIMAL = {
    "type": "string",
    "pattern": r"^(?:0|[1-9][0-9]*)(?:\.[0-9]+)?$",
}
SUPPORT = {"enum": ["SUPPORTED", "CONDITIONAL", "VISUAL_ONLY", "UNSUPPORTED", "NOT_APPLICABLE"]}
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
POLICY_REGISTRY_VERSION = "openpine.policies.rc4.v1"
SCHEMA_REGISTRY_VERSION = "openpine.schemas.rc4.v1"
CAPABILITY_REGISTRY_VERSION = "openpine.capabilities.rc4.v1"
PRODUCTION_SCHEMA_IDS = (
    "openpine.execution_context.v1",
    "openpine.worker.protocol.v2",
    "openpine.checkpoint.v1",
    "openpine.checkpoint.proof.v1",
    "openpine.intent.v2",
)
CAPABILITIES = (
    "closed_bar",
    "deterministic_clock",
    "checkpoint_v1",
    "sealed_artifact_refs",
)
INTENT_KIND_FIELDS: dict[str, tuple[str, list[str], dict[str, object]]] = {
    "entry": (
        "EntryIntent",
        ["order_id", "direction", "qty"],
        {
            "order_id": NONEMPTY_STRING,
            "direction": {"enum": ["LONG", "SHORT"]},
            "qty": NONNEGATIVE_DECIMAL,
            "stop": DECIMAL_OR_NULL,
            "limit": DECIMAL_OR_NULL,
            "oca_name": {"type": ["string", "null"]},
            "oca_type": {"type": ["string", "null"]},
            "comment": {"type": ["string", "null"]},
            "alert_message": {"type": ["string", "null"]},
            "disable_alert": {"type": "boolean"},
        },
    ),
    "order": (
        "OrderIntent",
        ["order_id", "direction", "qty"],
        {
            "order_id": NONEMPTY_STRING,
            "direction": {"enum": ["LONG", "SHORT"]},
            "qty": NONNEGATIVE_DECIMAL,
            "stop": DECIMAL_OR_NULL,
            "limit": DECIMAL_OR_NULL,
            "oca_name": {"type": ["string", "null"]},
            "oca_type": {"type": ["string", "null"]},
            "comment": {"type": ["string", "null"]},
            "alert_message": {"type": ["string", "null"]},
            "disable_alert": {"type": "boolean"},
        },
    ),
    "exit": (
        "ExitIntent",
        ["order_id", "from_entry"],
        {
            "order_id": NONEMPTY_STRING,
            "from_entry": NONEMPTY_STRING,
            "qty": NONNEGATIVE_DECIMAL,
            "qty_percent": NONNEGATIVE_DECIMAL,
            "profit": DECIMAL_OR_NULL,
            "limit": DECIMAL_OR_NULL,
            "loss": DECIMAL_OR_NULL,
            "stop": DECIMAL_OR_NULL,
            "trail_price": DECIMAL_OR_NULL,
            "trail_points": DECIMAL_OR_NULL,
            "trail_offset": DECIMAL_OR_NULL,
            "oca_name": {"type": ["string", "null"]},
            "comment": {"type": ["string", "null"]},
            "alert_message": {"type": ["string", "null"]},
            "disable_alert": {"type": "boolean"},
        },
    ),
    "close": (
        "CloseIntent",
        ["from_entry"],
        {
            "from_entry": NONEMPTY_STRING,
            "qty": NONNEGATIVE_DECIMAL,
            "qty_percent": NONNEGATIVE_DECIMAL,
            "comment": {"type": ["string", "null"]},
            "alert_message": {"type": ["string", "null"]},
            "immediately": {"type": "boolean"},
            "disable_alert": {"type": "boolean"},
        },
    ),
    "close_all": (
        "CloseAllIntent",
        [],
        {
            "comment": {"type": ["string", "null"]},
            "alert_message": {"type": ["string", "null"]},
            "immediately": {"type": "boolean"},
            "disable_alert": {"type": "boolean"},
        },
    ),
    "cancel": (
        "CancelIntent",
        ["order_id"],
        {"order_id": NONEMPTY_STRING},
    ),
    "cancel_all": ("CancelAllIntent", [], {}),
    "risk": (
        "RiskIntent",
        ["risk_rule", "risk_value", "risk_unit", "risk_scope"],
        {
            "risk_rule": NONEMPTY_STRING,
            "risk_value": DECIMAL,
            "risk_unit": NONEMPTY_STRING,
            "risk_scope": NONEMPTY_STRING,
            "alert_message": {"type": ["string", "null"]},
        },
    ),
}
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


def rc4_schema(
    schema_id: str,
    schema_version: str,
    *,
    required: list[str],
    properties: dict,
    defs: dict | None = None,
    extra: dict | None = None,
) -> dict:
    """Build a strict RC.4 schema with immutable provenance identity."""
    rc4_properties = {
        "schema_version": {"const": schema_version},
        "producer_commit": GIT_SHA,
        "stack_id": NONZERO_SHA,
        "content_hash": NONZERO_SHA,
        **properties,
    }
    return schema(
        schema_id,
        required=required,
        properties=rc4_properties,
        defs=defs,
        extra=extra,
    )


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

    provider_revision_identity = {
        "oneOf": [
            strict_object(
                ["known", "revision"],
                {
                    "known": {"const": True},
                    "revision": NONEMPTY_STRING,
                },
            ),
            strict_object(
                ["known", "revision"],
                {
                    "known": {"const": False},
                    "revision": {"type": "null"},
                },
            ),
        ]
    }
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
        "provider_revision": provider_revision_identity,
        "observed_at_utc_ms": {"type": ["integer", "null"]},
        "ingested_at_utc_ms": {"type": ["integer", "null"]},
        "session_id": {"type": ["string", "null"]},
        "bar_content_hash": NONZERO_SHA,
        "superseded_bar_hash": {"anyOf": [NONZERO_SHA, {"type": "null"}]},
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
        "provider_revision",
        "snapshot_id",
        "bar_content_hash",
        "superseded_bar_hash",
    ]
    bar_revision_lineage = [
        {
            "if": {
                "properties": {"revision_state": {"const": "ORIGINAL"}},
                "required": ["revision_state"],
            },
            "then": {
                "properties": {
                    "revision": {"const": 0},
                    "superseded_bar_hash": {"type": "null"},
                }
            },
        },
        {
            "if": {
                "properties": {"revision_state": {"enum": ["CORRECTED", "REVOKED"]}},
                "required": ["revision_state"],
            },
            "then": {
                "properties": {
                    "revision": {"type": "integer", "minimum": 1},
                    "superseded_bar_hash": NONZERO_SHA,
                }
            },
        },
    ]

    write(
        "openpine.marketdata.bar.v2.json",
        rc4_schema(
            "openpine.marketdata.bar.v2",
            "2.1.0",
            required=bar_required,
            properties={"producer_commit": NONZERO_GIT_SHA, **bar_props},
            extra={"allOf": bar_revision_lineage},
        ),
    )

    write(
        "openpine.marketdata.v2.json",
        rc4_schema(
            "openpine.marketdata.v2",
            "2.1.0",
            required=["kind", "body"],
            properties={
                "producer_commit": NONZERO_GIT_SHA,
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
                    "allOf": bar_revision_lineage,
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
                        "coverage",
                        "gaps",
                        "conflicts",
                        "provider_revision",
                        "created_at_utc_ms",
                    ],
                    "properties": {
                        "snapshot_id": {"type": "string"},
                        "query": {"$ref": "#/$defs/DataQuery"},
                        "bar_count": {"type": "integer", "minimum": 0},
                        "series_hash": NONZERO_SHA,
                        "coverage": {
                            "type": "array",
                            "items": {"$ref": "#/$defs/Coverage"},
                        },
                        "gaps": {
                            "type": "array",
                            "items": {"$ref": "#/$defs/Gap"},
                        },
                        "conflicts": {
                            "type": "array",
                            "items": {"$ref": "#/$defs/Conflict"},
                        },
                        "provider_revision": provider_revision_identity,
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
        "openpine.execution_context.v1.json",
        rc4_schema(
            "openpine.execution_context.v1",
            "1.0.0",
            required=[
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
                "policy_registry_version",
                "schema_registry_version",
                "capability_registry_version",
            ],
            properties={
                "run_id": NONEMPTY_STRING,
                "strategy_id": NONEMPTY_STRING,
                "session_id": NONEMPTY_STRING,
                "stack_manifest_hash": NONZERO_SHA,
                "wheel_identities": {
                    "type": "array",
                    "minItems": len(STACK_COMPONENTS),
                    "maxItems": len(STACK_COMPONENTS),
                    "uniqueItems": True,
                    "items": {"$ref": "#/$defs/WheelIdentity"},
                    "allOf": [
                        {
                            "contains": {
                                "type": "object",
                                "properties": {"name": {"const": component}},
                                "required": ["name"],
                            },
                            "minContains": 1,
                            "maxContains": 1,
                        }
                        for component in STACK_COMPONENTS
                    ],
                },
                "schema_hashes": strict_object(
                    list(PRODUCTION_SCHEMA_IDS),
                    {schema_id: NONZERO_SHA for schema_id in PRODUCTION_SCHEMA_IDS},
                ),
                "generated_artifact_hash": NONZERO_SHA,
                "source_hash": NONZERO_SHA,
                "emitted_module_hash": NONZERO_SHA,
                "data_snapshot_hash": NONZERO_SHA,
                "series_id": NONEMPTY_STRING,
                "instrument_id": NONEMPTY_STRING,
                "exchange": NONEMPTY_STRING,
                "market": NONEMPTY_STRING,
                "symbol": NONEMPTY_STRING,
                "timeframe": NONEMPTY_STRING,
                "timezone": NONEMPTY_STRING,
                "currency": NONEMPTY_STRING,
                "mintick": NONNEGATIVE_DECIMAL,
                "pointvalue": NONNEGATIVE_DECIMAL,
                "session_policy": NONEMPTY_STRING,
                "semantic_profile": {"enum": ["legacy_4x", "strict_5x"]},
                "finality_policy": {"enum": ["CLOSED_BAR_ONLY", "ALLOW_OPEN"]},
                "warmup_policy": {
                    "enum": ["CALC_ONLY", "TRADE_THROUGH_UNSCORED", "CALC_THEN_RESET_BROKER"]
                },
                "score_policy": {"enum": ["ALL_BARS", "AFTER_WARMUP"]},
                "end_policy": {"enum": ["LIQUIDATE_ON_LAST_BAR", "PRESERVE_OPEN_POSITIONS"]},
                "capabilities": {
                    "type": "array",
                    "minItems": 2,
                    "uniqueItems": True,
                    "items": {"enum": list(CAPABILITIES)},
                    "allOf": [
                        {"contains": {"const": capability}, "minContains": 1}
                        for capability in ("closed_bar", "deterministic_clock")
                    ],
                },
                "producer_commits": {"$ref": "#/$defs/ProducerCommits"},
                "policy_registry_version": {"const": POLICY_REGISTRY_VERSION},
                "schema_registry_version": {"const": SCHEMA_REGISTRY_VERSION},
                "capability_registry_version": {"const": CAPABILITY_REGISTRY_VERSION},
            },
            defs={
                "WheelIdentity": strict_object(
                    ["name", "version", "content_hash"],
                    {
                        "name": NONEMPTY_STRING,
                        "version": WHEEL_VERSION,
                        "content_hash": NONZERO_SHA,
                    },
                ),
                "ProducerCommits": strict_object(
                    [
                        "openpine-contracts",
                        "pine2ast",
                        "ast2python",
                        "pinelib",
                        "marketdata-provider",
                        "backtest_engine",
                        "optimizer",
                        "openpine",
                    ],
                    {
                        "openpine-contracts": NONZERO_GIT_SHA,
                        "pine2ast": NONZERO_GIT_SHA,
                        "ast2python": NONZERO_GIT_SHA,
                        "pinelib": NONZERO_GIT_SHA,
                        "marketdata-provider": NONZERO_GIT_SHA,
                        "backtest_engine": NONZERO_GIT_SHA,
                        "optimizer": NONZERO_GIT_SHA,
                        "openpine": NONZERO_GIT_SHA,
                    },
                ),
            },
        ),
    )

    intent_common_required = [
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
    ]
    intent_common_properties = {
        **ENVELOPE_PROPS,
        "schema_id": {"const": "openpine.intent.v2"},
        "schema_version": {"const": "2.2.0"},
        "producer_commit": GIT_SHA,
        "stack_id": SHA,
        "event_id": NONEMPTY_STRING,
        "sequence": {"type": "integer", "minimum": 0},
        "command_id": NONEMPTY_STRING,
        "kind": {"enum": list(INTENT_KIND_FIELDS)},
        "run_id": NONEMPTY_STRING,
        "strategy_id": NONEMPTY_STRING,
        "series_id": NONEMPTY_STRING,
        "instrument_id": NONEMPTY_STRING,
        "timeframe": NONEMPTY_STRING,
        "bar_index": {"type": "integer", "minimum": 0},
        "bar_open_time_utc_ms": {"type": "integer", "minimum": 0},
        "phase": NONEMPTY_STRING,
        "recalc_iteration": {"type": "integer", "minimum": 0},
        "source_span": {"$ref": "#/$defs/SourceProvenance"},
        "semantic_profile": {"enum": ["legacy_4x", "strict_5x"]},
        "idempotency_key": NONEMPTY_STRING,
    }
    intent_kind_defs = {
        def_name: strict_object(
            list(dict.fromkeys(ENVELOPE_REQUIRED + intent_common_required + required_fields)),
            {
                **intent_common_properties,
                "kind": {"const": kind},
                **allowed_fields,
            },
        )
        for kind, (def_name, required_fields, allowed_fields) in INTENT_KIND_FIELDS.items()
    }
    write(
        "openpine.intent.v2.json",
        rc4_schema(
            "openpine.intent.v2",
            "2.2.0",
            required=intent_common_required,
            properties={
                key: value
                for key, value in intent_common_properties.items()
                if key not in ENVELOPE_PROPS
            }
            | {
                field: definition
                for _, _, fields in INTENT_KIND_FIELDS.values()
                for field, definition in fields.items()
            },
            defs={
                "SourceProvenance": {
                    "oneOf": [
                        {"$ref": "#/$defs/KnownSourceProvenance"},
                        {"$ref": "#/$defs/UnknownSourceProvenance"},
                    ]
                },
                "KnownSourceProvenance": strict_object(
                    [
                        "known",
                        "source_hash",
                        "start_offset",
                        "end_offset",
                        "start_line",
                        "start_col",
                        "end_line",
                        "end_col",
                    ],
                    {
                        "known": {"const": True},
                        "source_hash": NONZERO_SHA,
                        "start_offset": {"type": "integer", "minimum": 0},
                        "end_offset": {"type": "integer", "minimum": 0},
                        "start_line": {"type": "integer", "minimum": 1},
                        "start_col": {"type": "integer", "minimum": 0},
                        "end_line": {"type": "integer", "minimum": 1},
                        "end_col": {"type": "integer", "minimum": 0},
                    },
                ),
                "UnknownSourceProvenance": strict_object(
                    [
                        "known",
                        "source_hash",
                        "start_offset",
                        "end_offset",
                        "start_line",
                        "start_col",
                        "end_line",
                        "end_col",
                    ],
                    {
                        "known": {"const": False},
                        "source_hash": {"type": "null"},
                        "start_offset": {"type": "null"},
                        "end_offset": {"type": "null"},
                        "start_line": {"type": "null"},
                        "start_col": {"type": "null"},
                        "end_line": {"type": "null"},
                        "end_col": {"type": "null"},
                    },
                ),
                **intent_kind_defs,
            },
            extra={
                "oneOf": [
                    {"$ref": f"#/$defs/{def_name}"}
                    for def_name, _, _ in INTENT_KIND_FIELDS.values()
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
        "openpine.broker_projection.v1.json",
        rc4_schema(
            "openpine.broker_projection.v1",
            "1.0.0",
            required=[
                "run_id",
                "series_id",
                "instrument_id",
                "bar_index",
                "bar_open_time_utc_ms",
                "recalc_iteration",
                "position",
                "orders",
                "fills",
                "open_trades",
                "closed_trades",
                "realized_pnl",
                "unrealized_pnl",
                "gross_profit",
                "gross_loss",
                "commission",
                "winning_trades",
                "losing_trades",
                "even_trades",
                "cash",
                "equity",
                "currency",
            ],
            properties={
                "run_id": NONEMPTY_STRING,
                "series_id": NONEMPTY_STRING,
                "instrument_id": NONEMPTY_STRING,
                "bar_index": {"type": "integer", "minimum": 0},
                "bar_open_time_utc_ms": {"type": "integer", "minimum": 0},
                "recalc_iteration": {"type": "integer", "minimum": 0},
                "position": {"$ref": "#/$defs/Position"},
                "orders": {
                    "type": "array",
                    "items": {"$ref": "#/$defs/Order"},
                },
                "fills": {
                    "type": "array",
                    "items": {"$ref": "#/$defs/Fill"},
                },
                "open_trades": {
                    "type": "array",
                    "items": {"$ref": "#/$defs/OpenTrade"},
                },
                "closed_trades": {
                    "type": "array",
                    "items": {"$ref": "#/$defs/ClosedTrade"},
                },
                "realized_pnl": DECIMAL,
                "unrealized_pnl": DECIMAL,
                "gross_profit": DECIMAL,
                "gross_loss": DECIMAL,
                "commission": NONNEGATIVE_DECIMAL,
                "winning_trades": {"type": "integer", "minimum": 0},
                "losing_trades": {"type": "integer", "minimum": 0},
                "even_trades": {"type": "integer", "minimum": 0},
                "cash": DECIMAL,
                "equity": DECIMAL,
                "currency": NONEMPTY_STRING,
            },
            defs={
                "Position": strict_object(
                    ["direction", "qty", "avg_price", "entry_name"],
                    {
                        "direction": {"enum": ["FLAT", "LONG", "SHORT"]},
                        "qty": DECIMAL,
                        "avg_price": DECIMAL_OR_NULL,
                        "entry_name": {"type": ["string", "null"]},
                    },
                ),
                "Order": strict_object(
                    [
                        "order_id",
                        "entry_name",
                        "state",
                        "direction",
                        "order_type",
                        "qty",
                        "filled_qty",
                        "limit_price",
                        "stop_price",
                        "created_bar_index",
                        "updated_bar_index",
                    ],
                    {
                        "order_id": NONEMPTY_STRING,
                        "entry_name": {"type": ["string", "null"]},
                        "state": {
                            "enum": [
                                "PENDING",
                                "OPEN",
                                "PARTIALLY_FILLED",
                                "FILLED",
                                "CANCELED",
                                "REJECTED",
                                "EXPIRED",
                            ]
                        },
                        "direction": {"enum": ["LONG", "SHORT"]},
                        "order_type": {"enum": ["MARKET", "LIMIT", "STOP", "STOP_LIMIT"]},
                        "qty": NONNEGATIVE_DECIMAL,
                        "filled_qty": NONNEGATIVE_DECIMAL,
                        "limit_price": DECIMAL_OR_NULL,
                        "stop_price": DECIMAL_OR_NULL,
                        "created_bar_index": {"type": "integer", "minimum": 0},
                        "updated_bar_index": {"type": "integer", "minimum": 0},
                    },
                ),
                "Fill": strict_object(
                    [
                        "fill_id",
                        "order_id",
                        "trade_id",
                        "direction",
                        "qty",
                        "price",
                        "commission",
                        "bar_index",
                        "occurred_at_utc_ms",
                    ],
                    {
                        "fill_id": NONEMPTY_STRING,
                        "order_id": NONEMPTY_STRING,
                        "trade_id": {"type": ["string", "null"]},
                        "direction": {"enum": ["LONG", "SHORT"]},
                        "qty": NONNEGATIVE_DECIMAL,
                        "price": DECIMAL,
                        "commission": NONNEGATIVE_DECIMAL,
                        "bar_index": {"type": "integer", "minimum": 0},
                        "occurred_at_utc_ms": {"type": "integer", "minimum": 0},
                    },
                ),
                "OpenTrade": strict_object(
                    [
                        "trade_id",
                        "entry_name",
                        "direction",
                        "qty",
                        "entry_price",
                        "entry_bar_index",
                        "entry_time_utc_ms",
                        "unrealized_pnl",
                    ],
                    {
                        "trade_id": NONEMPTY_STRING,
                        "entry_name": NONEMPTY_STRING,
                        "direction": {"enum": ["LONG", "SHORT"]},
                        "qty": NONNEGATIVE_DECIMAL,
                        "entry_price": DECIMAL,
                        "entry_bar_index": {"type": "integer", "minimum": 0},
                        "entry_time_utc_ms": {"type": "integer", "minimum": 0},
                        "unrealized_pnl": DECIMAL,
                    },
                ),
                "ClosedTrade": strict_object(
                    [
                        "trade_id",
                        "entry_name",
                        "direction",
                        "qty",
                        "entry_price",
                        "entry_bar_index",
                        "entry_time_utc_ms",
                        "exit_price",
                        "exit_bar_index",
                        "exit_time_utc_ms",
                        "realized_pnl",
                        "commission",
                    ],
                    {
                        "trade_id": NONEMPTY_STRING,
                        "entry_name": NONEMPTY_STRING,
                        "direction": {"enum": ["LONG", "SHORT"]},
                        "qty": NONNEGATIVE_DECIMAL,
                        "entry_price": DECIMAL,
                        "entry_bar_index": {"type": "integer", "minimum": 0},
                        "entry_time_utc_ms": {"type": "integer", "minimum": 0},
                        "exit_price": DECIMAL,
                        "exit_bar_index": {"type": "integer", "minimum": 0},
                        "exit_time_utc_ms": {"type": "integer", "minimum": 0},
                        "realized_pnl": DECIMAL,
                        "commission": NONNEGATIVE_DECIMAL,
                    },
                ),
            },
        ),
    )

    checkpoint_payload_ref = {
        "type": "object",
        "additionalProperties": False,
        "required": ["codec", "compression", "size_bytes", "segment_schema_hashes"],
        "properties": {
            "codec": {"enum": ["json", "msgpack", "openpine.checkpoint.v1"]},
            "compression": {"enum": ["none", "gzip", "zstd"]},
            "size_bytes": {"type": "integer", "minimum": 1},
            "segment_schema_hashes": {
                "type": "object",
                "minProperties": 1,
                "additionalProperties": NONZERO_SHA,
                "propertyNames": {"pattern": r"^[a-z][a-z0-9]*(?:[._-][a-z0-9]+)*\.v[1-9][0-9]*$"},
            },
            "uri": {"type": "string", "pattern": r"^(?:https?|s3|file)://.+$"},
            "inline_base64": {
                "type": "string",
                "minLength": 4,
                "pattern": r"^(?:[A-Za-z0-9+/]{4})*(?:[A-Za-z0-9+/]{2}==|[A-Za-z0-9+/]{3}=)?$",
            },
        },
        "oneOf": [{"required": ["uri"]}, {"required": ["inline_base64"]}],
    }

    write(
        "openpine.checkpoint.proof.v1.json",
        rc4_schema(
            "openpine.checkpoint.proof.v1",
            "1.0.0",
            required=[
                "checkpoint_id",
                "checkpoint_hash",
                "committed_sequence",
                "committed_message_id",
                "state_hash",
                "broker_projection_hash",
                "payload_ref",
            ],
            properties={
                "producer": {"const": "openpine"},
                "producer_commit": NONZERO_GIT_SHA,
                "stack_id": NONZERO_SHA,
                "content_hash": NONZERO_SHA,
                "checkpoint_id": NONEMPTY_STRING,
                "checkpoint_hash": NONZERO_SHA,
                "committed_sequence": {"type": "integer", "minimum": 0},
                "committed_message_id": NONEMPTY_STRING,
                "state_hash": NONZERO_SHA,
                "broker_projection_hash": NONZERO_SHA,
                "payload_ref": {"$ref": "#/$defs/CheckpointPayloadRef"},
            },
            defs={"CheckpointPayloadRef": checkpoint_payload_ref},
        ),
    )

    write(
        "openpine.checkpoint.v1.json",
        rc4_schema(
            "openpine.checkpoint.v1",
            "1.0.0",
            required=[
                "checkpoint_id",
                "run_id",
                "session_id",
                "bar_index",
                "bar_open_time_utc_ms",
                "recalc_iteration",
                "committed_sequence",
                "bar_commit_hash",
                "generated_artifact_hash",
                "data_snapshot_hash",
                "stack_manifest_hash",
                "engine_checkpoint_hash",
                "worker_checkpoint_hash",
                "combined_hash",
                "checkpoint_hash",
                "payload_ref",
            ],
            properties={
                "checkpoint_id": NONEMPTY_STRING,
                "run_id": NONEMPTY_STRING,
                "session_id": NONEMPTY_STRING,
                "bar_index": {"type": "integer", "minimum": 0},
                "bar_open_time_utc_ms": {"type": "integer", "minimum": 0},
                "recalc_iteration": {"type": "integer", "minimum": 0},
                "committed_sequence": {"type": "integer", "minimum": 0},
                "bar_commit_hash": NONZERO_SHA,
                "generated_artifact_hash": NONZERO_SHA,
                "data_snapshot_hash": NONZERO_SHA,
                "stack_manifest_hash": NONZERO_SHA,
                "engine_checkpoint_hash": NONZERO_SHA,
                "worker_checkpoint_hash": NONZERO_SHA,
                "combined_hash": NONZERO_SHA,
                "checkpoint_hash": NONZERO_SHA,
                "payload_ref": {"$ref": "#/$defs/CheckpointPayloadRef"},
            },
            defs={"CheckpointPayloadRef": checkpoint_payload_ref},
        ),
    )

    write(
        "openpine.trial.identity.v1.json",
        rc4_schema(
            "openpine.trial.identity.v1",
            "1.0.0",
            required=[
                "optimizer_id",
                "strategy_id",
                "generated_artifact_hash",
                "source_hash",
                "emitted_module_hash",
                "data_snapshot_hash",
                "stack_manifest_hash",
                "runner_fingerprint",
                "parameters",
                "policies",
                "schema_set",
                "seed",
                "fold",
                "walk_forward",
                "objective",
                "constraints",
            ],
            properties={
                "optimizer_id": NONEMPTY_STRING,
                "strategy_id": NONEMPTY_STRING,
                "generated_artifact_hash": NONZERO_SHA,
                "source_hash": NONZERO_SHA,
                "emitted_module_hash": NONZERO_SHA,
                "data_snapshot_hash": NONZERO_SHA,
                "stack_manifest_hash": NONZERO_SHA,
                "runner_fingerprint": NONZERO_SHA,
                "parameters": {
                    "type": "object",
                    "additionalProperties": {"$ref": "#/$defs/JsonNoFloat"},
                },
                "policies": {"$ref": "#/$defs/Policies"},
                "schema_set": {
                    "type": "array",
                    "minItems": 1,
                    "uniqueItems": True,
                    "items": {"$ref": "#/$defs/SchemaIdentity"},
                },
                "seed": {"type": ["integer", "null"]},
                "fold": {
                    "oneOf": [
                        {"type": "null"},
                        {"$ref": "#/$defs/FoldIdentity"},
                    ]
                },
                "walk_forward": {
                    "oneOf": [
                        {"type": "null"},
                        {"$ref": "#/$defs/WalkForwardIdentity"},
                    ]
                },
                "objective": {"$ref": "#/$defs/ObjectiveIdentity"},
                "constraints": {
                    "type": "array",
                    "items": {"$ref": "#/$defs/ConstraintIdentity"},
                },
            },
            defs={
                "JsonNoFloat": JSON_NO_FLOAT,
                "Policies": strict_object(
                    [
                        "semantic_profile",
                        "finality_policy",
                        "warmup_policy",
                        "score_policy",
                        "end_policy",
                        "numeric_policy",
                        "fill_policy",
                    ],
                    {
                        "semantic_profile": {"enum": ["legacy_4x", "strict_5x"]},
                        "finality_policy": {"enum": ["CLOSED_BAR_ONLY", "ALLOW_OPEN"]},
                        "warmup_policy": {
                            "enum": [
                                "CALC_ONLY",
                                "TRADE_THROUGH_UNSCORED",
                                "CALC_THEN_RESET_BROKER",
                            ]
                        },
                        "score_policy": {"enum": ["ALL_BARS", "AFTER_WARMUP"]},
                        "end_policy": {
                            "enum": ["LIQUIDATE_ON_LAST_BAR", "PRESERVE_OPEN_POSITIONS"]
                        },
                        "numeric_policy": NONEMPTY_STRING,
                        "fill_policy": NONEMPTY_STRING,
                    },
                ),
                "SchemaIdentity": strict_object(
                    ["schema_id", "schema_hash"],
                    {"schema_id": NONEMPTY_STRING, "schema_hash": NONZERO_SHA},
                ),
                "FoldIdentity": strict_object(
                    [
                        "fold_id",
                        "train_start_utc_ms",
                        "train_end_utc_ms",
                        "test_start_utc_ms",
                        "test_end_utc_ms",
                    ],
                    {
                        "fold_id": NONEMPTY_STRING,
                        "train_start_utc_ms": {"type": "integer", "minimum": 0},
                        "train_end_utc_ms": {"type": "integer", "minimum": 0},
                        "test_start_utc_ms": {"type": "integer", "minimum": 0},
                        "test_end_utc_ms": {"type": "integer", "minimum": 0},
                    },
                ),
                "WalkForwardIdentity": strict_object(
                    ["enabled", "window_size", "step_size", "anchored"],
                    {
                        "enabled": {"type": "boolean"},
                        "window_size": {"type": "integer", "minimum": 1},
                        "step_size": {"type": "integer", "minimum": 1},
                        "anchored": {"type": "boolean"},
                    },
                ),
                "ObjectiveIdentity": strict_object(
                    ["metric", "direction", "aggregation"],
                    {
                        "metric": NONEMPTY_STRING,
                        "direction": {"enum": ["MINIMIZE", "MAXIMIZE"]},
                        "aggregation": NONEMPTY_STRING,
                    },
                ),
                "ConstraintIdentity": strict_object(
                    ["name", "operator", "value"],
                    {
                        "name": NONEMPTY_STRING,
                        "operator": NONEMPTY_STRING,
                        "value": DECIMAL,
                    },
                ),
            },
        ),
    )

    write(
        "openpine.worker.protocol.v2.json",
        rc4_schema(
            "openpine.worker.protocol.v2",
            "2.3.0",
            required=[
                "message_id",
                "sender_role",
                "session_id",
                "run_id",
                "sequence",
                "correlation_id",
                "causation_id",
                "kind",
                "body",
            ],
            properties={
                "message_id": NONEMPTY_STRING,
                "sender_role": {"enum": ["parent", "worker", "engine"]},
                "session_id": NONEMPTY_STRING,
                "run_id": NONEMPTY_STRING,
                "sequence": {"type": "integer", "minimum": 0},
                "correlation_id": NONEMPTY_STRING,
                "causation_id": {"type": ["string", "null"]},
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
                        "protocol_version": {"const": "2.3.0"},
                        "capabilities": {
                            "type": "array",
                            "uniqueItems": True,
                            "items": NONEMPTY_STRING,
                        },
                    },
                ),
                "LoadArtifact": strict_object(
                    ["artifact_hash", "module_hash", "entrypoint_module", "entrypoint_class"],
                    {
                        "artifact_hash": NONZERO_SHA,
                        "module_hash": NONZERO_SHA,
                        "entrypoint_module": NONEMPTY_STRING,
                        "entrypoint_class": NONEMPTY_STRING,
                    },
                ),
                "InitRun": strict_object(
                    [
                        "run_id",
                        "run_hash",
                        "execution_context_hash",
                        "execution_context",
                        "semantic_profile",
                        "capabilities",
                    ],
                    {
                        "run_id": NONEMPTY_STRING,
                        "run_hash": NONZERO_SHA,
                        "execution_context_hash": NONZERO_SHA,
                        "execution_context": {"$ref": "openpine.execution_context.v1"},
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
                        "bar",
                        "broker_projection",
                    ],
                    {
                        "run_id": NONEMPTY_STRING,
                        "bar_index": {"type": "integer", "minimum": 0},
                        "bar_open_time_utc_ms": {"type": "integer", "minimum": 0},
                        "recalc_iteration": {"type": "integer", "minimum": 0},
                        "bar_hash": NONZERO_SHA,
                        "bar": {"$ref": "openpine.marketdata.bar.v2"},
                        "broker_projection": {"$ref": "openpine.broker_projection.v1"},
                    },
                ),
                "IntentBatch": strict_object(
                    [
                        "run_id",
                        "bar_index",
                        "recalc_iteration",
                        "intent_batch_hash",
                        "intents",
                    ],
                    {
                        "run_id": NONEMPTY_STRING,
                        "bar_index": {"type": "integer", "minimum": 0},
                        "recalc_iteration": {"type": "integer", "minimum": 0},
                        "intent_batch_hash": NONZERO_SHA,
                        "intents": {
                            "type": "array",
                            "items": {"$ref": "openpine.intent.v2"},
                        },
                    },
                ),
                "BrokerEventBatch": strict_object(
                    [
                        "run_id",
                        "bar_index",
                        "recalc_iteration",
                        "broker_event_batch_hash",
                        "broker_events",
                    ],
                    {
                        "run_id": NONEMPTY_STRING,
                        "bar_index": {"type": "integer", "minimum": 0},
                        "recalc_iteration": {"type": "integer", "minimum": 0},
                        "broker_event_batch_hash": NONZERO_SHA,
                        "broker_events": {
                            "type": "array",
                            "items": {"$ref": "openpine.broker.v2"},
                        },
                    },
                ),
                "RecalcRequest": strict_object(
                    [
                        "run_id",
                        "bar_index",
                        "recalc_iteration",
                        "cause_sequence",
                        "broker_projection_hash",
                        "broker_projection",
                    ],
                    {
                        "run_id": NONEMPTY_STRING,
                        "bar_index": {"type": "integer", "minimum": 0},
                        "recalc_iteration": {"type": "integer", "minimum": 1},
                        "cause_sequence": {"type": "integer", "minimum": 0},
                        "broker_projection_hash": NONZERO_SHA,
                        "broker_projection": {"$ref": "openpine.broker_projection.v1"},
                    },
                ),
                "RecalcResult": strict_object(
                    [
                        "run_id",
                        "bar_index",
                        "recalc_iteration",
                        "intent_batch_message_id",
                        "intent_batch_hash",
                    ],
                    {
                        "run_id": NONEMPTY_STRING,
                        "bar_index": {"type": "integer", "minimum": 0},
                        "recalc_iteration": {"type": "integer", "minimum": 1},
                        "intent_batch_message_id": NONEMPTY_STRING,
                        "intent_batch_hash": NONZERO_SHA,
                    },
                ),
                "BarCommit": strict_object(
                    [
                        "run_id",
                        "bar_index",
                        "recalc_iteration",
                        "state_hash",
                        "broker_projection_hash",
                        "state_ref",
                        "broker_projection_ref",
                    ],
                    {
                        "run_id": NONEMPTY_STRING,
                        "bar_index": {"type": "integer", "minimum": 0},
                        "recalc_iteration": {"type": "integer", "minimum": 0},
                        "state_hash": NONZERO_SHA,
                        "broker_projection_hash": NONZERO_SHA,
                        "state_ref": {"$ref": "#/$defs/SealedArtifactRef"},
                        "broker_projection_ref": {"$ref": "#/$defs/SealedArtifactRef"},
                    },
                ),
                "Checkpoint": strict_object(
                    [
                        "run_id",
                        "checkpoint_id",
                        "checkpoint_hash",
                        "committed_sequence",
                        "checkpoint_ref",
                    ],
                    {
                        "run_id": NONEMPTY_STRING,
                        "checkpoint_id": NONEMPTY_STRING,
                        "checkpoint_hash": NONZERO_SHA,
                        "committed_sequence": {"type": "integer", "minimum": 0},
                        "checkpoint_ref": {"$ref": "openpine.checkpoint.proof.v1"},
                    },
                ),
                "Restore": strict_object(
                    ["run_id", "checkpoint_id", "checkpoint_hash", "committed_sequence"],
                    {
                        "run_id": NONEMPTY_STRING,
                        "checkpoint_id": NONEMPTY_STRING,
                        "checkpoint_hash": NONZERO_SHA,
                        "committed_sequence": {"type": "integer", "minimum": 0},
                        "external_checkpoint_proof": {"$ref": "openpine.checkpoint.proof.v1"},
                    },
                ),
                "Finalize": strict_object(
                    [
                        "run_id",
                        "final_sequence",
                        "final_state_hash",
                        "broker_projection_hash",
                        "last_commit_message_id",
                        "last_committed_sequence",
                    ],
                    {
                        "run_id": NONEMPTY_STRING,
                        "final_sequence": {"type": "integer", "minimum": 0},
                        "final_state_hash": NONZERO_SHA,
                        "broker_projection_hash": NONZERO_SHA,
                        "last_commit_message_id": NONEMPTY_STRING,
                        "last_committed_sequence": {"type": "integer", "minimum": 0},
                    },
                ),
                "SealedArtifactRef": strict_object(
                    ["artifact_hash", "schema_id", "codec", "size_bytes", "uri"],
                    {
                        "artifact_hash": NONZERO_SHA,
                        "schema_id": NONEMPTY_STRING,
                        "codec": {"enum": ["json", "msgpack", "binary"]},
                        "size_bytes": {"type": "integer", "minimum": 1},
                        "uri": {"type": "string", "pattern": r"^(?:https?|s3|file)://.+$"},
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
        rc4_schema(
            "openpine.trial.v2",
            "2.1.0",
            required=["trial_key", "trial_identity_hash", "lifecycle", "retry_count"],
            properties={
                "trial_key": {"type": "string", "minLength": 1},
                "trial_identity_hash": NONZERO_SHA,
                "metrics": {"type": "object"},
                "artifacts": {"type": "array", "items": {"type": "object"}},
                "lifecycle": {
                    "enum": [
                        "QUEUED",
                        "RUNNING",
                        "SUCCEEDED",
                        "FAILED",
                        "CANCELED",
                        "RETRY_WAIT",
                    ]
                },
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
