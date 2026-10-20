"""Base protocols and data structures for algorithmic execution strategies."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from impactlab.engine.models import OrderType, Side, Trade


@dataclass(frozen=True, slots=True)
class OrderRequest:
    """Request to place an order from an execution strategy."""

    side: Side
    type: OrderType
    qty: int
    price: int | None = None
    owner: str = "algo_strategy"


@dataclass(frozen=True, slots=True)
class SliceExecution:
    """Record of an individual slice execution."""

    slice_index: int
    scheduled_time: float  # in seconds from strategy start
    executed_time: float  # in seconds from strategy start
    requested_qty: int
    filled_qty: int
    avg_price: float | None  # in paise
    trades: tuple[Trade, ...]


class ExecutionStrategy(Protocol):
    """Protocol for execution strategies (Market, TWAP, VWAP, Passive)."""

    name: str

    def plan_slices(
        self,
        side: Side,
        total_qty: int,
        start_time: float = 0.0,
    ) -> list[tuple[float, OrderRequest]]:
        """Return list of (scheduled_time_offset_sec, OrderRequest) pairs.

        Guaranteed invariant: sum(req.qty for _, req in pairs) == total_qty.
        """
        ...
