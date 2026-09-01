import copy
from collections.abc import Callable
from typing import Any

import pytest

import openpine_contracts as contracts

SCHEMA_ID = "openpine.generated_artifact.v3"


def _identity(label: str) -> str:
    return contracts.content_hash({"identity": label}, schema_id=SCHEMA_ID)


def _producer_shaped_payload() -> dict[str, Any]:
    catalog_hash = _identity("catalog")
    payload: dict[str, Any] = {
        "schema_id": SCHEMA_ID,
        "schema_version": "3.0.0",
        "producer": {
            "name": "ast2python",
            "version": "5.0.0rc6",
            "commit": None,
            "source_state": "UNCOMMITTED_LOCAL_BUILD",
        },
        "bundle_hash": _identity("consumer-bundle"),
        "source_hash": _identity("pine-source"),
        "version_context": {
            "pine_version": 6,
            "origin": "compiler_annotation",
            "annotation_span": {
                "start_offset": 0,
                "end_offset": 20,
                "start_line": 1,
                "start_col": 1,
                "end_line": 1,
                "end_col": 21,
            },
            "spec_snapshot_ref": "pine-language-reference-v6",
            "catalog_hash": catalog_hash,
            "context_hash": _identity("pine-version-context"),
        },
        "catalog_hash": catalog_hash,
        "lowering_plan_hash": _identity("lowering-plan"),
        "target_manifest_hash": _identity("target-manifest"),
        "emitted_module_hash": _identity("emitted-module"),
        "source_map_hash": _identity("source-map"),
        "entrypoint": {"module": "generated_strategy", "class": "GeneratedScript"},
        "required_operations": ["binary:add", "series:close"],
        "required_capabilities": ["series.numeric", "strategy.orders"],
        "import_manifest": ["pinelib.runtime", "typing"],
        "projection_proof": {
            "disposition_counts": {
                "EMITTED": 2,
                "COMPILE_TIME_ONLY": 1,
                "FOLDED": 0,
                "EXPANDED": 0,
                "DELEGATED": 0,
                "REJECTED": 0,
            },
            "source_node_count": 3,
            "ir_node_count": 2,
            "source_map_entry_count": 3,
            "mapped_ir_count": 2,
            "mapped_ir_coverage": True,
        },
        "release_acceptance": {
            "pine2ast_rc6": "EXACT_CORRECTED_BUNDLE_ACCEPTED",
            "pinelib_rc6": "EXACT_PINELIB_TARGET_MANIFEST_V2",
            "tradingview_oracle": "NOT_CLAIMED",
        },
    }
    sealed = contracts.seal_content_hash(payload, schema_id=SCHEMA_ID)
    assert contracts.verify_content_hash(sealed, schema_id=SCHEMA_ID)
    return sealed


def _reseal(payload: dict[str, Any]) -> dict[str, Any]:
    return contracts.seal_content_hash(payload, schema_id=SCHEMA_ID)


def test_generated_artifact_v3_is_registered() -> None:
    schema = contracts.get_schema(SCHEMA_ID)

    assert schema["$schema"] == "https://json-schema.org/draft/2020-12/schema"
    assert schema["$id"] == SCHEMA_ID
    assert SCHEMA_ID in contracts.list_schema_ids(include_aliases=False)
    assert "openpine.generated_artifact.v2" in contracts.list_schema_ids(include_aliases=False)


def test_generated_artifact_v3_accepts_current_ast2python_payload_shape() -> None:
    payload = _producer_shaped_payload()

    contracts.validate_payload(SCHEMA_ID, payload)


@pytest.mark.parametrize(
    "mutate",
    [
        pytest.param(lambda payload: payload.pop("source_map_hash"), id="missing-required-field"),
        pytest.param(
            lambda payload: payload.__setitem__("source_map_hash", "sha256:not-a-digest"),
            id="hash-format-drift",
        ),
        pytest.param(
            lambda payload: payload.__setitem__("schema_id", "openpine.generated_artifact.v2"),
            id="schema-id-drift",
        ),
        pytest.param(
            lambda payload: payload.__setitem__("schema_version", "3.0.1"),
            id="schema-version-drift",
        ),
        pytest.param(
            lambda payload: payload["version_context"].__setitem__("pine_version", "6"),
            id="nested-type-drift",
        ),
        pytest.param(
            lambda payload: payload["producer"].__setitem__("unexpected", True),
            id="extra-producer-field",
        ),
    ],
)
def test_generated_artifact_v3_rejects_wire_drift(
    mutate: Callable[[dict[str, Any]], object],
) -> None:
    payload = copy.deepcopy(_producer_shaped_payload())
    mutate(payload)

    with pytest.raises(contracts.SchemaValidationError):
        contracts.validate_payload(SCHEMA_ID, _reseal(payload))


def test_generated_artifact_v3_preserves_global_float_forbidden_policy() -> None:
    payload = copy.deepcopy(_producer_shaped_payload())
    payload["projection_proof"]["mapped_ir_count"] = 2.0

    with pytest.raises(contracts.SchemaValidationError) as raised:
        contracts.validate_payload(SCHEMA_ID, payload)

    assert raised.value.details["semantic_reason"] == "FLOAT_FORBIDDEN"
