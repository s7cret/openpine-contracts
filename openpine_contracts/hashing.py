from __future__ import annotations

import hashlib
import json
from typing import Any


def _normalize(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(k): _normalize(value[k]) for k in sorted(value)}
    if isinstance(value, (list, tuple)):
        return [_normalize(item) for item in value]
    if isinstance(value, bool) or value is None:
        return value
    if isinstance(value, int) and not isinstance(value, bool):
        return value
    if isinstance(value, float):
        raise ValueError("float is forbidden on contract boundary; use scaled int or decimal string")
    return value


def canonical_dumps(payload: Any) -> str:
    return json.dumps(_normalize(payload), separators=(",", ":"), ensure_ascii=False)


def content_hash(payload: Any, *, alg: str = "sha256") -> str:
    if alg != "sha256":
        raise ValueError(f"unsupported hash alg: {alg}")
    digest = hashlib.sha256(canonical_dumps(payload).encode("utf-8")).hexdigest()
    return f"sha256:{digest}"
