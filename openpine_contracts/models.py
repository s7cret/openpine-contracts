"""Canonical enums and immutable public contract types."""

from __future__ import annotations

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
        return cls(
            schema_id=str(payload["schema_id"]),
            schema_version=str(payload["schema_version"]),
            producer=str(payload["producer"]),
            producer_version=str(payload["producer_version"]),
            producer_commit=str(payload["producer_commit"]),
            stack_id=str(payload["stack_id"]),
            created_at_utc_ms=int(str(payload["created_at_utc_ms"])),
            serializer_id=str(payload["serializer_id"]),
            content_hash_alg=str(payload["content_hash_alg"]),
            content_hash=str(payload["content_hash"]),
        )
