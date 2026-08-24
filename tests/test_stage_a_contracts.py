from __future__ import annotations

from copy import deepcopy

import pytest
from test_rc4_wave1_contracts import (
    HASH_A,
    HASH_B,
    WORKER_BODIES,
    _checkpoint_proof,
    _execution_context,
    _valid_worker_sequence,
    _worker_message,
)

import openpine_contracts as contracts
from openpine_contracts import SchemaValidationError, get_schema, validate_payload


def _reseal(message: dict[str, object]) -> dict[str, object]:
    return contracts.seal_content_hash(message, schema_id="openpine.worker.protocol.v2")


def test_worker_protocol_v2_2_requires_message_identity_and_sender_role() -> None:
    schema = get_schema("openpine.worker.protocol.v2")
    assert schema["properties"]["schema_version"] == {"const": "2.2.0"}
    assert {"message_id", "sender_role"} <= set(schema["required"])
    assert schema["properties"]["sender_role"] == {"enum": ["parent", "worker", "engine"]}


def test_execution_context_uses_closed_versioned_policy_and_registry_contracts() -> None:
    schema = get_schema("openpine.execution_context.v1")
    assert {
        "policy_registry_version",
        "schema_registry_version",
        "capability_registry_version",
    } <= set(schema["required"])

    for field in ("score_policy", "end_policy"):
        payload = _execution_context()
        payload[field] = "invented-policy"
        with pytest.raises(SchemaValidationError):
            validate_payload("openpine.execution_context.v1", payload)


def test_aggregate_batch_hashes_are_recomputed_from_canonical_arrays() -> None:
    messages = _valid_worker_sequence()
    body = messages[4]["body"]
    assert isinstance(body, dict)
    body["intent_batch_hash"] = HASH_B
    messages[4] = _reseal(messages[4])

    with pytest.raises(contracts.WorkerProtocolSemanticError) as caught:
        contracts.validate_worker_protocol_sequence(messages)
    assert caught.value.details["reason"] == "AGGREGATE_BATCH_HASH_MISMATCH"


def test_aggregate_batch_hash_uses_ordered_item_content_identity() -> None:
    messages = _valid_worker_sequence()
    body = messages[4]["body"]
    assert isinstance(body, dict)
    items = body["intents"]
    assert isinstance(items, list)
    same_content = deepcopy(items)
    same_content[0]["created_at_utc_ms"] = 123456
    assert contracts.verify_content_hash(same_content[0], schema_id="openpine.intent.v2")

    assert contracts.aggregate_batch_hash(
        items,
        batch_kind="INTENT_BATCH",
        item_schema_id="openpine.intent.v2",
    ) == contracts.aggregate_batch_hash(
        same_content,
        batch_kind="INTENT_BATCH",
        item_schema_id="openpine.intent.v2",
    )


def test_aggregate_batch_hash_rejects_unverified_items() -> None:
    messages = _valid_worker_sequence()
    body = messages[4]["body"]
    assert isinstance(body, dict)
    items = deepcopy(body["intents"])
    assert isinstance(items, list)
    items[0]["command_id"] = "tampered-without-reseal"

    with pytest.raises(ValueError, match="not a verified"):
        contracts.aggregate_batch_hash(
            items,
            batch_kind="INTENT_BATCH",
            item_schema_id="openpine.intent.v2",
        )


def test_message_id_and_sender_role_are_semantically_enforced() -> None:
    messages = _valid_worker_sequence()
    messages[4]["message_id"] = messages[3]["message_id"]
    messages[4] = _reseal(messages[4])
    with pytest.raises(contracts.WorkerProtocolSemanticError) as caught:
        contracts.validate_worker_protocol_sequence(messages)
    assert caught.value.details["reason"] == "MESSAGE_ID_INVALID"

    messages = _valid_worker_sequence()
    messages[4]["sender_role"] = "parent"
    messages[4] = _reseal(messages[4])
    with pytest.raises(contracts.WorkerProtocolSemanticError) as caught:
        contracts.validate_worker_protocol_sequence(messages)
    assert caught.value.details["reason"] == "SENDER_ROLE_MISMATCH"


