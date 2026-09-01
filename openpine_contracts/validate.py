"""Payload validation against packaged JSON Schema resources."""

from __future__ import annotations

from functools import lru_cache
from typing import Any, Mapping, cast

from .errors import SchemaValidationError, SchemaValidatorUnavailableError
from .registry import get_schema, list_schema_ids

Draft202012Validator: Any = None
SchemaRegistry: Any = None
SchemaResource: Any = None
Draft202012Specification: Any = None
try:
    from jsonschema import Draft202012Validator as _Draft202012Validator
    from referencing import Registry as _SchemaRegistry
    from referencing import Resource as _SchemaResource
    from referencing.jsonschema import DRAFT202012 as _Draft202012Specification
except ImportError:  # pragma: no cover
    pass
else:
    Draft202012Validator = _Draft202012Validator
    SchemaRegistry = _SchemaRegistry
    SchemaResource = _SchemaResource
    Draft202012Specification = _Draft202012Specification


@lru_cache(maxsize=1)
def _packaged_registry() -> Any:
    if SchemaRegistry is None or SchemaResource is None or Draft202012Specification is None:
        raise SchemaValidatorUnavailableError(
            "Draft 2020-12 JSON Schema reference resolution is unavailable",
            details={"dependency": "jsonschema>=4.20"},
        )
    registry = SchemaRegistry()
    for packaged_schema_id in list_schema_ids(include_aliases=True):
        resource = SchemaResource.from_contents(
            dict(get_schema(packaged_schema_id)),
            default_specification=Draft202012Specification,
        )
        registry = registry.with_resource(packaged_schema_id, resource)
    return registry


def _find_float(value: object, path: tuple[object, ...] = ()) -> tuple[object, ...] | None:
    if type(value) is float:
        return path
    if isinstance(value, Mapping):
        for key, item in value.items():
            found = _find_float(item, (*path, key))
            if found is not None:
                return found
    elif isinstance(value, (list, tuple)):
        for index, item in enumerate(value):
            found = _find_float(item, (*path, index))
            if found is not None:
                return found
    return None


def _semantic_error(schema_id: str, reason: str, message: str, path: list[object]) -> None:
    raise SchemaValidationError(
        message,
        details={
            "schema_id": schema_id,
            "path": path,
            "error_count": 1,
            "semantic_reason": reason,
        },
    )


def _validate_intent_semantics(payload: Mapping[str, Any]) -> None:
    source_span = payload.get("source_span")
    if not isinstance(source_span, Mapping) or source_span.get("known") is not True:
        return
    start_offset = source_span.get("start_offset")
    end_offset = source_span.get("end_offset")
    if isinstance(start_offset, int) and isinstance(end_offset, int) and start_offset > end_offset:
        _semantic_error(
            "openpine.intent.v2",
            "SOURCE_OFFSET_ORDER",
            "source span start_offset must not exceed end_offset",
            ["source_span"],
        )
    start_line = source_span.get("start_line")
    start_col = source_span.get("start_col")
    end_line = source_span.get("end_line")
    end_col = source_span.get("end_col")
    if not all(isinstance(value, int) for value in (start_line, start_col, end_line, end_col)):
        return
    start_position = (cast(int, start_line), cast(int, start_col))
    end_position = (cast(int, end_line), cast(int, end_col))
    if start_position > end_position:
        _semantic_error(
            "openpine.intent.v2",
            "SOURCE_POSITION_ORDER",
            "source span start position must not exceed end position",
            ["source_span"],
        )


