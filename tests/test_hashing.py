from openpine_contracts import canonical_dumps, content_hash


def test_canonical_hash_is_key_order_stable() -> None:
    left = {"b": 2, "a": 1}
    right = {"a": 1, "b": 2}
    assert canonical_dumps(left) == '{"a":1,"b":2}'
    assert content_hash(left) == content_hash(right)


def test_float_is_rejected() -> None:
    try:
        content_hash({"px": 1.25})
    except ValueError as exc:
        assert "float" in str(exc)
    else:
        raise AssertionError("expected ValueError")