def test_causation_identifies_immediate_predecessor_message() -> None:
    messages = _valid_worker_sequence()
    messages[4]["causation_id"] = messages[2]["message_id"]
    messages[4] = _reseal(messages[4])

    with pytest.raises(contracts.WorkerProtocolSemanticError) as caught:
        contracts.validate_worker_protocol_sequence(messages)
    assert caught.value.details["reason"] == "CAUSATION_ID_MISMATCH"


def test_recalc_result_binds_specific_preceding_intent_batch() -> None:
    messages = _valid_worker_sequence()
    body = messages[7]["body"]
    assert isinstance(body, dict)
    body["intent_batch_message_id"] = messages[3]["message_id"]
    messages[7] = _reseal(messages[7])

    with pytest.raises(contracts.WorkerProtocolSemanticError) as caught:
        contracts.validate_worker_protocol_sequence(messages)
    assert caught.value.details["reason"] == "RECALC_INTENT_BINDING_MISMATCH"


def test_commit_and_finalize_bind_sealed_artifacts_and_last_commit() -> None:
    messages = _valid_worker_sequence()
    commit_body = messages[9]["body"]
    assert isinstance(commit_body, dict)
    state_ref = commit_body["state_ref"]
    assert isinstance(state_ref, dict)
    state_ref["artifact_hash"] = HASH_B
    messages[9] = _reseal(messages[9])

    with pytest.raises(contracts.WorkerProtocolSemanticError) as caught:
        contracts.validate_worker_protocol_sequence(messages)
    assert caught.value.details["reason"] == "BAR_COMMIT_ARTIFACT_MISMATCH"

    messages = _valid_worker_sequence()
    final_body = messages[11]["body"]
    assert isinstance(final_body, dict)
    final_body["final_state_hash"] = HASH_B
    messages[11] = _reseal(messages[11])
    with pytest.raises(contracts.WorkerProtocolSemanticError) as caught:
        contracts.validate_worker_protocol_sequence(messages)
    assert caught.value.details["reason"] == "FINALIZE_COMMIT_MISMATCH"


def test_checkpoint_proof_is_a_registered_standalone_contract() -> None:
    assert "openpine.checkpoint.proof.v1" in contracts.list_schema_ids(include_aliases=False)
    proof = _checkpoint_proof()
    validate_payload("openpine.checkpoint.proof.v1", proof)


def test_checkpoint_proof_seal_is_verified() -> None:
    messages = _valid_worker_sequence()
    body = messages[10]["body"]
    assert isinstance(body, dict)
    proof = body["checkpoint_ref"]
    assert isinstance(proof, dict)
    payload_ref = proof["payload_ref"]
    assert isinstance(payload_ref, dict)
    payload_ref["size_bytes"] = 8193
    messages[10] = _reseal(messages[10])

    with pytest.raises(contracts.WorkerProtocolSemanticError) as caught:
        contracts.validate_worker_protocol_sequence(messages)
    assert caught.value.details["reason"] == "CHECKPOINT_PROOF_CONTENT_HASH_MISMATCH"


def test_checkpoint_proof_identity_must_match_last_commit() -> None:
    messages = _valid_worker_sequence()
    body = messages[10]["body"]
    assert isinstance(body, dict)
    body["checkpoint_ref"] = _checkpoint_proof(checkpoint_id="other-checkpoint")
    messages[10] = _reseal(messages[10])

    with pytest.raises(contracts.WorkerProtocolSemanticError) as caught:
        contracts.validate_worker_protocol_sequence(messages)
    assert caught.value.details["reason"] == "CHECKPOINT_PROOF_MISMATCH"


def test_session_checkpoint_restore_succeeds_and_rejects_external_override() -> None:
    messages = _valid_worker_sequence()[:11]
    messages.append(
        _worker_message(
            "RESTORE",
            11,
            body=deepcopy(WORKER_BODIES["RESTORE"]),
        )
    )
    messages.append(
        _worker_message(
            "FINALIZE",
            12,
            body={
                "run_id": "run-1",
                "final_sequence": 11,
                "final_state_hash": HASH_A,
                "broker_projection_hash": HASH_B,
                "last_commit_message_id": "msg-9",
                "last_committed_sequence": 9,
            },
        )
    )
    contracts.validate_worker_protocol_sequence(messages)

    messages = _valid_worker_sequence()[:11]
    restore_body = deepcopy(WORKER_BODIES["RESTORE"])
    restore_body["external_checkpoint_proof"] = _checkpoint_proof()
    messages.append(_worker_message("RESTORE", 11, body=restore_body))
    with pytest.raises(contracts.WorkerProtocolSemanticError) as caught:
        contracts.validate_worker_protocol_sequence(messages)
    assert caught.value.details["reason"] == "UNEXPECTED_EXTERNAL_CHECKPOINT_PROOF"


