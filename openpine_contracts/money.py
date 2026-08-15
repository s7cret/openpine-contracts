"""Canonical decimal and money helpers. Float is never accepted."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from typing import Mapping

from .errors import MoneyError

# Contract boundary stores unlimited normalized decimal strings.
# Consumers apply instrument scale/rounding separately.
DECIMAL_POLICY = "unlimited_normalized_decimal_string"


def decimal_string(value: str | int | Decimal) -> str:
    if isinstance(value, bool):
        raise MoneyError("bool is not a decimal value", details={"value": value})
    if isinstance(value, float):
        raise MoneyError(
            "float is forbidden; use unsafe_decimal_from_float only for migrations",
            details={"value": str(value)},
        )
    if isinstance(value, str):
        text = value.strip()
        if not text:
            raise MoneyError("empty decimal string")
        if any(ch in text for ch in " ,_\t"):
            raise MoneyError("decimal string must be locale-independent", details={"value": value})
        raw = text
    elif isinstance(value, int):
        raw = str(value)
    elif isinstance(value, Decimal):
        raw = format(value, "f") if value.is_finite() else str(value)
    else:
        raise MoneyError("unsupported decimal type", details={"type": type(value).__name__})
    try:
        number = Decimal(raw)
    except (InvalidOperation, ValueError) as exc:
        raise MoneyError(
            f"invalid decimal value: {value!r}", details={"value": str(value)}
        ) from exc
    if not number.is_finite():
        raise MoneyError("decimal must be finite", details={"value": str(value)})
    if number.is_zero():
        return "0"
    text = format(number, "f")
    if "." in text:
        text = text.rstrip("0").rstrip(".")
    return text or "0"


def unsafe_decimal_from_float(value: float) -> str:
    """Migration-only. Never used by canonical serializers."""
    if isinstance(value, bool) or not isinstance(value, float):
        raise MoneyError("unsafe helper accepts float only")
    if not math_is_finite(value):
        raise MoneyError("decimal must be finite")
    return decimal_string(format(value, ".17g"))


def math_is_finite(value: float) -> bool:
    return value == value and value not in (float("inf"), float("-inf"))


@dataclass(frozen=True, slots=True)
class Money:
    amount: str
    currency: str
    scale: int | None = None

    def __post_init__(self) -> None:
        if not self.currency or not self.currency.strip():
            raise MoneyError("money requires currency/asset")
        object.__setattr__(self, "amount", decimal_string(self.amount))
        if self.scale is not None and self.scale < 0:
            raise MoneyError("scale must be >= 0", details={"scale": self.scale})

    def to_dict(self) -> dict[str, object]:
        payload: dict[str, object] = {"amount": self.amount, "currency": self.currency}
        if self.scale is not None:
            payload["scale"] = self.scale
        return payload

    @classmethod
    def from_mapping(cls, payload: Mapping[str, object]) -> Money:
        amount = payload.get("amount")
        currency = payload.get("currency")
        scale = payload.get("scale")
        if not isinstance(amount, (str, int, Decimal)):
            raise MoneyError("money.amount missing or invalid")
        if not isinstance(currency, str):
            raise MoneyError("money.currency missing or invalid")
        if scale is not None and not isinstance(scale, int):
            raise MoneyError("money.scale must be int or omitted")
        return cls(amount=decimal_string(amount), currency=currency, scale=scale)
