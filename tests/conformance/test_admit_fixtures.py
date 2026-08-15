import json
from pathlib import Path

from openpine_contracts import AdmitPolicy, AdmitRequest, evaluate_admit

CASES = json.loads(
    (Path(__file__).resolve().parents[1] / "fixtures" / "admit_cases.json").read_text()
)


def test_admit_fixture_matrix() -> None:
    base_policy = CASES["ok"]["policy"]
    policy = AdmitPolicy(
        supported_schema_id=base_policy["supported_schema_id"],
        min_major=base_policy["min_major"],
        max_major=base_policy["max_major"],
        min_minor=base_policy["min_minor"],
        max_minor=base_policy["max_minor"],
        capabilities=frozenset(base_policy["capabilities"]),
        expected_stack_id=base_policy["expected_stack_id"],
        expected_artifact_hash=base_policy["expected_artifact_hash"],
    )
    for name, case in CASES.items():
        req_raw = case["request"]
        request = AdmitRequest(
            schema_id=req_raw["schema_id"],
            schema_major=req_raw["schema_major"],
            schema_minor=req_raw["schema_minor"],
            required_capabilities=tuple(req_raw["required_capabilities"]),
            stack_id=req_raw["stack_id"],
            artifact_hash=req_raw["artifact_hash"],
        )
        result = evaluate_admit(request, policy)
        assert result.code == case["expected_code"], name