def _validate_trial_identity_semantics(payload: Mapping[str, Any]) -> None:
    schema_set = payload.get("schema_set")
    if isinstance(schema_set, list):
        schema_ids = [item.get("schema_id") for item in schema_set if isinstance(item, Mapping)]
        if len(schema_ids) != len(set(schema_ids)):
            _semantic_error(
                "openpine.trial.identity.v1",
                "DUPLICATE_SCHEMA_ID",
                "trial identity schema_set contains duplicate schema_id values",
                ["schema_set"],
            )
    fold = payload.get("fold")
    if isinstance(fold, Mapping):
        values = tuple(
            fold.get(field)
            for field in (
                "train_start_utc_ms",
                "train_end_utc_ms",
                "test_start_utc_ms",
                "test_end_utc_ms",
            )
        )
        if not all(isinstance(value, int) for value in values):
            return
        ordered_values = tuple(cast(int, value) for value in values)
        if not (ordered_values[0] <= ordered_values[1] < ordered_values[2] <= ordered_values[3]):
            _semantic_error(
                "openpine.trial.identity.v1",
                "FOLD_WINDOW_ORDER",
                "trial fold windows must be ordered and non-overlapping",
                ["fold"],
            )


def _validate_generated_artifact_v3_semantics(payload: Mapping[str, Any]) -> None:
    version_context = payload.get("version_context")
    if isinstance(version_context, Mapping):
        if payload.get("catalog_hash") != version_context.get("catalog_hash"):
            _semantic_error(
                "openpine.generated_artifact.v3",
                "CATALOG_HASH_MISMATCH",
                "generated artifact catalog_hash must match version_context.catalog_hash",
                ["catalog_hash"],
            )
    proof = payload.get("projection_proof")
    if not isinstance(proof, Mapping):
        return
    counts = proof.get("disposition_counts")
    if not isinstance(counts, Mapping):
        return
    rejected = counts.get("REJECTED")
    if isinstance(rejected, int) and rejected > 0:
        _semantic_error(
            "openpine.generated_artifact.v3",
            "PROJECTION_REJECTED",
            "canonical generated artifact projection must not contain REJECTED nodes",
            ["projection_proof", "disposition_counts", "REJECTED"],
        )
    if proof.get("mapped_ir_coverage") is not True:
        _semantic_error(
            "openpine.generated_artifact.v3",
            "PROJECTION_COVERAGE",
            "canonical generated artifact must prove mapped_ir_coverage",
            ["projection_proof", "mapped_ir_coverage"],
        )
    mapped_ir_count = proof.get("mapped_ir_count")
    source_map_entry_count = proof.get("source_map_entry_count")
    if proof.get("mapped_ir_count") != proof.get("ir_node_count"):
        _semantic_error(
            "openpine.generated_artifact.v3",
            "PROJECTION_IR_COUNT",
            "mapped_ir_count must equal ir_node_count",
            ["projection_proof", "mapped_ir_count"],
        )
    if (
        isinstance(source_map_entry_count, int)
        and isinstance(mapped_ir_count, int)
        and source_map_entry_count < mapped_ir_count
    ):
        _semantic_error(
            "openpine.generated_artifact.v3",
            "PROJECTION_SOURCE_MAP",
            "source_map_entry_count must cover mapped_ir_count",
            ["projection_proof", "source_map_entry_count"],
        )


def _validate_semantics(schema_id: str, payload: Mapping[str, Any]) -> None:
    if schema_id == "openpine.intent.v2":
        _validate_intent_semantics(payload)
    elif schema_id == "openpine.trial.identity.v1":
        _validate_trial_identity_semantics(payload)
    elif schema_id == "openpine.generated_artifact.v3":
        _validate_generated_artifact_v3_semantics(payload)


def validate_payload(schema_id: str, payload: Mapping[str, Any] | dict[str, Any]) -> None:
    schema = get_schema(schema_id)
    if Draft202012Validator is None:
        raise SchemaValidatorUnavailableError(
            "Draft 2020-12 JSON Schema validation is unavailable",
            details={"schema_id": schema_id, "dependency": "jsonschema>=4.20"},
        )
    float_path = _find_float(payload)
    if float_path is not None:
        _semantic_error(
            schema_id,
            "FLOAT_FORBIDDEN",
            "canonical contract payloads must not contain binary floats",
            list(float_path),
        )
    validator = Draft202012Validator(schema, registry=_packaged_registry())
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
    _validate_semantics(schema_id, payload)
