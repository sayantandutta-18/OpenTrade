"""Stock profile configurations for synthetic order flow generation.

Prices are stored in paise (1 Rs = 100 paise).
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field


@dataclass(slots=True)
class StockProfile:
    """Configuration for a stock market profile."""

    name: str
    description: str
    reference_price: int  # in paise
    tick_size: int = 5  # in paise (default Rs 0.05)
    lot_size: int = 1
    typical_spread_ticks: int = 2
    target_depth_shares: int = 50_000
    limit_arrival_rate: float = 40.0  # per simulated second
    market_arrival_rate: float = 6.0  # per simulated second
    cancel_rate: float = 0.02  # fraction of resting orders canceled per sec
    size_median: int = 80
    size_sigma: float = 0.8
    min_order_qty: int = 1
    max_order_qty: int = 5_000
    daily_volatility_pct: float = 22.0
    extra: dict[str, float] = field(default_factory=dict)

    @property
    def size_mu(self) -> float:
        """Log-normal mu parameter corresponding to the specified median."""
        return math.log(max(1, self.size_median))


LARGE_CAP = StockProfile(
    name="large_cap",
    description="Deep large-cap equity (e.g. Reliance / HDFC Bank / TCS style)",
    reference_price=250_000,  # Rs 2,500
    tick_size=5,
    typical_spread_ticks=1,
    target_depth_shares=50_000,
    limit_arrival_rate=40.0,
    market_arrival_rate=6.0,
    cancel_rate=0.02,
    size_median=80,
    size_sigma=0.8,
    min_order_qty=1,
    max_order_qty=5_000,
    daily_volatility_pct=22.0,
)

MID_CAP = StockProfile(
    name="mid_cap",
    description="Mid-cap equity with moderate liquidity and spread",
    reference_price=45_000,  # Rs 450
    tick_size=5,
    typical_spread_ticks=4,
    target_depth_shares=6_000,
    limit_arrival_rate=8.0,
    market_arrival_rate=1.2,
    cancel_rate=0.03,
    size_median=40,
    size_sigma=0.9,
    min_order_qty=1,
    max_order_qty=2_000,
    daily_volatility_pct=35.0,
)

SMALL_CAP = StockProfile(
    name="small_cap",
    description="Thin small-cap equity with wide spreads and shallow depth",
    reference_price=8_500,  # Rs 85
    tick_size=5,
    typical_spread_ticks=12,
    target_depth_shares=800,
    limit_arrival_rate=1.5,
    market_arrival_rate=0.2,
    cancel_rate=0.05,
    size_median=25,
    size_sigma=1.0,
    min_order_qty=1,
    max_order_qty=1_000,
    daily_volatility_pct=55.0,
)

PROFILES: dict[str, StockProfile] = {
    "large_cap": LARGE_CAP,
    "mid_cap": MID_CAP,
    "small_cap": SMALL_CAP,
}


def get_profile(name: str) -> StockProfile:
    """Retrieve a StockProfile by name."""
    norm = name.strip().lower()
    if norm in PROFILES:
        return PROFILES[norm]
    raise KeyError(f"Unknown stock profile '{name}'. Choose from: {list(PROFILES.keys())}")
