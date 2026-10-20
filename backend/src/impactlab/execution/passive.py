"""Passive limit order execution strategy with pegging and timeout."""

from __future__ import annotations

from dataclasses import dataclass

from impactlab.engine.models import OrderType, Side
from impactlab.execution.base import OrderRequest


@dataclass(slots=True)
class PassiveLimitStrategy:
    """Passive execution posting limit orders at the near touch."""

    duration_seconds: float = 60.0
    num_slices: int = 5
    name: str = "passive_limit"

    def plan_slices(
        self,
        side: Side,
        total_qty: int,
        start_time: float = 0.0,
    ) -> list[tuple[float, OrderRequest]]:
        if total_qty <= 0 or self.num_slices <= 0:
            return []

        n = min(self.num_slices, total_qty)
        base = total_qty // n
        remainder = total_qty % n
        interval = self.duration_seconds / n if n > 1 else 0.0

        slices: list[tuple[float, OrderRequest]] = []
        for i in range(n):
            qty_i = base + (1 if i < remainder else 0)
            t_i = start_time + (i * interval)
            # Strategy creates POST_ONLY or LIMIT orders designed to earn the spread
            slices.append(
                (
                    t_i,
                    OrderRequest(
                        side=side,
                        type=OrderType.LIMIT,
                        qty=qty_i,
                        price=None,  # pegged to near touch dynamically during execution
                        owner=f"passive_slice_{i + 1}",
                    ),
                )
            )

        return slices
