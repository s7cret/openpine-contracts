# openpine-contracts

Canonical contract train for OpenPine 5.0.

This package owns schemas, IDs, compatibility, and canonical hashing.
It does not own Pine parsing, runtime, fills, or market adapters.

Version policy: the coordinated stack candidate is `5.0.0-rc.4`
(PEP 440 `5.0.0rc4`). Internal wheel dependencies use this exact version;
immutable Git and wheel hashes are bound by the external stack candidate manifest.
See `docs/adr/001-versioning.md`.

## Catalog

Official family IDs:

- `pine.ast.v1`
- `openpine.frontend.v2`
- `openpine.support_profile.v2`
- `openpine.generated_artifact.v2`
- `openpine.runtime.v2`
- `openpine.marketdata.v2`
- `openpine.execution_context.v1`
- `openpine.intent.v2`
- `openpine.broker.v2`
- `openpine.broker_projection.v1`
- `openpine.checkpoint.v1`
- `openpine.worker.protocol.v2`
- `openpine.run.v2`
- `openpine.trial.identity.v1`
- `openpine.trial.v2`
- `openpine.job.v1`
- `openpine.audit.v1`
- `openpine.event.v1`

Migration alias: `openpine.marketdata.bar.v2` (CanonicalBar document).
New producers emit `openpine.marketdata.v2`.

Schemas ship inside the wheel and are read via `importlib.resources`.

## API

```python
from openpine_contracts import (
    get_schema,
    schema_bytes,
    schema_hash,
    validate_payload,
    canonical_dumps,
    content_hash,
    seal_content_hash,
    verify_content_hash,
    decimal_string,
    Money,
    admit,
    evaluate_admit,
    validate_worker_protocol_sequence,
)
```

Draft 2020-12 validation is fail-closed and requires `jsonschema>=4.20,<5`
(including its `referencing` dependency for packaged cross-schema references).
Python `>=3.11`.
