from __future__ import annotations

from decimal import Decimal, InvalidOperation


class MoneyError(ValueError):
    pass


def decimal_string(value: str | int | Decimal) -> str:
    if isinstance(value, bool):
        raise MoneyError("bool is not a money value")
    try:
        number = Decimal(str(value))
    except (InvalidOperation, ValueError) as exc:
        raise MoneyError(f"invalid money value: {value!r}") from exc
    if not number.is_finite():
        raise MoneyError("money must be finite")
    text = format(number, "f")
    if "." in text:
        text = text.rstrip("0").rstrip(".")
    return text or "0"
