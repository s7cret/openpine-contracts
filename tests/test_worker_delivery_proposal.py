"""Independent draft framing fixtures; opaque payloads do not qualify native restore."""

import json
from dataclasses import asdict, replace

import pytest

import openpine_contracts as contracts
from openpine_contracts.proposals.worker_delivery import (
    CHUNK_BYTES,
    FRAME_BYTES,
    LIMITS,
    PAYLOAD_BYTES,
    SCHEMA_ID,
    TRANSCRIPT_BYTES,
    TRANSCRIPT_FRAMES,
    CutReceipt,
    DeliveryBinding,
    DeliveryProposalError,
    decode_frame,
    encode_frame,
    payload_frames,
    proposal_schema_bytes,
    raw_hash,
    validate_delivery_sequence,
)
from tests.test_rc4_wave1_contracts import HASH_B, _valid_worker_sequence


@pytest.fixture
def fixture():
    logical = _valid_worker_sequence()
    first = logical[0]
    binding = DeliveryBinding(
        "job",
        first["run_id"],
        first["session_id"],
        "worker-2",
        2,
        first["stack_id"],
        first["producer_commit"],
    )
    template = {
        **asdict(binding),
        "schema_id": SCHEMA_ID,
        "schema_version": "1.0.0",
        "producer": "openpine",
        "producer_version": first["producer_version"],
        "created_at_utc_ms": 0,
        "serializer_id": "openpine.canonical.json.v1",
        "content_hash_alg": "sha256",
        "sender_role": "parent",
    }
    # Framing-only bytes. Complete native/Pine owner admission is external.
    payload = b'{"opaque":"owner-admitted-for-framing-fixture"}'
    cut = CutReceipt(
        binding,
        HASH_B,
        raw_hash(payload),
        len(payload),
        2,
        2,
        tuple(contracts.canonical_dumps(m).encode() for m in logical[:10]),
    )
    return binding, template, logical, payload, cut


def envelope(template, kind, body, identity=None, role="parent"):
    return encode_frame(
        {
            **template,
            "kind": kind,
            "body": body,
            "sender_role": role,
            "delivery_id": identity or kind,
        }
    )


def hello(template, checkpoint=None):
    return envelope(
        template,
        "HELLO",
        {
            "capabilities": ["delivery_v1", "committed_job_v1"],
            "inner_schema_hash": contracts.schema_hash("openpine.worker.protocol.v2"),
            "delivery_schema_hash": raw_hash(proposal_schema_bytes()),
            "checkpoint_hash": checkpoint,
            "limits": LIMITS,
        },
        role="worker",
    )


def control(template, kind, cut):
    return envelope(
        template,
        kind,
        {
            "payload_id": "cut",
            "checkpoint_hash": cut.checkpoint_hash,
            "committed_sequence": len(cut.frames) - 1,
            "callback_sequence": cut.callback_sequence,
            "intent_sequence": cut.intent_sequence,
        },
    )


def ack(template, cut, sequence, identity=None):
    message = json.loads(cut.frames[sequence])
    return envelope(
        template,
        "ACK",
        {
            "message_id": message["message_id"],
            "message_hash": message["content_hash"],
            "sequence": sequence,
            "checkpoint_hash": cut.checkpoint_hash,
            "committed_sequence": len(cut.frames) - 1,
            "callback_sequence": cut.callback_sequence,
            "intent_sequence": cut.intent_sequence,
        },
        identity or "ack-" + str(sequence),
        "parent" if message["sender_role"] == "worker" else "worker",
    )


def restored(fixture, *, payload=None, cut=None):
    binding, template, _, original, original_cut = fixture
    payload, cut = original if payload is None else payload, original_cut if cut is None else cut
    return [
        hello(template, cut.checkpoint_hash),
        *payload_frames(payload, template=template, payload_id="cut"),
        control(template, "RESTORE", cut),
    ]


def mutate(wire, **changes):
    value = decode_frame(wire)
    value.update(changes)
    return encode_frame(value)


def run(fixture, wires, cut=None):
    binding, _, _, _, original = fixture
    cut = original if cut is None else cut
    return validate_delivery_sequence(wires, binding, durable_cuts=(cut,), restored_cut=cut)


