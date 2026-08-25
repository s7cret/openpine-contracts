# ADR-001 — Versioning for openpine-contracts

## Status

Accepted. 2026-08-15.

## Decision

- The coordinated RC.4 wheel train uses one PEP 440 version: `5.0.0rc5`
  (displayed as `5.0.0-rc.5`).
- Source commits and wheel hashes remain independent immutable identities in
  the external stack candidate manifest.
- Schema IDs use family names plus major: `openpine.marketdata.v2`.
- Nested types (`CanonicalBar`, `DataSnapshot`, intents) live in `$defs` of the family schema.
- Historical alias `openpine.marketdata.bar.v2` remains registered and maps to the CanonicalBar document schema. New producers emit `openpine.marketdata.v2`.
- Package version PEP 440: `1.0.0rc1`. Display / lock string: `1.0.0-rc.1`.

## Consequences

- Implementation repos pin a contracts wheel, not a sibling checkout.
- Breaking schema changes increment the schema major and the contracts major together.
- Additive schema changes increment schema minor and contracts minor.
