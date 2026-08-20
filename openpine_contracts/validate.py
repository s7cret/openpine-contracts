"""Payload validation against packaged JSON Schema resources."""

from __future__ import annotations

from typing import Any, Mapping

from .errors import SchemaValidationError
from .registry import get_schema

Draft202012Validator: Any = None
try:
    from jsonschema import Draft202012Validator as _Draft202012Validator
except ImportError:  # pragma: no cover
    pass
else:
    Draft202012Validator = _Draft202012Validator


def validate_payload(schema_id: str, payload: Mapping[str, Any] | dict[str, Any]) -> None:
    schema = get_schema(schema_id)
    if Draft202012Validator is None:
        _validate_required_subset(schema_id, schema, payload)
        return
    validator = Draft202012Validator(schema)
    errors = sorted(validator.iter_errors(payload), key=lambda err: list(err.path))
    if errors:
        first = errors[0]
        raise SchemaValidationError(
            first.message,
            details={
                "schema_id": schema_id,
                "path": list(first.path),
                "error_count": len(errors),
            },
        )


def _validate_required_subset(
    schema_id: str,
    schema: Mapping[str, object],
    payload: Mapping[str, Any],
) -> None:
    if not isinstance(payload, dict):
        raise SchemaValidationError("payload must be an object", details={"schema_id": schema_id})
    required = schema.get("required", [])
    if isinstance(required, list):
        missing = [key for key in required if key not in payload]
        if missing:
            raise SchemaValidationError(
                "missing required fields",
                details={"schema_id": schema_id, "missing": missing},
            )
    const_id = None
    properties = schema.get("properties")
    if isinstance(properties, dict):
        schema_id_prop = properties.get("schema_id")
        if isinstance(schema_id_prop, dict):
            const_id = schema_id_prop.get("const")
    if const_id is not None and payload.get("schema_id") != const_id:
        raise SchemaValidationError(
            "schema_id const mismatch",
            details={"schema_id": schema_id, "got": payload.get("schema_id")},
        )
