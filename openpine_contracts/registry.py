"""Installable schema registry. Schemas are package data, not checkout files."""

from __future__ import annotations

import hashlib
import json
from functools import lru_cache
from importlib import resources
from importlib.resources.abc import Traversable
from typing import Mapping

from .errors import SchemaNotFoundError
from .hashing import CONTENT_HASH_ALG

SCHEMA_PACKAGE = "openpine_contracts.schemas"

# Official catalog IDs. Family names + major. Nested types live in $defs.
CATALOG: tuple[str, ...] = (
    "pine.ast.v1",
    "openpine.frontend.v2",
    "openpine.support_profile.v2",
    "openpine.generated_artifact.v2",
    "openpine.runtime.v2",
    "openpine.marketdata.v2",
    "openpine.intent.v2",
    "openpine.broker.v2",
    "openpine.worker.protocol.v2",
    "openpine.run.v2",
    "openpine.trial.v2",
    "openpine.job.v1",
    "openpine.audit.v1",
    "openpine.event.v1",
)

# Migration alias: historical bar document schema.
ALIASES: dict[str, str] = {
    "openpine.marketdata.bar.v2": "openpine.marketdata.bar.v2",
}

FILENAME_BY_ID: dict[str, str] = {
    schema_id: f"{schema_id}.json" for schema_id in (*CATALOG, *ALIASES)
}


def list_schema_ids(*, include_aliases: bool = True) -> tuple[str, ...]:
    if include_aliases:
        return CATALOG + tuple(ALIASES)
    return CATALOG


def _schema_path(schema_id: str) -> Traversable:
    filename = FILENAME_BY_ID.get(schema_id)
    if filename is None:
        raise SchemaNotFoundError(
            f"unknown schema_id: {schema_id}", details={"schema_id": schema_id}
        )
    return resources.files(SCHEMA_PACKAGE).joinpath(filename)


def schema_bytes(schema_id: str) -> bytes:
    path = _schema_path(schema_id)
    if not path.is_file():
        raise SchemaNotFoundError(
            f"schema resource missing: {schema_id}",
            details={"schema_id": schema_id, "filename": FILENAME_BY_ID[schema_id]},
        )
    return bytes(path.read_bytes())


@lru_cache(maxsize=None)
def get_schema(schema_id: str) -> Mapping[str, object]:
    payload = json.loads(schema_bytes(schema_id).decode("utf-8"))
    if not isinstance(payload, dict):
        raise SchemaNotFoundError("schema is not an object", details={"schema_id": schema_id})
    return payload


def schema_hash(schema_id: str, *, alg: str = CONTENT_HASH_ALG) -> str:
    if alg != CONTENT_HASH_ALG:
        raise SchemaNotFoundError(f"unsupported hash alg: {alg}", details={"alg": alg})
    digest = hashlib.sha256(schema_bytes(schema_id)).hexdigest()
    return f"{alg}:{digest}"
