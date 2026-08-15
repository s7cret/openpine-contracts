# openpine-contracts

Canonical contract train for OpenPine 5.0.

This package owns schemas, IDs, compatibility, and canonical hashing.
It does not own Pine parsing, runtime, fills, or market adapters.

Version policy: contracts SemVer `1.0.0-rc.1` (PEP 440 `1.0.0rc1`).
The OpenPine stack train (`5.0.0-rc.1`) pins this package; the two version lines are not mixed.
See `docs/adr/001-versioning.md`.

## Catalog

Official family IDs:

- `pine.ast.v1`
- `openpine.frontend.v2`
- `openpine.support_profile.v2`
- `openpine.generated_artifact.v2`
- `openpine.runtime.v2`
- `openpine.marketdata.v2`
- `openpine.intent.v2`
- `openpine.broker.v2`
- `openpine.run.v2`
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
    decimal_string,
    Money,
    admit,
    evaluate_admit,
)
```

Zero required runtime dependencies. Optional extra: `validation` (`jsonschema`).
Python `>=3.11`.
