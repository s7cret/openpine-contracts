"""Bounded delivery.v1 checks over the unchanged logical worker protocol.

CutReceipt inputs are trusted owner-admitted durable views. This module checks
their bindings, not fsync, native/Pine decoding, worker activation or authenticity.
It neither registers its schema nor exports an API from the current package root.
"""

from __future__ import annotations

import base64
import hashlib
import json
import re
from collections.abc import Iterator, Mapping, Sequence
from dataclasses import dataclass
from functools import lru_cache
from typing import Any, NoReturn

from .errors import ContractError
from .hashing import canonical_dumps, seal_content_hash, verify_content_hash
from .registry import schema_bytes, schema_hash
from .validate import (
    Draft202012Specification,
    Draft202012Validator,
    SchemaResource,
    _packaged_registry,
    validate_payload,
)
from .worker_protocol import validate_worker_protocol_sequence

SCHEMA_ID = "openpine.worker.delivery.v1"
CHUNK_BYTES = 128 * 1024
FRAME_BYTES = 256 * 1024
PAYLOAD_BYTES = 16 * 1024 * 1024
TRANSCRIPT_BYTES = 32 * 1024 * 1024
TRANSCRIPT_FRAMES = 4096
LIMITS = {
    "raw_chunk_bytes": CHUNK_BYTES,
    "frame_bytes": FRAME_BYTES,
    "payload_bytes": PAYLOAD_BYTES,
    "transcript_bytes": TRANSCRIPT_BYTES,
    "transcript_frames": TRANSCRIPT_FRAMES,
}


class DeliveryProposalError(ContractError):
    code = "WORKER_DELIVERY_PROPOSAL_ERROR"


def _fail(reason: str) -> NoReturn:
    raise DeliveryProposalError(reason, details={"reason": reason})


def raw_hash(wire: bytes) -> str:
    return "sha256:" + hashlib.sha256(wire).hexdigest()


def proposal_schema_bytes() -> bytes:
    """Compatibility alias for the registered additive schema bytes."""
    return schema_bytes(SCHEMA_ID)


@lru_cache(maxsize=1)
def _validator() -> Any:
    schema = json.loads(proposal_schema_bytes())
    if Draft202012Validator is None or SchemaResource is None:
        _fail("SCHEMA_VALIDATOR_UNAVAILABLE")
    Draft202012Validator.check_schema(schema)
    registry = _packaged_registry().with_resource(
        SCHEMA_ID,
        SchemaResource.from_contents(schema, default_specification=Draft202012Specification),
    )
    return Draft202012Validator(schema, registry=registry)


