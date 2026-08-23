"""Typed contract errors with stable diagnostic codes."""

from __future__ import annotations

from typing import Mapping


class ContractError(ValueError):
    code = "CONTRACT_ERROR"

    def __init__(self, message: str, *, details: Mapping[str, object] | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.details: Mapping[str, object] = dict(details or {})

    def to_dict(self) -> dict[str, object]:
        return {"code": self.code, "message": self.message, "details": dict(self.details)}


class CanonicalizationError(ContractError):
    code = "CANONICALIZATION_ERROR"


class SchemaNotFoundError(ContractError):
    code = "SCHEMA_NOT_FOUND"


class SchemaValidationError(ContractError):
    code = "SCHEMA_VALIDATION_ERROR"


class SchemaValidatorUnavailableError(ContractError):
    code = "SCHEMA_VALIDATOR_UNAVAILABLE"


class WorkerProtocolSemanticError(ContractError):
    code = "WORKER_PROTOCOL_SEMANTIC_ERROR"


class MoneyError(ContractError):
    code = "MONEY_ERROR"


class AdmitError(ContractError):
    code = "ADMIT_ERROR"

    def __init__(
        self,
        message: str,
        *,
        code: str | None = None,
        details: Mapping[str, object] | None = None,
    ) -> None:
        super().__init__(message, details=details)
        if code is not None:
            self.code = code