def test_external_checkpoint_proof_must_match_restore_request() -> None:
    messages = _valid_worker_sequence()[:3]
    proof = _checkpoint_proof(
        checkpoint_id="proof-checkpoint",
        checkpoint_hash=HASH_A,
        committed_message_id="external-commit",
    )
    messages.append(
        _worker_message(
            "RESTORE",
            3,
            body={
                "run_id": "run-1",
                "checkpoint_id": "requested-checkpoint",
                "checkpoint_hash": HASH_A,
                "committed_sequence": 9,
                "external_checkpoint_proof": proof,
            },
        )
    )
    with pytest.raises(contracts.WorkerProtocolSemanticError) as caught:
        contracts.validate_worker_protocol_sequence(messages)
    assert caught.value.details["reason"] == "RESTORE_CHECKPOINT_MISMATCH"


def test_bidirectional_messages_keep_distinct_admitted_producers() -> None:
    messages = _valid_worker_sequence()
    assert [(message["sender_role"], message["producer"]) for message in messages[:6]] == [
        ("worker", "openpine"),
        ("parent", "openpine"),
        ("parent", "openpine"),
        ("parent", "openpine"),
        ("worker", "pinelib"),
        ("engine", "backtest_engine"),
    ]
    contracts.validate_worker_protocol_sequence(messages)


def test_schema_valid_external_checkpoint_proof_allows_restore() -> None:
    messages = _valid_worker_sequence()[:3]
    proof = _checkpoint_proof(
        checkpoint_id="external-checkpoint",
        checkpoint_hash=HASH_A,
        committed_sequence=9,
        committed_message_id="external-commit-message",
        state_hash=HASH_A,
        broker_projection_hash=HASH_B,
    )
    messages.append(
        _worker_message(
            "RESTORE",
            3,
            body={
                "run_id": "run-1",
                "checkpoint_id": "external-checkpoint",
                "checkpoint_hash": HASH_A,
                "committed_sequence": 9,
                "external_checkpoint_proof": proof,
            },
        )
    )
    messages.append(
        _worker_message(
            "FINALIZE",
            4,
            body={
                "run_id": "run-1",
                "final_sequence": 3,
                "final_state_hash": HASH_A,
                "broker_projection_hash": HASH_B,
                "last_commit_message_id": "external-commit-message",
                "last_committed_sequence": 9,
            },
        )
    )

    contracts.validate_worker_protocol_sequence(messages)


def test_unknown_restore_requires_schema_valid_external_checkpoint_proof() -> None:
    messages = _valid_worker_sequence()[:3]
    restore = deepcopy(messages[-1])
    restore.update(
        {
            "message_id": "msg-restore-external",
            "sequence": 3,
            "causation_id": messages[-1]["message_id"],
            "sender_role": "parent",
            "kind": "RESTORE",
            "body": {
                "run_id": "run-1",
                "checkpoint_id": "unknown-checkpoint",
                "checkpoint_hash": HASH_A,
                "committed_sequence": 9,
            },
        }
    )
    messages.append(_reseal(restore))
    final = deepcopy(messages[-1])
    final.update(
        {
            "message_id": "msg-final-external",
            "sequence": 4,
            "causation_id": "msg-restore-external",
            "sender_role": "parent",
            "kind": "FINALIZE",
            "body": {
                "run_id": "run-1",
                "final_sequence": 3,
                "final_state_hash": HASH_A,
                "broker_projection_hash": HASH_B,
                "last_commit_message_id": "external:unknown-checkpoint",
                "last_committed_sequence": 9,
            },
        }
    )
    messages.append(_reseal(final))

    with pytest.raises(contracts.WorkerProtocolSemanticError) as caught:
        contracts.validate_worker_protocol_sequence(messages)
    assert caught.value.details["reason"] == "EXTERNAL_CHECKPOINT_PROOF_REQUIRED"
