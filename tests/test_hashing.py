import unicodedata

from openpine_contracts import SERIALIZER_ID, CanonicalizationError, canonical_dumps, content_hash


def test_canonical_hash_is_key_order_stable() -> None:
    left = {"b": 2, "a": 1}
    right = {"a": 1, "b": 2}
    assert canonical_dumps(left) == '{"a":1,"b":2}'
    assert content_hash(left, schema_id="openpine.run.v2") == content_hash(
        right, schema_id="openpine.run.v2"
    )


def test_float_is_rejected() -> None:
    try:
        content_hash({"px": 1.25}, schema_id="openpine.run.v2")
    except CanonicalizationError as exc:
        assert exc.code == "CANONICALIZATION_ERROR"
        assert "float" in str(exc)
    else:
        raise AssertionError("expected CanonicalizationError")


def test_unknown_object_is_canonicalization_error() -> None:
    try:
        canonical_dumps({"x": object()})
    except CanonicalizationError as exc:
        assert "unsupported type" in str(exc)
    else:
        raise AssertionError("expected CanonicalizationError")


def test_non_string_key_rejected() -> None:
    try:
        canonical_dumps({1: "a"})  # type: ignore[dict-item]
    except CanonicalizationError:
        return
    raise AssertionError("expected CanonicalizationError")


def test_unicode_nfc_and_hash_domain() -> None:
    nfd = "e\u0301"
    nfc = unicodedata.normalize("NFC", nfd)
    assert canonical_dumps({"name": nfd}) == canonical_dumps({"name": nfc})
    left = content_hash({"a": 1}, schema_id="openpine.run.v2")
    right = content_hash({"a": 1}, schema_major=2)
    assert left == right
    assert left.startswith("sha256:")
    assert SERIALIZER_ID
    other_major = content_hash({"a": 1}, schema_id="openpine.job.v1")
    assert left != other_major