def test_registered_additive_schema_keeps_v2_bytes_unchanged(fixture):
    assert SCHEMA_ID in contracts.list_schema_ids()
    assert not hasattr(contracts, "validate_delivery_sequence")
    assert contracts.get_schema(SCHEMA_ID)["properties"]["schema_version"] == {"const": "1.0.0"}
    assert contracts.get_schema("openpine.worker.protocol.v2")["properties"]["schema_version"] == {
        "const": "2.3.0"
    }
    logical = fixture[2]
    contracts.validate_worker_protocol_sequence(logical)
    before = [contracts.canonical_dumps(m) for m in logical]
    binding, template = fixture[:2]
    frames = [hello(template)] + [
        envelope(
            template,
            "MESSAGE",
            {"message": m},
            "frame-" + str(m["sequence"]),
            "worker" if m["sender_role"] == "worker" else "parent",
        )
        for m in logical
    ]
    projection = validate_delivery_sequence(frames, binding)
    assert projection.logical_next_sequence == 12 and projection.last_acknowledged_frame == -1
    assert before == [contracts.canonical_dumps(m) for m in logical]


def test_restore_has_no_logical_replay_and_preserves_ack_then_exact_repeats(fixture):
    cut = replace(fixture[4], last_acknowledged_frame=4)
    frames = restored(fixture, cut=cut)
    before = tuple(cut.frames)
    frames += [ack(fixture[1], cut, 5), ack(fixture[1], cut, 5)]
    frames += [frames[-1], frames[-3], frames[0], frames[1]]
    result = run(fixture, frames, cut)
    assert result.logical_next_sequence == 10 and result.last_acknowledged_frame == 5
    assert result.repeated_deliveries == 5 and cut.frames == before
    assert result.payloads == (("cut", fixture[3]),)


@pytest.mark.parametrize("size", [1, CHUNK_BYTES - 1, CHUNK_BYTES, CHUNK_BYTES + 1, PAYLOAD_BYTES])
def test_bounded_payload_literal_reassembly(fixture, size):
    data = b"p" * size
    binding, template = fixture[:2]
    frames = [hello(template), *payload_frames(data, template=template, payload_id="literal")]
    assert all(len(w) <= FRAME_BYTES for w in frames)
    result = validate_delivery_sequence(frames, binding)
    assert result.payloads == (("literal", data),) and result.logical_next_sequence == 0


@pytest.mark.parametrize(
    "damage",
    [
        "stale",
        "future",
        "job",
        "worker",
        "schema-hash",
        "capability",
        "limit",
        "unknown-kind",
        "extra",
        "float",
        "hash",
    ],
)
def test_handshake_generation_identity_and_shape_refusal(fixture, damage):
    value = decode_frame(restored(fixture)[0])
    if damage in {"stale", "future"}:
        value["worker_generation"] = 1 if damage == "stale" else 3
    elif damage in {"job", "worker"}:
        value[damage + "_id"] = "foreign"
    elif damage == "schema-hash":
        value["body"]["inner_schema_hash"] = HASH_B
    elif damage == "capability":
        value["body"]["capabilities"] = ["closed_bar"]
    elif damage == "limit":
        value["body"]["limits"]["payload_bytes"] += 1
    elif damage == "unknown-kind":
        value["kind"] = "INVENTED"
    elif damage == "extra":
        value["body"]["extra"] = True
    elif damage == "float":
        value["worker_generation"] = 2.0
    else:
        value["content_hash"] = HASH_B
    if damage not in {"float", "hash"}:
        value = contracts.seal_content_hash(value, schema_id=SCHEMA_ID)
    # Deliberately bypass producer's guard for malicious incoming bytes.
    wire = json.dumps(value).encode()
    with pytest.raises(DeliveryProposalError):
        run(fixture, [wire])


