from __future__ import annotations

from decimal import Decimal

import pytest

import openpine_contracts.hashing as hashing
import openpine_contracts.registry as registry
import openpine_contracts.validate as validation
import openpine_contracts.worker_protocol as worker
from openpine_contracts import (
    AdmitPolicy,
    AdmitRequest,
    ArtifactEnvelope,
    CanonicalizationError,
    ContractError,
    Money,
    MoneyError,
    SchemaNotFoundError,
    SchemaValidatorUnavailableError,
    evaluate_admit,
    schema_hash,
)
from openpine_contracts.errors import WorkerProtocolSemanticError
from openpine_contracts.money import decimal_string, unsafe_decimal_from_float
from tests.test_rc4_wave1_contracts import (
    HASH_D,
    WORKER_BODIES,
    _valid_worker_sequence,
    _worker_message,
)


def _admit_request(**overrides: object) -> AdmitRequest:
    values: dict[str, object] = {
        "schema_id": "openpine.run.v2",
        "schema_major": 2,
        "schema_minor": 1,
        "required_capabilities": (),
        "stack_id": "stack",
        "artifact_hash": "artifact",
    }
    values.update(overrides)
    return AdmitRequest(**values)  # type: ignore[arg-type]


def _admit_policy(**overrides: object) -> AdmitPolicy:
    values: dict[str, object] = {
        "supported_schema_id": "openpine.run.v2",
        "min_major": 2,
        "max_major": 2,
        "min_minor": 1,
        "max_minor": 2,
        "capabilities": frozenset(),
        "expected_stack_id": "stack",
        "expected_artifact_hash": "artifact",
    }
    values.update(overrides)
    return AdmitPolicy(**values)  # type: ignore[arg-type]


def test_compatibility_remaining_denial_branches() -> None:
    assert evaluate_admit(_admit_request(schema_id="other.v2"), _admit_policy()).code == (
        "SCHEMA_ID_MISMATCH"
    )
    assert evaluate_admit(_admit_request(schema_minor=0), _admit_policy()).code == (
        "SCHEMA_MINOR_TOO_OLD"
    )


def test_contract_error_and_envelope_remaining_branches() -> None:
    error = ContractError("bad", details={"field": "x"})
    assert error.to_dict() == {
        "code": "CONTRACT_ERROR",
        "message": "bad",
        "details": {"field": "x"},
    }
    with pytest.raises(ContractError, match="incomplete"):
        ArtifactEnvelope.from_mapping({})
    envelope = ArtifactEnvelope(
        schema_id="openpine.event.v1",
        schema_version="1.0.0",
        producer="tests",
        producer_version="1.0.0",
        producer_commit="a" * 40,
        stack_id="sha256:" + "b" * 64,
        created_at_utc_ms=0,
        content_hash="sha256:" + "c" * 64,
    )
    assert envelope.to_dict()["schema_id"] == "openpine.event.v1"


