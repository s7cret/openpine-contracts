"""Transport-independent identity of one Pine execution, not one chart bar.

The containing worker message seals this value. Tick ordinal, callback ordinal
and fill-recalculation ordinal are deliberately different coordinates.
"""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass, fields
from decimal import Decimal, InvalidOperation
from typing import Mapping


@dataclass(frozen=True, slots=True)
class ExecutionEvent:
    sequence: int
    bar_index: int
    last_bar_index: int
    last_historical_bar_index: int
    bar_open_time_utc_ms: int
    phase: str
    realtime: bool
    final_tick: bool
    tick_index: int
    recalc_iteration: int
    cause: str
    fill_order_id: str | None = None
    fill_price: str | None = None

    def __post_init__(self) -> None:
        for name in (
            "sequence",
            "bar_index",
            "last_bar_index",
            "bar_open_time_utc_ms",
            "tick_index",
            "recalc_iteration",
        ):
            value = getattr(self, name)
            if type(value) is not int or value < 0:
                raise ValueError(f"execution event {name} must be a nonnegative integer")
        if (
            type(self.last_historical_bar_index) is not int
            or not -1 <= self.last_historical_bar_index <= self.last_bar_index
            or self.bar_index > self.last_bar_index
        ):
            raise ValueError("execution event dataset bounds are inconsistent")
        if type(self.realtime) is not bool or type(self.final_tick) is not bool:
            raise ValueError("execution event flags must be boolean")
        if self.realtime != (self.bar_index > self.last_historical_bar_index):
            raise ValueError("execution event historical boundary is inconsistent")
        if not self.realtime and not self.final_tick:
            raise ValueError("historical execution must have confirmed data")
        phases = {
            "BAR_CLOSE": "HISTORICAL_EVAL",
            "TICK": "REALTIME_EVAL",
            "ORDER_FILL": "ORDER_FILL_RECALC",
        }
        if self.cause not in phases or self.phase != phases[self.cause]:
            raise ValueError("execution event phase/cause is inconsistent")
        if self.cause != "ORDER_FILL" and self.realtime != (self.cause == "TICK"):
            raise ValueError("execution event cause does not match market phase")
        if self.cause == "ORDER_FILL":
            if type(self.fill_order_id) is not str or not self.fill_order_id:
                raise ValueError("fill recalculation requires its order identity")
            try:
                if (
                    type(self.fill_price) is not str
                    or re.fullmatch(r"-?(?:0|[1-9][0-9]*)(?:\.[0-9]+)?", self.fill_price) is None
                    or not Decimal(self.fill_price).is_finite()
                ):
                    raise ValueError("fill recalculation requires a finite decimal price")
            except InvalidOperation as error:
                raise ValueError("fill price is not a decimal") from error
        elif self.fill_order_id is not None or self.fill_price is not None:
            raise ValueError("non-fill callback cannot claim a fill cause")

    @property
    def is_last(self) -> bool:
        return self.realtime or self.bar_index == self.last_bar_index

    @property
    def is_last_confirmed_history(self) -> bool:
        return not self.realtime and self.bar_index == self.last_historical_bar_index

    def to_dict(self) -> dict[str, object]:
        return {"schema_id": "openpine.execution_event.v1", **asdict(self)}

    @classmethod
    def from_dict(cls, value: Mapping[str, object]) -> ExecutionEvent:
        names = {field.name for field in fields(cls)}
        if (
            not isinstance(value, Mapping)
            or set(value) != names | {"schema_id"}
            or value.get("schema_id") != "openpine.execution_event.v1"
        ):
            raise ValueError("execution event schema is invalid")
        return cls(**{name: value[name] for name in names})  # type: ignore[arg-type]
