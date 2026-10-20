"""Volume-Weighted Average Price (VWAP) execution strategy with U-shaped intraday curve."""

from __future__ import annotations

from dataclasses import dataclass

from impactlab.engine.models import OrderType, Side
from impactlab.execution.base import OrderRequest


@dataclass(slots=True)
class VWAPStrategy:
    """Volume-Weighted Average Price (VWAP) execution strategy.

    Allocates order slices according to a canonical U-shaped volume profile
    using the Largest Remainder (Hamilton) method.
    Guarantees that slice quantities strictly sum to total_qty.
    """

    duration_seconds: float = 60.0
    num_slices: int = 5
    name: str = "vwap"

    def plan_slices(
        self,
        side: Side,
        total_qty: int,
        start_time: float = 0.0,
    ) -> list[tuple[float, OrderRequest]]:
        if total_qty <= 0 or self.num_slices <= 0:
            return []

        n = min(self.num_slices, total_qty)
        if n == 1:
            return [
                (
                    start_time,
                    OrderRequest(side=side, type=OrderType.MARKET, qty=total_qty, owner="vwap_1"),
                )
            ]

        # Generate quadratic U-curve weights: w(x) = (x - 0.5)^2 + 0.1
        xs = [i / (n - 1) for i in range(n)]
        raw_weights = [((x - 0.5) ** 2) + 0.1 for x in xs]
        total_w = sum(raw_weights)
        norm_weights = [w / total_w for w in raw_weights]

        # Largest Remainder (Hamilton) method:
        # Guarantee every slice gets at least 1 share, then distribute remaining shares
        shares_to_distribute = total_qty - n
        exact_shares = [w * shares_to_distribute for w in norm_weights]
        integer_parts = [int(x) for x in exact_shares]
        fractional_parts = [x - integer_parts[i] for i, x in enumerate(exact_shares)]

        remainder = shares_to_distribute - sum(integer_parts)
        # Sort indices by largest fractional part
        sorted_indices = sorted(range(n), key=lambda i: fractional_parts[i], reverse=True)
        for i in range(remainder):
            integer_parts[sorted_indices[i]] += 1

        # Each slice gets base 1 + allocated integer part
        allocated = [1 + integer_parts[i] for i in range(n)]

        interval = self.duration_seconds / n
        slices: list[tuple[float, OrderRequest]] = []

        for i, qty_i in enumerate(allocated):
            t_i = start_time + (i * interval)
            slices.append(
                (
                    t_i,
                    OrderRequest(
                        side=side,
                        type=OrderType.MARKET,
                        qty=qty_i,
                        owner=f"vwap_slice_{i + 1}",
                    ),
                )
            )

        return slices
