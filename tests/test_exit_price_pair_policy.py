"""Explicit fixed-price pair semantics do not reinterpret older replay records."""

from copy import deepcopy

import pytest
from test_rc3_contracts import _intent

from openpine_contracts import (
    SchemaValidationError,
    seal_content_hash,
    validate_payload,
    verify_content_hash,
)


def mixed(scope="named"):
    return _intent(
        "exit",
        schema_version="2.4.0",
        order_id="X",
        price_pair_policy="first_trigger",
        profit="0",
        limit="110",
        **({"from_entry": "A"} if scope == "named" else {"exit_scope": "all_entries"}),
    )


@pytest.mark.parametrize("scope", ["named", "all"])
@pytest.mark.parametrize("leg", ["tp", "sl", "both"])
def test_versioned_policy_roundtrip(scope, leg):
    payload = mixed(scope)
    if leg != "tp":
        payload.update(loss="0", stop="90")
    if leg == "sl":
        payload.pop("profit")
        payload.pop("limit")
    sealed = seal_content_hash(payload, schema_id="openpine.intent.v2")
    validate_payload("openpine.intent.v2", sealed)
    assert verify_content_hash(sealed, schema_id="openpine.intent.v2")


@pytest.mark.parametrize(
    "fault",
    [
        "policy",
        "missing_policy",
        "both_scopes",
        "no_scope",
        "no_pair",
        "null_pair",
        "old_named",
        "old_all",
        "wrong_kind",
    ],
)
def test_invalid_policy_or_scope_is_rejected(fault):
    event = mixed()
    if fault == "policy":
        event["price_pair_policy"] = "absolute_first"
    elif fault == "missing_policy":
        event.pop("price_pair_policy")
    elif fault == "both_scopes":
        event["exit_scope"] = "all_entries"
    elif fault == "no_scope":
        event.pop("from_entry")
    elif fault == "no_pair":
        event.pop("profit")
    elif fault == "null_pair":
        event["profit"] = None
    elif fault == "old_named":
        event["schema_version"] = "2.2.0"
    elif fault == "old_all":
        event.pop("from_entry")
        event.update(schema_version="2.3.0", exit_scope="all_entries")
    else:
        event.update(kind="entry", direction="LONG", qty="1")
    with pytest.raises(SchemaValidationError):
        validate_payload("openpine.intent.v2", event)


@pytest.mark.parametrize("scope", ["named", "all"])
def test_old_mixed_records_remain_valid_and_hash_distinct(scope):
    new = mixed(scope)
    old = deepcopy(new)
    old.pop("price_pair_policy")
    old["schema_version"] = "2.2.0" if scope == "named" else "2.3.0"
    for event in (old, new):
        validate_payload("openpine.intent.v2", event)
    assert (
        seal_content_hash(old, schema_id="openpine.intent.v2")["content_hash"]
        != seal_content_hash(new, schema_id="openpine.intent.v2")["content_hash"]
    )
