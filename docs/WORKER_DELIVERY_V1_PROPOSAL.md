# Worker delivery v1 proposal

This draft adds `openpine.worker.delivery.v1`, version `1.0.0`, without changing
the current catalog, registry, package root exports or `worker.protocol.v2`
version `2.3.0`. Import `openpine_contracts.proposals.worker_delivery` explicitly
to review the draft. Its JSON resource has a `.proposal.json` suffix and is not
discoverable through `get_schema` or `list_schema_ids`.
The resource lives in the separate `openpine_contracts.proposals` package with
an explicit package-data entry; the current schema generator's resource closure
remains intact.

The proposal is a bounded detached transcript validator and payload framer.
It performs no worker launch, transport I/O, owner activation or database write.
It reuses canonical sealing and the existing v2 schema/semantic validator. It
does not decode native/Pine state or establish that a receipt was durably stored.

## Physical and logical identities

The closed outer envelope binds job, run, logical session, physical worker ID,
generation, delivery ID, role, stack and producer identity. Its physical `HELLO`
negotiates exact `delivery_v1`/`committed_job_v1` capabilities, both schema hashes,
limits and the admitted recovery checkpoint. The trusted caller supplies the
expected binding; a wire message cannot choose its own generation or identity.

`MESSAGE` carries existing sealed v2.3.0 frames without rewriting their bytes,
IDs, causation or sequences. Parent and engine frames use the parent physical
channel; worker frames use the worker channel. Physical recovery controls never
consume the logical cursor. Historical inner control frames remain valid parts
of the existing immutable protocol; new producers must distinguish these from
physical recovery operations when the coordinated consumer design is adopted.

Legacy fresh `closed_bar` traffic retains its current transport. Recovery mode
must explicitly negotiate the new capability; an old worker must refuse a
request requiring it. This draft does not alter that negotiation in consumers.

## Complete cuts, acknowledgments and repetition

The caller supplies immutable `CutReceipt` views from its existing durable job
owner. They bind the active physical generation, full admitted committed v2
prefix, checkpoint and raw payload hashes/size, callback/intent cursors and the
last acknowledged frame. Complete prefixes are checked through the current
validator using a detached terminal at BAR_COMMIT. That terminal is not emitted.

`RESTORE` requires the admitted checkpoint's fully reconstructed payload and
preserves its logical/ack cursor without replay. A conflicting restore after
progress refuses. Exact delivery ID/hash repeats produce no second operation,
including restore or handshake repeats after progress. Conflicting repeats fail.

`ACK` binds the exact message ID/hash/sequence, committed checkpoint and owner
cursors. It requires a matching durable-owner view and delivered committed
prefix, correct receiving role and contiguous advancement. Provisional frames,
gaps, foreign cuts and mismatched cursors refuse. Exact repeats cannot roll back
acknowledgments. Publication, native/Pine admission and fsync remain the existing
owners' responsibilities; this validator cannot attest those operations.

## Transport bounds

| Bound | Bytes/count |
|---|---:|
| Raw chunk | 131,072 |
| Encoded envelope | 262,144 |
| Aggregate raw payload per detached transcript | 16,777,216 |
| Encoded detached transcript | 33,554,432 |
| Frames/cut views per detached transcript | 4,096 |
| JSON nesting | 64 |

`PAYLOAD_BEGIN` declares an exact size and SHA-256; indexed chunks bind their
payload ID and hashes; `PAYLOAD_END` binds count, whole size and hash. Base64 is
canonical. Missing EOF, overlapping transfers, malformed/oversized frames,
nonfinite values, duplicate JSON keys and exhausted budgets refuse. The producer
emits bounded chunks; the detached validator holds bounded reconstructed bytes.
Future streaming consumers should reuse the existing 2 MiB spool mechanism;
there is no spool or external URI reader in this draft.

## Decision before consumers

Agree the additive outer schema/version, capabilities, physical recovery versus
logical control behavior, ACK owner boundary and these limits before registering
the schema or connecting producer/consumer adapters. This follows specification
section 11.1: common schema changes are coordinated before implementing consumers.
Standing code/commit/draft PR authorization already covers this producer draft.

Next consumers belong to OpenPine runtime/jobs, capability negotiation and trusted
helper staging. Changes to frozen INT04 launch bindings and actual protected
fault qualification require their separate authorization. No Pine/native decoder
replacement or isolation relaxation is proposed. Normal/sdist installed checks,
the required Python matrices, complete candidate bindings and protected recovery
qualification remain future obligations. Unit fixtures here use opaque framing
payloads and synthetic owner views and grant none of those acceptance claims.
