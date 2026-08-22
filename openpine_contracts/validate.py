"""Payload validation against packaged JSON Schema resources."""

from __future__ import annotations

from typing import Any, Mapping

from .errors import SchemaValidationError, SchemaValidatorUnavailableError
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
        raise SchemaValidatorUnavailableError(
            "Draft 2020-12 JSON Schema validation is unavailable",
            details={"schema_id": schema_id, "dependency": "jsonschema>=4.20"},
        )
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
