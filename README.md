# openpine-contracts

Canonical contract train for OpenPine **5.0**.

This package owns schemas, IDs, compatibility, and canonical hashing.
It does not own Pine parsing, runtime, fills, or market adapters.

## Scope (v0.1)

- envelope + content hash
- `openpine.marketdata.v2` bar/finality
- `openpine.intent.v2` / `openpine.broker.v2` split
- `openpine.run.v2` identity fields
- compatibility admission helper

Zero runtime dependencies. Python `>=3.11`.
