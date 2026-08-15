"""Compatibility admission with structured results and codes."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Mapping

from .errors import AdmitError

CODE_OK = "ADMIT_OK"
CODE_SCHEMA_ID = "SCHEMA_ID_MISMATCH"
CODE_MAJOR = "SCHEMA_MAJOR_UNSUPPORTED"
CODE_MINOR_NEW = "SCHEMA_MINOR_TOO_NEW"
CODE_MINOR_OLD = "SCHEMA_MINOR_TOO_OLD"
CODE_CAPS = "MISSING_CAPABILITIES"
CODE_STACK = "STACK_ID_DRIFT"
CODE_HASH = "ARTIFACT_HASH_MISMATCH"


@dataclass(frozen=True, slots=True)
class AdmitRequest:
    schema_id: str
    schema_major: int
    schema_minor: int
    required_capabilities: tuple[str, ...]
    stack_id: str
    artifact_hash: str


@dataclass(frozen=True, slots=True)
class AdmitPolicy:
    supported_schema_id: str
    min_major: int
    max_major: int
    min_minor: int
    max_minor: int
    capabilities: frozenset[str]
    expected_stack_id: str
    expected_artifact_hash: str
    allow_stack_override: bool = False


@dataclass(frozen=True, slots=True)
class AdmitResult:
    admitted: bool
    code: str
    message: str
    details: Mapping[str, object] = field(default_factory=dict)

    def to_dict(self) -> dict[str, object]:
        return {
            "admitted": self.admitted,
            "code": self.code,
            "message": self.message,
            "details": dict(self.details),
        }

    def raise_if_denied(self) -> AdmitResult:
        if not self.admitted:
            raise AdmitError(self.message, code=self.code, details=self.details)
        return self


def evaluate_admit(request: AdmitRequest, policy: AdmitPolicy) -> AdmitResult:
    if request.schema_id != policy.supported_schema_id:
        return AdmitResult(
            False,
            CODE_SCHEMA_ID,
            f"schema_id mismatch: {request.schema_id}",
            {"request": request.schema_id, "policy": policy.supported_schema_id},
        )
    if not (policy.min_major <= request.schema_major <= policy.max_major):
        return AdmitResult(
            False,
            CODE_MAJOR,
            f"schema major not supported: {request.schema_major}",
            {
                "request_major": request.schema_major,
                "min_major": policy.min_major,
                "max_major": policy.max_major,
            },
        )
    if request.schema_major == policy.max_major and request.schema_minor > policy.max_minor:
        return AdmitResult(
            False,
            CODE_MINOR_NEW,
            f"schema minor too new: {request.schema_minor}",
            {"request_minor": request.schema_minor, "max_minor": policy.max_minor},
        )
    if request.schema_major == policy.min_major and request.schema_minor < policy.min_minor:
        return AdmitResult(
            False,
            CODE_MINOR_OLD,
            f"schema minor too old: {request.schema_minor}",
            {"request_minor": request.schema_minor, "min_minor": policy.min_minor},
        )
    missing = [cap for cap in request.required_capabilities if cap not in policy.capabilities]
    if missing:
        return AdmitResult(
            False,
            CODE_CAPS,
            f"missing capabilities: {','.join(missing)}",
            {"missing": missing},
        )
    if request.stack_id != policy.expected_stack_id and not policy.allow_stack_override:
        return AdmitResult(
            False,
            CODE_STACK,
            "stack_id drift",
            {"request_stack_id": request.stack_id, "expected_stack_id": policy.expected_stack_id},
        )
    if request.artifact_hash != policy.expected_artifact_hash:
        return AdmitResult(
            False,
            CODE_HASH,
            "artifact hash mismatch",
            {"request_hash": request.artifact_hash, "expected_hash": policy.expected_artifact_hash},
        )
    return AdmitResult(True, CODE_OK, "admitted", {"schema_id": request.schema_id})


def admit(request: AdmitRequest, policy: AdmitPolicy) -> AdmitResult:
    """Fail-closed admission. Returns a structured result; raises on deny."""
    return evaluate_admit(request, policy).raise_if_denied()
