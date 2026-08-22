"""Canonical JSON serializer and content hashing."""

from __future__ import annotations

import hashlib
import hmac
import json
import math
import unicodedata
from typing import Any, Mapping

from .errors import CanonicalizationError

SERIALIZER_ID = "openpine.canonical.json.v1"
SERIALIZER_VERSION = 1
CONTENT_HASH_ALG = "sha256"


def _is_neg_zero_int(value: int) -> bool:
    return value == 0 and math.copysign(1.0, value) == -1.0


def _normalize(value: Any) -> Any:
    if isinstance(value, dict):
        out: dict[str, Any] = {}
        for key, item in value.items():
            if not isinstance(key, str):
                raise CanonicalizationError(
                    "map keys must be strings",
                    details={"key_type": type(key).__name__},
                )
            normalized_key = unicodedata.normalize("NFC", key)
            if normalized_key in out:
                raise CanonicalizationError(
                    "map keys collide after NFC normalization",
                    details={"normalized_key": normalized_key},
                )
            out[normalized_key] = _normalize(item)
        return {key: out[key] for key in sorted(out)}
    if isinstance(value, (list, tuple)):
        return [_normalize(item) for item in value]
    if isinstance(value, bool) or value is None:
        return value
    if isinstance(value, int) and not isinstance(value, bool):
        if _is_neg_zero_int(value):
            return 0
        return value
    if isinstance(value, float):
        raise CanonicalizationError(
            "float is forbidden on contract boundary; use scaled int or decimal string",
            details={"value": str(value)},
        )
    if isinstance(value, str):
        return unicodedata.normalize("NFC", value)
    raise CanonicalizationError(
        "unsupported type on contract boundary",
        details={"type": type(value).__name__},
    )


def canonical_dumps(payload: Any) -> str:
    try:
        return json.dumps(_normalize(payload), separators=(",", ":"), ensure_ascii=False)
    except CanonicalizationError:
        raise
    except TypeError as exc:
        raise CanonicalizationError(str(exc), details={"cause": "json.dumps"}) from exc


def schema_major_from_id(schema_id: str) -> int:
    if not schema_id:
        raise CanonicalizationError("schema_id is required for hash domain")
    marker = schema_id.rsplit(".", 1)[-1]
    if marker.startswith("v") and marker[1:].isdigit():
        return int(marker[1:])
    raise CanonicalizationError(
        "schema_id must end with .vN major",
        details={"schema_id": schema_id},
    )


def content_hash(
    payload: Any,
    *,
    alg: str = CONTENT_HASH_ALG,
    schema_id: str | None = None,
    schema_major: int | None = None,
) -> str:
    if alg != CONTENT_HASH_ALG:
        raise CanonicalizationError(f"unsupported hash alg: {alg}", details={"alg": alg})
    major = schema_major
    if major is None:
        if schema_id is None:
            raise CanonicalizationError("schema_id or schema_major is required for hash domain")
        major = schema_major_from_id(schema_id)
    domain = {
        "serializer_id": SERIALIZER_ID,
        "serializer_version": SERIALIZER_VERSION,
        "schema_major": major,
        "payload": payload,
    }
    digest = hashlib.sha256(canonical_dumps(domain).encode("utf-8")).hexdigest()
    return f"{alg}:{digest}"


def seal_content_hash(
    payload: Mapping[str, Any],
    *,
    schema_id: str | None = None,
    alg: str = CONTENT_HASH_ALG,
) -> dict[str, Any]:
    """Return a copy sealed over its content, excluding any prior root hash."""
    unsealed = dict(payload)
    unsealed.pop("content_hash", None)
    hash_schema_id = schema_id if schema_id is not None else unsealed.get("schema_id")
    if type(hash_schema_id) is not str:
        raise CanonicalizationError("schema_id must be a string for content sealing")
    sealed = dict(unsealed)
    hash_view = dict(unsealed)
    hash_view.pop("created_at_utc_ms", None)
    sealed["content_hash"] = content_hash(hash_view, alg=alg, schema_id=hash_schema_id)
    return sealed


def verify_content_hash(
    payload: Mapping[str, Any],
    *,
    schema_id: str | None = None,
    alg: str = CONTENT_HASH_ALG,
) -> bool:
    """Recompute and compare a root content hash without trusting the stored value."""
    expected = payload.get("content_hash")
    if type(expected) is not str:
        return False
    try:
        actual = seal_content_hash(payload, schema_id=schema_id, alg=alg)["content_hash"]
    except CanonicalizationError:
        return False
    return hmac.compare_digest(expected, actual)