def _unique(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            _fail("DUPLICATE_JSON_KEY")
        result[key] = value
    return result


def _constant(value: str) -> None:
    _fail("NONFINITE_JSON: " + value)


def decode_frame(wire: bytes) -> dict[str, Any]:
    if type(wire) is not bytes or not wire or len(wire) > FRAME_BYTES:
        _fail("FRAME_BYTES")
    depth, quoted, escaped = 0, False, False
    for byte in wire:
        if quoted:
            if escaped:
                escaped = False
            elif byte == 92:
                escaped = True
            elif byte == 34:
                quoted = False
        elif byte == 34:
            quoted = True
        elif byte in (91, 123):
            depth += 1
            if depth > 64:
                _fail("JSON_DEPTH")
        elif byte in (93, 125):
            depth -= 1
    try:
        value = json.loads(
            wire.decode("utf-8"), object_pairs_hook=_unique, parse_constant=_constant
        )
    except DeliveryProposalError:
        raise
    except (ValueError, UnicodeError, RecursionError) as error:
        raise DeliveryProposalError("INVALID_JSON") from error
    if type(value) is not dict:
        _fail("FRAME_OBJECT")
    if next(_validator().iter_errors(value), None) is not None:
        _fail("SCHEMA")
    if not verify_content_hash(value, schema_id=SCHEMA_ID):
        _fail("CONTENT_HASH")
    return dict(value)


@dataclass(frozen=True)
class DeliveryBinding:
    job_id: str
    run_id: str
    session_id: str
    worker_id: str
    worker_generation: int
    stack_id: str
    producer_commit: str


@dataclass(frozen=True)
class CutReceipt:
    """Trusted durable owner's immutable view, not an assertion from wire JSON."""

    binding: DeliveryBinding
    checkpoint_hash: str
    payload_sha256: str
    payload_size: int
    callback_sequence: int
    intent_sequence: int
    frames: tuple[bytes, ...]
    last_acknowledged_frame: int = -1


@dataclass(frozen=True)
class DeliveryProjection:
    logical_next_sequence: int
    last_acknowledged_frame: int
    repeated_deliveries: int
    payloads: tuple[tuple[str, bytes], ...]


def _logical(wire: bytes) -> dict[str, Any]:
    if type(wire) is not bytes or not wire or len(wire) > FRAME_BYTES:
        _fail("LOGICAL_FRAME_BYTES")
    try:
        value = json.loads(
            wire.decode("utf-8"), object_pairs_hook=_unique, parse_constant=_constant
        )
    except DeliveryProposalError:
        raise
    except (ValueError, UnicodeError, RecursionError) as error:
        raise DeliveryProposalError("LOGICAL_JSON") from error
    validate_payload("openpine.worker.protocol.v2", value)
    if not verify_content_hash(value, schema_id="openpine.worker.protocol.v2"):
        _fail("LOGICAL_CONTENT_HASH")
    return dict(value)


def _complete_prefix(messages: list[dict[str, Any]]) -> None:
    if not messages:
        return
    if messages[-1]["kind"] == "BAR_COMMIT":
        commit = messages[-1]
        body = commit["body"]
        final = seal_content_hash(
            {
                **commit,
                "producer": "openpine",
                "producer_commit": messages[0]["producer_commit"],
                "kind": "FINALIZE",
                "sender_role": "parent",
                "sequence": commit["sequence"] + 1,
                "message_id": "proposal-terminal:" + commit["message_id"],
                "causation_id": commit["message_id"],
                "body": {
                    "run_id": commit["run_id"],
                    "final_sequence": commit["sequence"],
                    "final_state_hash": body["state_hash"],
                    "broker_projection_hash": body["broker_projection_hash"],
                    "last_commit_message_id": commit["message_id"],
                    "last_committed_sequence": commit["sequence"],
                },
            },
            schema_id="openpine.worker.protocol.v2",
        )
        validate_worker_protocol_sequence([*messages, final])
    else:
        validate_worker_protocol_sequence(messages)


def validate_delivery_sequence(
    wires: Sequence[bytes],
    binding: DeliveryBinding,
    *,
    durable_cuts: Sequence[CutReceipt] = (),
    restored_cut: CutReceipt | None = None,
) -> DeliveryProjection:
    """Admit one bounded detached transcript; rejection changes no caller owner.

    The final logical prefix must end at BAR_COMMIT or a terminal. Streaming
    adapters must admit complete batches before invoking owners.
    """
    if type(binding.worker_generation) is not int or binding.worker_generation < 1:
        _fail("BINDING_GENERATION")
    if not wires or len(wires) > TRANSCRIPT_FRAMES:
        _fail("TRANSCRIPT_FRAMES")
    if any(type(w) is not bytes for w in wires) or sum(map(len, wires)) > TRANSCRIPT_BYTES:
        _fail("TRANSCRIPT_BYTES")
    cuts: dict[str, tuple[CutReceipt, list[dict[str, Any]]]] = {}
    cut_bytes = 0
    if len(durable_cuts) > TRANSCRIPT_FRAMES:
        _fail("CUT_COUNT")
    for cut in durable_cuts:
        if cut.checkpoint_hash in cuts:
            _fail("DUPLICATE_CUT")
        if (
            cut.binding != binding
            or type(cut.frames) is not tuple
            or not re.fullmatch(r"sha256:(?!0{64}$)[0-9a-f]{64}", cut.checkpoint_hash)
            or not re.fullmatch(r"sha256:(?!0{64}$)[0-9a-f]{64}", cut.payload_sha256)
            or type(cut.payload_size) is not int
            or not 0 < cut.payload_size <= PAYLOAD_BYTES
            or type(cut.callback_sequence) is not int
            or cut.callback_sequence < 0
            or type(cut.intent_sequence) is not int
            or cut.intent_sequence < 0
            or type(cut.last_acknowledged_frame) is not int
            or not -1 <= cut.last_acknowledged_frame < len(cut.frames)
        ):
            _fail("CUT_CURSOR")
        if len(cut.frames) > TRANSCRIPT_FRAMES or any(type(w) is not bytes for w in cut.frames):
            _fail("CUT_BYTES")
        cut_bytes += sum(map(len, cut.frames))
        if cut_bytes > TRANSCRIPT_BYTES:
            _fail("CUT_BYTES")
        frames = [_logical(w) for w in cut.frames]
        if not frames or frames[-1]["kind"] != "BAR_COMMIT":
            _fail("CUT_BOUNDARY")
        _complete_prefix(frames)
        for frame in frames:
            if any(frame[k] != getattr(binding, k) for k in ("run_id", "session_id", "stack_id")):
                _fail("CUT_IDENTITY")
        cuts[cut.checkpoint_hash] = (cut, frames)
    if (
        restored_cut is not None
        and cuts.get(restored_cut.checkpoint_hash, (None,))[0] != restored_cut
    ):
        _fail("RESTORED_CUT_NOT_ADMITTED")
    messages = [] if restored_cut is None else list(cuts[restored_cut.checkpoint_hash][1])
    ack = -1 if restored_cut is None else restored_cut.last_acknowledged_frame
    seen: dict[str, str] = {}
    payloads: dict[str, bytes] = {}
    active: dict[str, Any] | None = None
    repeated, raw_total = 0, 0
    restored = restored_cut is None
    for index, wire in enumerate(wires):
        envelope = decode_frame(wire)
        if any(envelope[k] != getattr(binding, k) for k in binding.__dataclass_fields__):
            _fail("GENERATION_OR_IDENTITY")
        delivery_id, digest = envelope["delivery_id"], envelope["content_hash"]
        if delivery_id in seen:
            if seen[delivery_id] != digest:
                _fail("CONFLICTING_DELIVERY")
            repeated += 1
            continue
        kind, body = envelope["kind"], envelope["body"]
        if index == 0 and kind != "HELLO" or index > 0 and kind == "HELLO":
            _fail("PHYSICAL_HELLO_ORDER")
        if kind == "HELLO":
            expected_hash = None if restored_cut is None else restored_cut.checkpoint_hash
            if (
                body["checkpoint_hash"] != expected_hash
                or body["inner_schema_hash"] != schema_hash("openpine.worker.protocol.v2")
                or body["delivery_schema_hash"] != raw_hash(proposal_schema_bytes())
            ):
                _fail("HANDSHAKE_SCHEMA_OR_CUT")
        elif kind == "PAYLOAD_BEGIN":
            if active is not None or body["payload_id"] in payloads:
                _fail("PAYLOAD_ALREADY_OPEN")
            if raw_total + body["size_bytes"] > PAYLOAD_BYTES:
                _fail("AGGREGATE_PAYLOAD_BYTES")
            active = {**body, "index": 0, "data": bytearray()}
        elif kind == "PAYLOAD_CHUNK":
            if (
                active is None
                or body["payload_id"] != active["payload_id"]
                or body["index"] != active["index"]
            ):
                _fail("CHUNK_ORDER_OR_IDENTITY")
            try:
                chunk = base64.b64decode(body["data"], validate=True)
            except ValueError as error:
                raise DeliveryProposalError("BASE64") from error
            if (
                not chunk
                or len(chunk) > CHUNK_BYTES
                or base64.b64encode(chunk).decode("ascii") != body["data"]
                or raw_hash(chunk) != body["sha256"]
                or len(active["data"]) + len(chunk) > active["size_bytes"]
            ):
                _fail("CHUNK_BYTES_OR_HASH")
            active["data"].extend(chunk)
            active["index"] += 1
        elif kind == "PAYLOAD_END":
            if (
                active is None
                or body["payload_id"] != active["payload_id"]
                or body["chunks"] != active["index"]
            ):
                _fail("PAYLOAD_END_ORDER")
            data = bytes(active["data"])
            if len(data) != active["size_bytes"] or raw_hash(data) != active["sha256"]:
                _fail("PAYLOAD_INCOMPLETE_OR_HASH")
            payloads[body["payload_id"]] = data
            raw_total += len(data)
            active = None
        elif kind in {"CHECKPOINT", "RESTORE", "ACK"}:
            if body["checkpoint_hash"] not in cuts:
                _fail("CUT_NOT_DURABLE_OWNER_ADMITTED")
            cut, prefix = cuts[body["checkpoint_hash"]]
            if (
                body["committed_sequence"] != len(prefix) - 1
                or body["callback_sequence"] != cut.callback_sequence
                or body["intent_sequence"] != cut.intent_sequence
                or messages[: len(prefix)] != prefix
            ):
                _fail("CUT_CURSOR_OR_PREFIX")
            if kind == "ACK":
                sequence = body["sequence"]
                if not restored or sequence >= len(prefix):
                    _fail("PROVISIONAL_ACK")
                message = prefix[sequence]
                expected_role = "parent" if message["sender_role"] == "worker" else "worker"
                if (
                    body["message_id"] != message["message_id"]
                    or body["message_hash"] != message["content_hash"]
                    or envelope["sender_role"] != expected_role
                    or sequence > ack + 1
                ):
                    _fail("ACK_IDENTITY_ROLE_OR_GAP")
                ack = max(ack, sequence)
            else:
                cut_data = payloads.get(body["payload_id"])
                if (
                    cut_data is None
                    or len(cut_data) != cut.payload_size
                    or raw_hash(cut_data) != cut.payload_sha256
                ):
                    _fail("CUT_PAYLOAD_NOT_ADMITTED")
                if kind == "RESTORE":
                    if restored_cut != cut or restored or messages != prefix:
                        _fail("RESTORE_CONFLICT_OR_AFTER_PROGRESS")
                    restored = True
        elif kind == "MESSAGE":
            if not restored:
                _fail("MESSAGE_BEFORE_RESTORE")
            message = body["message"]
            if (
                message["sequence"] != len(messages)
                or any(
                    message[k] != getattr(binding, k) for k in ("run_id", "session_id", "stack_id")
                )
                or envelope["sender_role"]
                != ("worker" if message["sender_role"] == "worker" else "parent")
                or not verify_content_hash(message, schema_id="openpine.worker.protocol.v2")
            ):
                _fail("LOGICAL_SEQUENCE_IDENTITY_ROLE_OR_HASH")
            messages.append(message)
        seen[delivery_id] = digest
    if active is not None or not restored:
        _fail("INCOMPLETE_PAYLOAD_OR_RESTORE")
    _complete_prefix(messages)
    return DeliveryProjection(len(messages), ack, repeated, tuple(payloads.items()))


def encode_frame(envelope: Mapping[str, Any]) -> bytes:
    """Seal with the existing canonical hash owner, then validate the draft shape."""
    wire = canonical_dumps(seal_content_hash(envelope, schema_id=SCHEMA_ID)).encode("utf-8")
    decode_frame(wire)
    return wire


def payload_frames(
    payload: bytes, *, template: Mapping[str, Any], payload_id: str
) -> Iterator[bytes]:
    """Produce bounded chunks of opaque bytes; existing owners admit their codec."""
    if type(payload) is not bytes or not 0 < len(payload) <= PAYLOAD_BYTES:
        _fail("PAYLOAD_BYTES")
    digest = raw_hash(payload)

    def frame(kind: str, body: dict[str, Any], index: int = -1) -> bytes:
        identity = f"{payload_id}:{digest}:{kind}:{index}".encode("utf-8")
        return encode_frame(
            {**template, "kind": kind, "delivery_id": raw_hash(identity), "body": body}
        )

    yield frame(
        "PAYLOAD_BEGIN",
        {
            "payload_id": payload_id,
            "codec": "openpine.committed-job.v1",
            "size_bytes": len(payload),
            "sha256": digest,
        },
    )
    count = 0
    for offset in range(0, len(payload), CHUNK_BYTES):
        chunk = payload[offset : offset + CHUNK_BYTES]
        yield frame(
            "PAYLOAD_CHUNK",
            {
                "payload_id": payload_id,
                "index": count,
                "sha256": raw_hash(chunk),
                "data": base64.b64encode(chunk).decode("ascii"),
            },
            count,
        )
        count += 1
    yield frame("PAYLOAD_END", {"payload_id": payload_id, "chunks": count})
