import copy
import tomllib
from pathlib import Path
from typing import Any

import pytest

import openpine_contracts as contracts
import openpine_contracts.validate as validation
from openpine_contracts.hashing import canonical_dumps

ROOT = Path(__file__).resolve().parents[1]
HASH_A = "sha256:" + ("a" * 64)


def _valid_envelope() -> dict[str, object]:
    return {
        "schema_id": "openpine.run.v2",
        "schema_version": "2.1.0",
        "producer": "openpine-runner",
        "producer_version": "5.0.0-rc.3",
        "producer_commit": "deadbeef",
        "stack_id": "stack-5.0.0-rc.3",
        "created_at_utc_ms": 0,
        "serializer_id": "openpine.canonical.json.v1",
        "content_hash_alg": "sha256",
        "content_hash": HASH_A,
    }


def test_jsonschema_is_a_required_runtime_dependency() -> None:
    project = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))["project"]
    assert any(dependency.startswith("jsonschema>=") for dependency in project["dependencies"])


def test_validate_payload_fails_closed_when_draft_202012_validator_is_unavailable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(validation, "Draft202012Validator", None)

    with pytest.raises(contracts.ContractError) as caught:
        validation.validate_payload("openpine.run.v2", {"schema_id": "openpine.run.v2"})

    assert type(caught.value).__name__ == "SchemaValidatorUnavailableError"
    assert caught.value.code == "SCHEMA_VALIDATOR_UNAVAILABLE"


def test_production_validator_has_no_required_only_fallback() -> None:
    source = (ROOT / "openpine_contracts" / "validate.py").read_text(encoding="utf-8")
    assert "_validate_required_subset" not in source


def test_canonicalization_rejects_nfc_key_collisions() -> None:
    with pytest.raises(contracts.CanonicalizationError) as caught:
        canonical_dumps({"é": 1, "e\u0301": 2})

    assert caught.value.details["normalized_key"] == "é"


def test_seal_content_hash_strips_prior_hash_without_mutating_input() -> None:
    payload: dict[str, Any] = {
        "schema_id": "openpine.run.v2",
        "name": "Cafe\u0301",
        "count": 2,
        "content_hash": HASH_A,
    }
    original = copy.deepcopy(payload)

    sealed = contracts.seal_content_hash(payload)

    assert payload == original
    assert sealed["content_hash"] == (
        "sha256:cf95c43e86cb026685cee9bbd5339d19636b647501a26928005492c90457d30c"
    )
    assert contracts.verify_content_hash(sealed) is True


def test_verify_content_hash_recomputes_and_detects_tampering() -> None:
    sealed = contracts.seal_content_hash(
        {"schema_id": "openpine.run.v2", "run_id": "run-1", "content_hash": HASH_A}
    )
    tampered = dict(sealed, run_id="run-2")

    assert contracts.verify_content_hash(tampered) is False
    assert contracts.verify_content_hash({"schema_id": "openpine.run.v2"}) is False


def test_content_identity_excludes_root_creation_wall_clock() -> None:
    first = contracts.seal_content_hash(
        {
            "schema_id": "openpine.frontend.v2",
            "artifact": "same",
            "created_at_utc_ms": 1,
        }
    )
    second = contracts.seal_content_hash(
        {
            "schema_id": "openpine.frontend.v2",
            "artifact": "same",
            "created_at_utc_ms": 2,
        }
    )

    assert first["created_at_utc_ms"] == 1
    assert second["created_at_utc_ms"] == 2
    assert first["content_hash"] == second["content_hash"]
    assert contracts.verify_content_hash(first) is True
    assert contracts.verify_content_hash(second) is True


def test_seal_content_hash_rejects_float_values() -> None:
    with pytest.raises(contracts.CanonicalizationError, match="float"):
        contracts.seal_content_hash({"schema_id": "openpine.run.v2", "price": 1.25})


def test_artifact_envelope_from_mapping_accepts_exact_contract_types() -> None:
    assert contracts.ArtifactEnvelope.from_mapping(_valid_envelope()).created_at_utc_ms == 0


@pytest.mark.parametrize(
    ("field", "invalid"),
    [
        ("schema_id", ""),
        ("schema_id", "openpine-run-v2"),
        ("schema_version", "2.1"),
        ("producer", ""),
        ("producer_version", "5.0.0rc3"),
        ("producer_commit", ""),
        ("stack_id", ""),
        ("created_at_utc_ms", -1),
        ("created_at_utc_ms", True),
        ("created_at_utc_ms", "0"),
        ("serializer_id", "other"),
        ("content_hash_alg", "md5"),
        ("content_hash", "sha256:abc"),
    ],
)
def test_artifact_envelope_from_mapping_rejects_invalid_values(field: str, invalid: object) -> None:
    payload = _valid_envelope()
    payload[field] = invalid

    with pytest.raises(contracts.ContractError):
        contracts.ArtifactEnvelope.from_mapping(payload)


@pytest.mark.parametrize(
    "field",
    [
        "schema_id",
        "schema_version",
        "producer",
        "producer_version",
        "producer_commit",
        "stack_id",
        "serializer_id",
        "content_hash_alg",
        "content_hash",
    ],
)
def test_artifact_envelope_from_mapping_does_not_coerce_string_fields(field: str) -> None:
    payload = _valid_envelope()
    payload[field] = 123

    with pytest.raises(contracts.ContractError):
        contracts.ArtifactEnvelope.from_mapping(payload)


def test_release_metadata_is_5_0_0_rc5_everywhere() -> None:
    pyproject = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    adr = (ROOT / "docs" / "adr" / "001-versioning.md").read_text(encoding="utf-8")
    workflow = (ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")

    assert pyproject["project"]["version"] == "5.0.0rc5"
    assert contracts.__version__ == "5.0.0rc5"
    assert "5.0.0-rc.5" in readme
    assert "5.0.0-rc.5" in adr
    assert 'openpine_contracts.__version__ == "5.0.0rc5"' in workflow
