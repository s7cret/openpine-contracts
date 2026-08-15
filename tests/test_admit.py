from openpine_contracts import AdmitError, AdmitPolicy, AdmitRequest, admit, evaluate_admit
from openpine_contracts.compatibility import CODE_MAJOR, CODE_OK, CODE_STACK


def _ok() -> tuple[AdmitRequest, AdmitPolicy]:
    req = AdmitRequest(
        schema_id="openpine.run.v2",
        schema_major=2,
        schema_minor=0,
        required_capabilities=("closed_bar",),
        stack_id="stack-1",
        artifact_hash="sha256:aaa",
    )
    policy = AdmitPolicy(
        supported_schema_id="openpine.run.v2",
        min_major=2,
        max_major=2,
        min_minor=0,
        max_minor=5,
        capabilities=frozenset({"closed_bar", "mtf"}),
        expected_stack_id="stack-1",
        expected_artifact_hash="sha256:aaa",
    )
    return req, policy


def test_admit_ok() -> None:
    req, policy = _ok()
    result = admit(req, policy)
    assert result.admitted is True
    assert result.code == CODE_OK


def test_stack_drift_fail_closed() -> None:
    req, policy = _ok()
    req = AdmitRequest(
        schema_id=req.schema_id,
        schema_major=req.schema_major,
        schema_minor=req.schema_minor,
        required_capabilities=req.required_capabilities,
        stack_id="other",
        artifact_hash=req.artifact_hash,
    )
    result = evaluate_admit(req, policy)
    assert result.admitted is False
    assert result.code == CODE_STACK
    try:
        admit(req, policy)
    except AdmitError as exc:
        assert exc.code == CODE_STACK
        assert "stack_id" in str(exc)
    else:
        raise AssertionError("expected AdmitError")


def test_unsupported_major_has_stable_code() -> None:
    req, policy = _ok()
    req = AdmitRequest(
        schema_id=req.schema_id,
        schema_major=3,
        schema_minor=0,
        required_capabilities=req.required_capabilities,
        stack_id=req.stack_id,
        artifact_hash=req.artifact_hash,
    )
    result = evaluate_admit(req, policy)
    assert result.code == CODE_MAJOR
    assert result.to_dict()["admitted"] is False
