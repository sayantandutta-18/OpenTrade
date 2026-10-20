"""Market order and Time-Weighted Average Price (TWAP) execution strategies."""

from __future__ import annotations

from dataclasses import dataclass

from impactlab.engine.models import OrderType, Side
from impactlab.execution.base import OrderRequest


@dataclass(slots=True)
class MarketStrategy:
    """Immediate single market order strategy."""

    name: str = "market"

    def plan_slices(
        self,
        side: Side,
        total_qty: int,
        start_time: float = 0.0,
    ) -> list[tuple[float, OrderRequest]]:
        if total_qty <= 0:
            return []
        req = OrderRequest(side=side, type=OrderType.MARKET, qty=total_qty, owner="market_algo")
        return [(start_time, req)]


@dataclass(slots=True)
class TWAPStrategy:
    """Time-Weighted Average Price (TWAP) execution strategy.

    Slices total quantity into N equal parts released at regular intervals over duration.
    Invariant: sum(req.qty for _, req in slices) == total_qty.
    """

    duration_seconds: float = 60.0
    num_slices: int = 5
    name: str = "twap"

    def plan_slices(
        self,
        side: Side,
        total_qty: int,
        start_time: float = 0.0,
    ) -> list[tuple[float, OrderRequest]]:
        if total_qty <= 0 or self.num_slices <= 0:
            return []

        n = min(self.num_slices, total_qty)
        base_slice = total_qty // n
        remainder = total_qty % n

        interval = self.duration_seconds / n if n > 1 else 0.0
        slices: list[tuple[float, OrderRequest]] = []

        for i in range(n):
            # Distribute remainder across the first 'remainder' slices
            qty_i = base_slice + (1 if i < remainder else 0)
            t_i = start_time + (i * interval)
            req = OrderRequest(
                side=side,
                type=OrderType.MARKET,
                qty=qty_i,
                owner=f"twap_slice_{i + 1}",
            )
            slices.append((t_i, req))

        return slices
