"""Unqualified exits have an explicit versioned scope, never a wildcard entry ID."""

import pytest
from test_rc3_contracts import _intent

from openpine_contracts import (
    SchemaValidationError,
    seal_content_hash,
    validate_payload,
    verify_content_hash,
)


def all_exit(**updates):
    return _intent(
        "exit",
        schema_version="2.3.0",
        exit_scope="all_entries",
        order_id="X",
        profit="5",
        **updates,
    )


def test_all_entry_exit_is_sealed_and_validated():
    event = seal_content_hash(all_exit(), schema_id="openpine.intent.v2")
    validate_payload("openpine.intent.v2", event)
    assert verify_content_hash(event, schema_id="openpine.intent.v2")


@pytest.mark.parametrize(
    "fault",
    [
        "old_version",
        "explicit_and_all",
        "missing_scope",
        "unknown_scope",
        "close",
        "unknown_version",
        "entry",
    ],
)
def test_scope_is_unambiguous_and_cannot_change_other_intents(fault):
    value = all_exit()
    if fault == "old_version":
        value["schema_version"] = "2.2.0"
    if fault == "explicit_and_all":
        value["from_entry"] = "A"
    if fault == "missing_scope":
        value.pop("exit_scope")
    if fault == "unknown_scope":
        value["exit_scope"] = "*"
    if fault == "close":
        value["kind"] = "close"
    if fault == "entry":
        value["kind"] = "entry"
        value.update(direction="LONG", qty="1")
    if fault == "unknown_version":
        value["schema_version"] = "2.4.0"
    with pytest.raises(SchemaValidationError):
        validate_payload("openpine.intent.v2", value)


@pytest.mark.parametrize("name", ["A", "*", "A:B"])
def test_existing_explicit_entry_ids_are_not_wildcards(name):
    validate_payload(
        "openpine.intent.v2", _intent("exit", order_id="X", from_entry=name, profit="5")
    )
