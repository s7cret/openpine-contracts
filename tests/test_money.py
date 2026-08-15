from openpine_contracts.money import MoneyError, decimal_string


def test_decimal_string_normalizes() -> None:
    assert decimal_string("1.2300") == "1.23"
    assert decimal_string(2) == "2"


def test_decimal_string_rejects_nan() -> None:
    try:
        decimal_string("NaN")
    except MoneyError:
        return
    raise AssertionError("expected MoneyError")
