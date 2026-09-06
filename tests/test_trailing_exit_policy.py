"""Trailing policy is explicit on wire; older exits keep their exact contract."""

import pytest
from test_rc3_contracts import _intent

from openpine_contracts import (
    SchemaValidationError,
    seal_content_hash,
    validate_payload,
    verify_content_hash,
)


def trail(scope="named", policy="first_trigger"):
    return _intent(
        "exit",
        schema_version="2.5.0",
        order_id="X",
        trail_price="105",
        trail_points="2",
        trail_offset="0",
        price_pair_policy=policy,
        **({"from_entry": "A"} if scope == "named" else {"exit_scope": "all_entries"}),
    )


@pytest.mark.parametrize("scope", ["named", "all"])
@pytest.mark.parametrize("policy", ["absolute_first", "first_trigger"])
@pytest.mark.parametrize("activation", ["price", "points", "both"])
def test_trailing_wire_roundtrip(scope, policy, activation):
    event = trail(scope, policy)
    if activation != "both":
        event.pop("trail_points" if activation == "price" else "trail_price")
    event.update(profit="5", limit="110")  # TP is compatible; a second stop is not.
    sealed = seal_content_hash(event, schema_id="openpine.intent.v2")
    validate_payload("openpine.intent.v2", sealed)
    assert verify_content_hash(sealed, schema_id="openpine.intent.v2")


@pytest.mark.parametrize(
    "fault",
    [
        "offset",
        "null_offset",
        "negative",
        "activation",
        "null_activation",
        "policy",
        "missing_policy",
        "both_scopes",
        "no_scope",
        "fixed_stop",
        "fixed_loss",
        "wrong_kind",
        "old_version",
    ],
)
def test_incomplete_or_ambiguous_trailing_is_rejected(fault):
    event = trail()
    if fault == "offset":
        event.pop("trail_offset")
    elif fault == "null_offset":
        event["trail_offset"] = None
    elif fault == "negative":
        event["trail_offset"] = "-1"
    elif fault == "activation":
        event.pop("trail_price")
        event.pop("trail_points")
    elif fault == "null_activation":
        event["trail_price"] = event["trail_points"] = None
    elif fault == "policy":
        event["price_pair_policy"] = "unknown"
    elif fault == "missing_policy":
        event.pop("price_pair_policy")
    elif fault == "both_scopes":
        event["exit_scope"] = "all_entries"
    elif fault == "no_scope":
        event.pop("from_entry")
    elif fault == "fixed_stop":
        event["stop"] = "95"
    elif fault == "fixed_loss":
        event["loss"] = "0"
    elif fault == "wrong_kind":
        event["kind"] = "close"
    elif fault == "old_version":
        event["schema_version"] = "2.4.0"
    with pytest.raises(SchemaValidationError):
        validate_payload("openpine.intent.v2", event)
