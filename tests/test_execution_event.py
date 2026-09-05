from dataclasses import FrozenInstanceError, replace

import pytest

from openpine_contracts import ExecutionEvent, validate_payload


def event(**kwargs):
    values = dict(
        sequence=0,
        bar_index=0,
        last_bar_index=2,
        last_historical_bar_index=2,
        bar_open_time_utc_ms=0,
        phase="HISTORICAL_EVAL",
        realtime=False,
        final_tick=True,
        tick_index=0,
        recalc_iteration=0,
        cause="BAR_CLOSE",
    )
    return ExecutionEvent(**(values | kwargs))


def test_callback_descriptor_roundtrips_and_has_distinct_last_flags():
    first = event()
    validate_payload("openpine.execution_event.v1", first.to_dict())
    assert ExecutionEvent.from_dict(first.to_dict()) == first
    assert not first.is_last and not first.is_last_confirmed_history
    closed = replace(first, bar_index=2)
    assert closed.is_last and closed.is_last_confirmed_history
    prelive = replace(first, bar_index=1, last_historical_bar_index=1)
    assert not prelive.is_last and prelive.is_last_confirmed_history
    with pytest.raises(FrozenInstanceError):
        first.sequence = 1


@pytest.mark.parametrize(
    "changes",
    [
        {"sequence": True},
        {"bar_index": -1},
        {"tick_index": -1},
        {"recalc_iteration": False},
        {"bar_index": 3},
        {"last_historical_bar_index": 3},
        {"realtime": True},
        {"final_tick": False},
        {"phase": "REALTIME_EVAL"},
        {"cause": "nonsense"},
        {"fill_order_id": "fake"},
        {"fill_price": "1"},
        {"phase": "ORDER_FILL_RECALC", "cause": "ORDER_FILL"},
    ],
)
def test_inconsistent_execution_identity_is_rejected(changes):
    with pytest.raises(ValueError):
        event(**changes)


def test_fill_cause_and_tick_ordinal_are_independent():
    fill = event(
        phase="ORDER_FILL_RECALC",
        cause="ORDER_FILL",
        recalc_iteration=3,
        fill_order_id="L",
        fill_price="101.5",
    )
    assert fill.tick_index == 0 and fill.recalc_iteration == 3
    validate_payload("openpine.execution_event.v1", fill.to_dict())
    for price in ("NaN", "Infinity", "invalid"):
        with pytest.raises(ValueError):
            replace(fill, fill_price=price)
    with pytest.raises(ValueError):
        ExecutionEvent.from_dict(fill.to_dict() | {"unexpected": 1})
