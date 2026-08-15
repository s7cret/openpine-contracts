from __future__ import annotations

from dataclasses import dataclass


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


class AdmitError(ValueError):
    pass


def admit(request: AdmitRequest, policy: AdmitPolicy) -> None:
    if request.schema_id != policy.supported_schema_id:
        raise AdmitError(f"schema_id mismatch: {request.schema_id}")
    if not (policy.min_major <= request.schema_major <= policy.max_major):
        raise AdmitError(f"schema major not supported: {request.schema_major}")
    if request.schema_major == policy.max_major and request.schema_minor > policy.max_minor:
        raise AdmitError(f"schema minor too new: {request.schema_minor}")
    if request.schema_major == policy.min_major and request.schema_minor < policy.min_minor:
        raise AdmitError(f"schema minor too old: {request.schema_minor}")
    missing = [cap for cap in request.required_capabilities if cap not in policy.capabilities]
    if missing:
        raise AdmitError(f"missing capabilities: {','.join(missing)}")
    if request.stack_id != policy.expected_stack_id and not policy.allow_stack_override:
        raise AdmitError("stack_id drift")
    if request.artifact_hash != policy.expected_artifact_hash:
        raise AdmitError("artifact hash mismatch")