@pytest.mark.parametrize(
    "damage",
    [
        "index",
        "payload-id",
        "chunk-hash",
        "base64",
        "raw-size",
        "size",
        "whole-hash",
        "count",
        "eof",
        "duplicate-conflict",
        "restore-before-payload",
    ],
)
def test_chunk_and_cut_refusal_before_any_external_mutation(fixture, damage):
    frames = restored(fixture)
    index = 2
    value = decode_frame(frames[index])
    if damage == "index":
        value["body"]["index"] = 1
    elif damage == "payload-id":
        value["body"]["payload_id"] = "other"
    elif damage == "chunk-hash":
        value["body"]["sha256"] = HASH_B
    elif damage == "base64":
        value["body"]["data"] = "AB=="  # valid alphabet, noncanonical pad bits
    elif damage == "raw-size":
        import base64

        value["body"]["data"] = base64.b64encode(b"x" * (CHUNK_BYTES + 1)).decode()
    elif damage in {"size", "whole-hash"}:
        index = 1
        value = decode_frame(frames[index])
        if damage == "size":
            value["body"]["size_bytes"] += 1
        else:
            value["body"]["sha256"] = HASH_B
    elif damage == "count":
        index = 3
        value = decode_frame(frames[index])
        value["body"]["chunks"] = 2
    elif damage == "eof":
        frames = frames[:3]
    elif damage == "duplicate-conflict":
        conflict = decode_frame(frames[2])
        conflict["body"]["sha256"] = HASH_B
        frames.insert(
            3,
            contracts.canonical_dumps(
                contracts.seal_content_hash(conflict, schema_id=SCHEMA_ID)
            ).encode(),
        )
    else:
        frames = [frames[0], frames[-1]]
    if damage not in {"eof", "duplicate-conflict", "restore-before-payload"}:
        frames[index] = contracts.canonical_dumps(
            contracts.seal_content_hash(value, schema_id=SCHEMA_ID)
        ).encode()
    before = (fixture[4], tuple(fixture[4].frames))
    with pytest.raises(DeliveryProposalError):
        run(fixture, frames)
    assert before == (fixture[4], tuple(fixture[4].frames))


@pytest.mark.parametrize(
    "damage",
    [
        "gap",
        "id",
        "hash",
        "provisional",
        "role",
        "checkpoint",
        "callback",
        "intent",
        "commit",
        "no-durable-cut",
    ],
)
def test_ack_requires_contiguous_exact_durable_cut(fixture, damage):
    cut = fixture[4]
    value = decode_frame(ack(fixture[1], cut, 0))
    if damage == "gap":
        value = decode_frame(ack(fixture[1], cut, 1))
    elif damage in {"id", "hash"}:
        value["body"]["message_" + damage] = "other" if damage == "id" else HASH_B
    elif damage == "provisional":
        value["body"]["sequence"] = 10
    elif damage == "role":
        value["sender_role"] = "worker"
    elif damage == "checkpoint":
        value["body"]["checkpoint_hash"] = "sha256:" + "a" * 64
    elif damage in {"callback", "intent"}:
        value["body"][damage + "_sequence"] += 1
    elif damage == "commit":
        value["body"]["committed_sequence"] += 1
    frames = restored(fixture) + [encode_frame(value)]
    with pytest.raises(DeliveryProposalError):
        if damage == "no-durable-cut":
            validate_delivery_sequence(frames, fixture[0])
        else:
            run(fixture, frames)


