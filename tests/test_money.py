from decimal import Decimal

from openpine_contracts import Money, MoneyError, decimal_string, unsafe_decimal_from_float


def test_decimal_string_normalizes() -> None:
    assert decimal_string("1.2300") == "1.23"
    assert decimal_string(2) == "2"
    assert decimal_string(Decimal("4.50")) == "4.5"


def test_negative_zero_canonicalizes() -> None:
    assert decimal_string("-0") == "0"
    assert decimal_string("-0.0") == "0"
    assert decimal_string(Decimal("-0")) == "0"
    assert decimal_string(0) == "0"


def test_scientific_notation_and_huge_precision() -> None:
    assert decimal_string("1.23E+3") == "1230"
    assert decimal_string("1.2300E-2") == "0.0123"
    huge = "1." + ("0" * 40) + "1"
    assert decimal_string(huge) == "1." + ("0" * 40) + "1"


def test_idempotent_and_locale_independent() -> None:
    assert decimal_string(decimal_string("10.500")) == "10.5"
    try:
        decimal_string("1,23")
    except MoneyError:
        return
    raise AssertionError("expected MoneyError")


def test_rejects_bool_nan_inf_float() -> None:
    for value in (True, False, "NaN", "Infinity", "-Infinity", 1.25):
        try:
            decimal_string(value)  # type: ignore[arg-type]
        except MoneyError:
            continue
        raise AssertionError(f"expected MoneyError for {value!r}")


def test_money_requires_currency() -> None:
    money = Money(amount="1.2300", currency="USDT", scale=2)
    assert money.to_dict() == {"amount": "1.23", "currency": "USDT", "scale": 2}
    try:
        Money(amount="1", currency=" ")
    except MoneyError:
        return
    raise AssertionError("expected MoneyError")


def test_unsafe_float_helper_is_explicit() -> None:
    assert unsafe_decimal_from_float(1.5) == "1.5"
