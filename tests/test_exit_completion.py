"""Versioned composite exits and per-leg messages, preserving all older readers."""

import pytest
from test_rc3_contracts import _intent

from openpine_contracts import (
    SchemaValidationError,
    seal_content_hash,
    validate_payload,
    verify_content_hash,
)


def event(scope="named", **kwargs):
    return _intent(
        "exit",
        schema_version="2.6.0",
        order_id="X",
        price_pair_policy="first_trigger",
        **({"from_entry": "A"} if scope == "named" else {"exit_scope": "all_entries"}),
        **kwargs,
    )


@pytest.mark.parametrize("scope", ["named", "all"])
@pytest.mark.parametrize("policy", ["absolute_first", "first_trigger"])
@pytest.mark.parametrize(
    "prices",
    [
        {"stop": "95", "trail_price": "105", "trail_offset": "2"},
        {
            "profit": "10",
            "limit": "110",
            "loss": "5",
            "stop": "95",
            "trail_points": "5",
            "trail_offset": "0",
        },
        {"limit": "110", "comment_profit": "", "alert_profit": "exact"},
        {"stop": "95", "comment_loss": "stop", "alert_loss": ""},
        {
            "trail_points": "5",
            "trail_offset": "2",
            "comment_trailing": "trail",
            "alert_trailing": "event",
        },
    ],
)
def test_unambiguous_exit_roundtrip(scope, policy, prices):
    value = event(scope, **prices)
    value["price_pair_policy"] = policy
    value = seal_content_hash(value, schema_id="openpine.intent.v2")
    validate_payload("openpine.intent.v2", value)
    assert verify_content_hash(value, schema_id="openpine.intent.v2")


@pytest.mark.parametrize(
    "fault",
    [
        "policy",
        "scope",
        "both",
        "empty",
        "offset",
        "negative",
        "null_offset",
        "activation",
        "metadata_type",
        "metadata_null",
        "wrong_kind",
    ],
)
def test_incomplete_or_ambiguous_exit_rejected(fault):
    value = event(stop="95", trail_price="105", trail_offset="2", comment_loss="sl")
    if fault == "policy":
        value.pop("price_pair_policy")
    if fault == "scope":
        value.pop("from_entry")
    if fault == "both":
        value["exit_scope"] = "all_entries"
    if fault == "empty":
        for k in ("stop", "trail_price", "trail_offset"):
            value.pop(k)
    if fault == "offset":
        value.pop("trail_offset")
    if fault == "negative":
        value["trail_offset"] = "-1"
    if fault == "null_offset":
        value["trail_offset"] = None
    if fault == "activation":
        value.pop("trail_price")
    if fault == "metadata_type":
        value["comment_loss"] = 42
    if fault == "metadata_null":
        value["alert_loss"] = None
    if fault == "wrong_kind":
        value["kind"] = "entry"
    with pytest.raises(SchemaValidationError):
        validate_payload("openpine.intent.v2", value)


@pytest.mark.parametrize("version", ["2.2.0", "2.3.0", "2.4.0", "2.5.0"])
@pytest.mark.parametrize(
    "field",
    [
        "comment_profit",
        "comment_loss",
        "comment_trailing",
        "alert_profit",
        "alert_loss",
        "alert_trailing",
    ],
)
def test_old_wire_does_not_silently_accept_new_metadata(version, field):
    values = {"profit": "5", "limit": "110"}
    if version == "2.5.0":
        values = {"trail_points": "5", "trail_offset": "2"}
    value = event("all" if version == "2.3.0" else "named", **values)
    value["schema_version"] = version
    if version in {"2.2.0", "2.3.0"}:
        value.pop("price_pair_policy")
    validate_payload("openpine.intent.v2", value)
    value[field] = "new"
    with pytest.raises(SchemaValidationError):
        validate_payload("openpine.intent.v2", value)


def test_old_trailing_subset_remains_strict():
    value = event(trail_price="105", trail_offset="2")
    value["schema_version"] = "2.5.0"
    validate_payload("openpine.intent.v2", value)
    value["stop"] = "95"
    with pytest.raises(SchemaValidationError):
        validate_payload("openpine.intent.v2", value)
