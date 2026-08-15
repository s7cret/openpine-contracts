from __future__ import annotations

from enum import StrEnum


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
