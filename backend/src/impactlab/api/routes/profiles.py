"""Routes for listing stock profiles."""

from __future__ import annotations

from fastapi import APIRouter

from impactlab.api.schemas import ProfileResponse
from impactlab.cli import format_inr
from impactlab.flow.profiles import PROFILES

router = APIRouter(prefix="/profiles", tags=["profiles"])


@router.get("", response_model=list[ProfileResponse])
def list_profiles() -> list[ProfileResponse]:
    """List all available stock profiles (Large-cap, Mid-cap, Small-cap)."""
    items: list[ProfileResponse] = []
    for p in PROFILES.values():
        items.append(
            ProfileResponse(
                name=p.name,
                description=p.description,
                reference_price=p.reference_price,
                reference_price_formatted=format_inr(p.reference_price),
                tick_size=p.tick_size,
                lot_size=p.lot_size,
                typical_spread_ticks=p.typical_spread_ticks,
                target_depth_shares=p.target_depth_shares,
                limit_arrival_rate=p.limit_arrival_rate,
                market_arrival_rate=p.market_arrival_rate,
                cancel_rate=p.cancel_rate,
                daily_volatility_pct=p.daily_volatility_pct,
            )
        )
    return items
