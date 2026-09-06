"""Every text field in the published 2.6 exit contract remains exact and versioned."""

from copy import deepcopy

import pytest
from test_rc3_contracts import _intent

from openpine_contracts import (
    SchemaValidationError,
    seal_content_hash,
    validate_payload,
    verify_content_hash,
)

FIELDS = (
    "comment_profit",
    "comment_loss",
    "comment_trailing",
    "alert_profit",
    "alert_loss",
    "alert_trailing",
)


def old(version):
    kwargs = dict(order_id="X", schema_version=version)
    if version == "2.3.0":
        kwargs.update(exit_scope="all_entries", limit="110")
    else:
        kwargs["from_entry"] = "A"
    if version in ("2.2.0", "2.4.0"):
        kwargs.update(profit="2", limit="110")
    if version in ("2.4.0", "2.5.0"):
        kwargs["price_pair_policy"] = "first_trigger"
    if version == "2.5.0":
        kwargs.update(trail_points="5", trail_offset="2")
    return _intent("exit", **kwargs)


def extended(version="2.2.0", **metadata):
    event = old(version)
    event.update(
        schema_version="2.6.0",
        price_pair_policy="first_trigger" if version in ("2.4.0", "2.5.0") else "absolute_first",
        **(metadata or {"comment_profit": "TP"}),
    )
    return event


@pytest.mark.parametrize("version", ["2.2.0", "2.3.0", "2.4.0", "2.5.0"])
@pytest.mark.parametrize("field", FIELDS)
@pytest.mark.parametrize("text", ["", "Тест <&> {{strategy.order.id}}"])
def test_leg_text_roundtrips_without_changing_price_contract(version, field, text):
    validate_payload("openpine.intent.v2", old(version))
    event = seal_content_hash(extended(version, **{field: text}), schema_id="openpine.intent.v2")
    validate_payload("openpine.intent.v2", event)
    assert verify_content_hash(event, schema_id="openpine.intent.v2")
    assert event[field] == text


@pytest.mark.parametrize(
    "fault",
    [
        "unknown_field",
        "no_active_leg",
        "null",
        "bool",
        "bad_policy",
        "wrong_kind",
        "old_version",
        "unknown_version",
        "missing_policy",
        "both_scopes",
        "bad_pair",
        "bad_trail",
    ],
)
def test_ambiguous_or_malformed_metadata_cannot_bypass_old_contracts(fault):
    event = extended()
    if fault == "unknown_field":
        event["arbitrary"] = "x"
    elif fault == "no_active_leg":
        event.pop("profit")
        event.pop("limit")
    elif fault in {"null", "bool"}:
        event["comment_profit"] = None if fault == "null" else True
    elif fault == "bad_policy":
        event["price_pair_policy"] = "unknown"
    elif fault == "wrong_kind":
        event["kind"] = "entry"
        event.update(qty="1", direction="LONG")
    elif fault == "old_version":
        event["schema_version"] = "2.2.0"
    elif fault == "unknown_version":
        event["schema_version"] = "2.7.0"
    elif fault == "missing_policy":
        event.pop("price_pair_policy")
    elif fault == "both_scopes":
        event["exit_scope"] = "all_entries"
    elif fault == "bad_pair":
        event = extended("2.4.0")
        event["profit"] = True
    else:
        event = extended("2.5.0")
        event.pop("trail_offset")
    with pytest.raises(SchemaValidationError):
        validate_payload("openpine.intent.v2", event)


@pytest.mark.parametrize("version", ["2.2.0", "2.3.0", "2.4.0", "2.5.0"])
def test_metadata_is_not_an_unversioned_addition(version):
    event = old(version)
    before = deepcopy(event)
    event["alert_profit"] = "TP"
    with pytest.raises(SchemaValidationError):
        validate_payload("openpine.intent.v2", event)
    validate_payload("openpine.intent.v2", before)