@pytest.mark.parametrize(
    "damage",
    [
        "duplicate-json",
        "nan",
        "utf16",
        "depth",
        "frame-size",
        "frame-count",
        "transcript-size",
        "payload-zero",
        "payload-oversize",
    ],
)
def test_parser_and_transport_budget_refusal(fixture, damage):
    first = hello(fixture[1])
    if damage == "duplicate-json":
        wire = b'{"kind":"HELLO","kind":"ACK"}'
    elif damage == "nan":
        wire = b'{"value":NaN}'
    elif damage == "utf16":
        wire = first.decode().encode("utf-16")
    elif damage == "depth":
        wire = b"[" * 65 + b"0" + b"]" * 65
    elif damage == "frame-size":
        wire = b" " * (FRAME_BYTES + 1)
    else:
        wire = first
    with pytest.raises(DeliveryProposalError):
        if damage == "frame-count":
            validate_delivery_sequence([first] * (TRANSCRIPT_FRAMES + 1), fixture[0])
        elif damage == "transcript-size":
            validate_delivery_sequence(
                [b" " * FRAME_BYTES] * (TRANSCRIPT_BYTES // FRAME_BYTES + 1), fixture[0]
            )
        elif damage in {"payload-zero", "payload-oversize"}:
            list(
                payload_frames(
                    b"" if damage == "payload-zero" else b"p" * (PAYLOAD_BYTES + 1),
                    template=fixture[1],
                    payload_id="too-large",
                )
            )
        else:
            decode_frame(wire)


def test_restore_repeat_after_logical_progress_preserves_cursor(fixture):
    frames = restored(fixture)
    control_frame = frames[-1]
    for message in fixture[2][10:]:
        frames.append(
            envelope(
                fixture[1], "MESSAGE", {"message": message}, "next-" + str(message["sequence"])
            )
        )
    frames.append(control_frame)
    result = run(fixture, frames)
    assert result.logical_next_sequence == 12 and result.repeated_deliveries == 1
    frames[-1] = mutate(control_frame, delivery_id="different-restore")
    with pytest.raises(DeliveryProposalError):
        run(fixture, frames)


def test_foreign_durable_owner_binding_rejects(fixture):
    cut = replace(fixture[4], binding=replace(fixture[0], job_id="other"))
    with pytest.raises(DeliveryProposalError):
        run(fixture, restored(fixture), cut)


@pytest.mark.parametrize("damage", ["sequence", "run", "role", "hash", "causation", "nested"])
def test_unchanged_inner_contract_checks_remain_active(fixture, damage):
    binding, template, logical = fixture[:3]
    messages = json.loads(json.dumps(logical))
    message = messages[4]
    if damage == "sequence":
        message["sequence"] += 1
    elif damage == "run":
        message["run_id"] = "foreign"
    elif damage == "role":
        message["sender_role"] = "parent"
    elif damage == "hash":
        message["content_hash"] = HASH_B
    elif damage == "causation":
        message["causation_id"] = "foreign-message"
    else:
        message["body"]["intents"][0]["producer_commit"] = "a" * 40
    if damage != "hash":
        messages[4] = contracts.seal_content_hash(message, schema_id="openpine.worker.protocol.v2")
    frames = [hello(template)] + [
        envelope(
            template,
            "MESSAGE",
            {"message": m},
            "logical-" + str(index),
            "worker" if m["sender_role"] == "worker" else "parent",
        )
        for index, m in enumerate(messages)
    ]
    with pytest.raises((DeliveryProposalError, contracts.WorkerProtocolSemanticError)):
        validate_delivery_sequence(frames, binding)
    assert logical == fixture[2]


@pytest.mark.parametrize(
    "damage",
    ["bool-ack", "ack-past-cut", "negative-callback", "foreign-generation", "mutable-frames"],
)
def test_malformed_owner_admitted_view_refuses(fixture, damage):
    cut = fixture[4]
    if damage == "bool-ack":
        cut = replace(cut, last_acknowledged_frame=True)
    elif damage == "ack-past-cut":
        cut = replace(cut, last_acknowledged_frame=len(cut.frames))
    elif damage == "negative-callback":
        cut = replace(cut, callback_sequence=-1)
    elif damage == "foreign-generation":
        cut = replace(cut, binding=replace(cut.binding, worker_generation=1))
    else:
        cut = replace(cut, frames=list(cut.frames))
    with pytest.raises(DeliveryProposalError):
        run(fixture, restored(fixture), cut)


def test_aggregate_payload_budget_and_distinct_hello_refuse(fixture):
    binding, template = fixture[:2]
    frames = [hello(template), *payload_frames(b"p", template=template, payload_id="first")]
    large = envelope(
        template,
        "PAYLOAD_BEGIN",
        {
            "payload_id": "second",
            "codec": "openpine.committed-job.v1",
            "size_bytes": PAYLOAD_BYTES,
            "sha256": HASH_B,
        },
        identity="second-begin",
    )
    with pytest.raises(DeliveryProposalError, match="AGGREGATE_PAYLOAD_BYTES"):
        validate_delivery_sequence([*frames, large], binding)
    with pytest.raises(DeliveryProposalError, match="PHYSICAL_HELLO_ORDER"):
        validate_delivery_sequence(
            [*frames, mutate(frames[0], delivery_id="second-hello")], binding
        )
