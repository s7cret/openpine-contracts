# ADR-001 — Versioning for openpine-contracts

## Status

Accepted. 2026-08-15.

## Decision

- Stack train uses OpenPine SemVer: `5.0.0-rc.1`, `5.0.0`, ...
- `openpine-contracts` uses its **own** SemVer, starting at `1.0.0-rc.1`.
- These version lines are not mixed. A contracts `1.x` package may be pinned by a `5.0` stack lock.
- Schema IDs use family names plus major: `openpine.marketdata.v2`.
- Nested types (`CanonicalBar`, `DataSnapshot`, intents) live in `$defs` of the family schema.
- Historical alias `openpine.marketdata.bar.v2` remains registered and maps to the CanonicalBar document schema. New producers emit `openpine.marketdata.v2`.
- Package version PEP 440: `1.0.0rc1`. Display / lock string: `1.0.0-rc.1`.

## Consequences

- Implementation repos pin a contracts wheel, not a sibling checkout.
- Breaking schema changes increment the schema major and the contracts major together.
- Additive schema changes increment schema minor and contracts minor.
