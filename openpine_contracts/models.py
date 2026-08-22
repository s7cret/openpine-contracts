"""Canonical enums and immutable public contract types."""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import StrEnum
from typing import Mapping

from .errors import ContractError
from .hashing import CONTENT_HASH_ALG, SERIALIZER_ID


class Finality(StrEnum):
    OPEN = "OPEN"
    FINAL = "FINAL"


class RevisionState(StrEnum):
    ORIGINAL = "ORIGINAL"
    CORRECTED = "CORRECTED"
    REVOKED = "REVOKED"


class SemanticProfile(StrEnum):
    LEGACY_4X = "legacy_4x"
    STRICT_5X = "strict_5x"


class WarmupMode(StrEnum):
    CALC_ONLY = "CALC_ONLY"
    TRADE_THROUGH_UNSCORED = "TRADE_THROUGH_UNSCORED"
    CALC_THEN_RESET_BROKER = "CALC_THEN_RESET_BROKER"


class RunMode(StrEnum):
    COMPILE = "COMPILE"
    BACKTEST = "BACKTEST"
    OPTIMIZE = "OPTIMIZE"
    PARITY = "PARITY"
    PAPER = "PAPER"
    LIVE = "LIVE"
    BACKFILL = "BACKFILL"


class JobState(StrEnum):
    QUEUED = "QUEUED"
    RUNNING = "RUNNING"
    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"
    CANCELED = "CANCELED"
    RETRY_WAIT = "RETRY_WAIT"
    LOST = "LOST"


class SupportStatus(StrEnum):
    SUPPORTED = "SUPPORTED"
    CONDITIONAL = "CONDITIONAL"
    VISUAL_ONLY = "VISUAL_ONLY"
    UNSUPPORTED = "UNSUPPORTED"
    NOT_APPLICABLE = "NOT_APPLICABLE"


class IntentKind(StrEnum):
    ENTRY = "entry"
    ORDER = "order"
    EXIT = "exit"
    CLOSE = "close"
    CLOSE_ALL = "close_all"
    CANCEL = "cancel"
    CANCEL_ALL = "cancel_all"
    RISK = "risk"


ENVELOPE_FIELDS = (
    "schema_id",
    "schema_version",
    "producer",
    "producer_version",
    "producer_commit",
    "stack_id",
    "created_at_utc_ms",
    "serializer_id",
    "content_hash_alg",
    "content_hash",
)

SCHEMA_ID_RE = re.compile(r"^[a-z][a-z0-9]*(?:[._-][a-z0-9]+)*\.v[1-9][0-9]*$")
SEMVER_RE = re.compile(
    r"^(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)"
    r"(?:-(?:0|[1-9][0-9]*|[0-9]*[A-Za-z-][0-9A-Za-z-]*)"
    r"(?:\.(?:0|[1-9][0-9]*|[0-9]*[A-Za-z-][0-9A-Za-z-]*))*)?"
    r"(?:\+[0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*)?$"
)
CONTENT_HASH_RE = re.compile(r"^sha256:[0-9a-f]{64}$")


def _exact_nonempty_string(payload: Mapping[str, object], field: str) -> str:
    value = payload[field]
    if type(value) is not str or not value.strip():
        raise ContractError(
            "artifact envelope field must be a nonempty string",
            details={"field": field, "actual_type": type(value).__name__},
        )
    return value


@dataclass(frozen=True, slots=True)
class ArtifactEnvelope:
    schema_id: str
    schema_version: str
    producer: str
    producer_version: str
    producer_commit: str
    stack_id: str
    created_at_utc_ms: int
    serializer_id: str = SERIALIZER_ID
    content_hash_alg: str = CONTENT_HASH_ALG
    content_hash: str = ""

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_id": self.schema_id,
            "schema_version": self.schema_version,
            "producer": self.producer,
            "producer_version": self.producer_version,
            "producer_commit": self.producer_commit,
            "stack_id": self.stack_id,
            "created_at_utc_ms": self.created_at_utc_ms,
            "serializer_id": self.serializer_id,
            "content_hash_alg": self.content_hash_alg,
            "content_hash": self.content_hash,
        }

    @classmethod
    def from_mapping(cls, payload: Mapping[str, object]) -> ArtifactEnvelope:
        missing = [field for field in ENVELOPE_FIELDS if field not in payload]
        if missing:
            raise ContractError("artifact envelope incomplete", details={"missing": missing})
        strings = {
            field: _exact_nonempty_string(payload, field)
            for field in ENVELOPE_FIELDS
            if field != "created_at_utc_ms"
        }
        created_at_utc_ms = payload["created_at_utc_ms"]
        if type(created_at_utc_ms) is not int or created_at_utc_ms < 0:
            raise ContractError(
                "created_at_utc_ms must be a nonnegative integer",
                details={"actual_type": type(created_at_utc_ms).__name__},
            )
        if SCHEMA_ID_RE.fullmatch(strings["schema_id"]) is None:
            raise ContractError("schema_id must be a versioned contract ID")
        for field in ("schema_version", "producer_version"):
            if SEMVER_RE.fullmatch(strings[field]) is None:
                raise ContractError("version must be SemVer", details={"field": field})
        if strings["serializer_id"] != SERIALIZER_ID:
            raise ContractError("unsupported serializer_id")
        if strings["content_hash_alg"] != CONTENT_HASH_ALG:
            raise ContractError("unsupported content_hash_alg")
        if CONTENT_HASH_RE.fullmatch(strings["content_hash"]) is None:
            raise ContractError("content_hash must be a canonical sha256 hash")
        return cls(created_at_utc_ms=created_at_utc_ms, **strings)