def test_hashing_remaining_error_branches(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(hashing, "_is_neg_zero_int", lambda value: True)
    assert hashing._normalize(0) == 0

    def broken_dumps(*_args: object, **_kwargs: object) -> str:
        raise TypeError("broken")

    monkeypatch.setattr(hashing.json, "dumps", broken_dumps)
    with pytest.raises(CanonicalizationError, match="broken"):
        hashing.canonical_dumps({"ok": True})
    monkeypatch.undo()

    with pytest.raises(CanonicalizationError, match="schema_id is required"):
        hashing.schema_major_from_id("")
    with pytest.raises(CanonicalizationError, match="must end"):
        hashing.schema_major_from_id("openpine.event")
    with pytest.raises(CanonicalizationError, match="unsupported hash alg"):
        hashing.content_hash({}, alg="md5", schema_major=1)
    with pytest.raises(CanonicalizationError, match="schema_id or schema_major"):
        hashing.content_hash({})
    with pytest.raises(CanonicalizationError, match="schema_id must be a string"):
        hashing.seal_content_hash({"schema_id": 1})
    assert not hashing.verify_content_hash(
        {"content_hash": "sha256:" + "a" * 64, "x": 1.0}, schema_id="x.v1"
    )


def test_money_remaining_error_and_mapping_branches() -> None:
    with pytest.raises(MoneyError, match="empty"):
        decimal_string(" ")
    with pytest.raises(MoneyError, match="unsupported decimal type"):
        decimal_string(None)  # type: ignore[arg-type]
    with pytest.raises(MoneyError, match="invalid decimal"):
        decimal_string("abc")
    with pytest.raises(MoneyError, match="float only"):
        unsafe_decimal_from_float(1)  # type: ignore[arg-type]
    with pytest.raises(MoneyError, match="finite"):
        unsafe_decimal_from_float(float("inf"))
    with pytest.raises(MoneyError, match="scale"):
        Money("1", "USD", -1)
    with pytest.raises(MoneyError, match="amount"):
        Money.from_mapping({"currency": "USD"})
    with pytest.raises(MoneyError, match="currency"):
        Money.from_mapping({"amount": "1"})
    with pytest.raises(MoneyError, match="scale"):
        Money.from_mapping({"amount": Decimal("1"), "currency": "USD", "scale": "2"})
    assert Money.from_mapping({"amount": 1, "currency": "USD", "scale": 2}).to_dict()["scale"] == 2


def test_registry_remaining_resource_and_algorithm_branches(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class MissingResource:
        def is_file(self) -> bool:
            return False

    monkeypatch.setattr(registry, "_schema_path", lambda _schema_id: MissingResource())
    with pytest.raises(SchemaNotFoundError, match="resource missing"):
        registry.schema_bytes("openpine.event.v1")
    monkeypatch.undo()

    monkeypatch.setattr(registry, "schema_bytes", lambda _schema_id: b"[]")
    registry.get_schema.cache_clear()
    with pytest.raises(SchemaNotFoundError, match="not an object"):
        registry.get_schema("openpine.event.v1")
    registry.get_schema.cache_clear()
    monkeypatch.undo()

    with pytest.raises(SchemaNotFoundError, match="unsupported hash alg"):
        schema_hash("openpine.event.v1", alg="md5")


def test_validation_remaining_unavailable_and_early_return_branches(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    validation._packaged_registry.cache_clear()
    monkeypatch.setattr(validation, "SchemaRegistry", None)
    with pytest.raises(SchemaValidatorUnavailableError, match="reference resolution"):
        validation._packaged_registry()
    validation._packaged_registry.cache_clear()
    monkeypatch.undo()

    assert validation._find_float(["ok", 1.5]) == (1,)
    validation._validate_intent_semantics(
        {
            "source_span": {
                "known": True,
                "start_offset": 0,
                "end_offset": 1,
                "start_line": None,
                "start_col": None,
                "end_line": None,
                "end_col": None,
            }
        }
    )
    validation._validate_trial_identity_semantics(
        {
            "fold": {
                "train_start_utc_ms": None,
                "train_end_utc_ms": 1,
                "test_start_utc_ms": 2,
                "test_end_utc_ms": 3,
            }
        }
    )


def test_worker_private_helper_remaining_branches() -> None:
    with pytest.raises(WorkerProtocolSemanticError, match="nested content hash"):
        worker._verify_nested_hashes("INIT_RUN", {}, 0)
    assert worker._semver_from_wheel_version("5.0.0") == "5.0.0"
    assert worker._semver_from_wheel_version("5.0.0rcx") == "5.0.0rcx"
    with pytest.raises(WorkerProtocolSemanticError, match="sequence is empty"):
        worker.validate_worker_protocol_sequence([])


def _bypass_worker_contracts(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(worker, "validate_payload", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(worker, "verify_content_hash", lambda *_args, **_kwargs: True)


def test_worker_first_kind_and_body_run_branches(monkeypatch: pytest.MonkeyPatch) -> None:
    _bypass_worker_contracts(monkeypatch)
    with pytest.raises(WorkerProtocolSemanticError, match="begin with HELLO"):
        worker.validate_worker_protocol_sequence(
            [_worker_message("LOAD_ARTIFACT", 0, body=WORKER_BODIES["LOAD_ARTIFACT"])]
        )

    messages = [
        _worker_message("HELLO", 0),
        _worker_message(
            "LOAD_ARTIFACT",
            1,
            causation_id="correlation-1",
            body={**WORKER_BODIES["LOAD_ARTIFACT"], "run_id": "other"},
        ),
    ]
    with pytest.raises(WorkerProtocolSemanticError, match="body run_id"):
        worker.validate_worker_protocol_sequence(messages)


def test_worker_nested_identity_and_bar_hash_branches() -> None:
    messages = _valid_worker_sequence()
    init_body = messages[2]["body"]
    assert isinstance(init_body, dict)
    init_body["execution_context_hash"] = HASH_D
    messages[2] = hashing.seal_content_hash(messages[2], schema_id="openpine.worker.protocol.v2")
    with pytest.raises(WorkerProtocolSemanticError, match="execution_context_hash"):
        worker.validate_worker_protocol_sequence(messages)

    messages = _valid_worker_sequence()
    bar_body = messages[3]["body"]
    assert isinstance(bar_body, dict)
    bar_body["bar_hash"] = HASH_D
    messages[3] = hashing.seal_content_hash(messages[3], schema_id="openpine.worker.protocol.v2")
    with pytest.raises(WorkerProtocolSemanticError, match="bar_hash"):
        worker.validate_worker_protocol_sequence(messages)

    messages = _valid_worker_sequence()
    bar_body = messages[3]["body"]
    assert isinstance(bar_body, dict)
    bar = bar_body["bar"]
    assert isinstance(bar, dict)
    bar["series_id"] = "other-series"
    bar_body["bar"] = hashing.seal_content_hash(bar, schema_id="openpine.marketdata.bar.v2")
    messages[3] = hashing.seal_content_hash(messages[3], schema_id="openpine.worker.protocol.v2")
    with pytest.raises(WorkerProtocolSemanticError, match="canonical bar differs"):
        worker.validate_worker_protocol_sequence(messages)


def test_worker_nonmapping_intent_and_recalc_edge_branches(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _bypass_worker_contracts(monkeypatch)
    monkeypatch.setattr(worker, "_verify_nested_hashes", lambda *_args, **_kwargs: None)
    messages = _valid_worker_sequence()
    intent_body = messages[4]["body"]
    assert isinstance(intent_body, dict)
    intent_body["intents"] = [None]
    worker.validate_worker_protocol_sequence(messages)

    allowed = dict(worker._ALLOWED_AFTER)
    allowed["INIT_RUN"] = frozenset({"RECALC_REQUEST"})
    monkeypatch.setattr(worker, "_ALLOWED_AFTER", allowed)
    messages = _valid_worker_sequence()[:3]
    messages.append(
        _worker_message(
            "RECALC_REQUEST",
            3,
            causation_id="correlation-1",
            body=WORKER_BODIES["RECALC_REQUEST"],
        )
    )
    with pytest.raises(WorkerProtocolSemanticError, match="no active bar"):
        worker.validate_worker_protocol_sequence(messages)

    allowed["INIT_RUN"] = frozenset({"BAR_BEGIN", "RECALC_REQUEST"})
    allowed["BAR_BEGIN"] = frozenset({"RECALC_REQUEST"})
    monkeypatch.setattr(worker, "_ALLOWED_AFTER", allowed)
    messages = _valid_worker_sequence()[:4]
    bar_body = messages[3]["body"]
    assert isinstance(bar_body, dict)
    bar_body["recalc_iteration"] = "bad"
    projection = bar_body["broker_projection"]
    assert isinstance(projection, dict)
    projection["recalc_iteration"] = "bad"
    messages.append(
        _worker_message(
            "RECALC_REQUEST",
            4,
            causation_id="correlation-1",
            body=WORKER_BODIES["RECALC_REQUEST"],
        )
    )
    with pytest.raises(WorkerProtocolSemanticError, match="not an integer"):
        worker.validate_worker_protocol_sequence(messages)

    messages = _valid_worker_sequence()[:4]
    messages.append(
        _worker_message(
            "RECALC_REQUEST",
            4,
            causation_id="correlation-1",
            body={**WORKER_BODIES["RECALC_REQUEST"], "recalc_iteration": 4},
        )
    )
    with pytest.raises(WorkerProtocolSemanticError, match="does not advance"):
        worker.validate_worker_protocol_sequence(messages)


def test_worker_restore_mismatch_branch() -> None:
    messages = _valid_worker_sequence()[:11]
    restore_body = dict(WORKER_BODIES["RESTORE"], checkpoint_hash=HASH_D, committed_sequence=9)
    messages.append(
        _worker_message(
            "RESTORE",
            11,
            causation_id="correlation-1",
            body=restore_body,
        )
    )
    with pytest.raises(WorkerProtocolSemanticError, match="differs from its session checkpoint"):
        worker.validate_worker_protocol_sequence(messages)
