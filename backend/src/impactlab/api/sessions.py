"""In-memory session manager for simulation instances."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from impactlab.engine.matcher import MatchingEngine
from impactlab.flow.generators import FlowSimulator
from impactlab.flow.profiles import StockProfile, get_profile


@dataclass
class SimulationSession:
    """An active simulation session holding an engine and a synthetic flow simulator."""

    id: str
    profile: StockProfile
    engine: MatchingEngine
    simulator: FlowSimulator
    seed: int
    warmup_seconds: float
    created_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())


class SessionStore:
    """Thread-safe / async in-memory store for simulation sessions."""

    def __init__(self) -> None:
        self._sessions: dict[str, SimulationSession] = {}

    def create(
        self,
        profile_name: str = "mid_cap",
        seed: int = 1,
        warmup_seconds: float = 30.0,
        overrides: dict[str, Any] | None = None,
    ) -> SimulationSession:
        """Create and initialize a new simulation session."""
        session_id = str(uuid.uuid4())
        profile = get_profile(profile_name)

        if overrides:
            # Allow tweaking profile parameters for experiments
            profile = StockProfile(
                name=profile.name,
                description=profile.description,
                reference_price=int(overrides.get("reference_price", profile.reference_price)),
                tick_size=int(overrides.get("tick_size", profile.tick_size)),
                lot_size=int(overrides.get("lot_size", profile.lot_size)),
                typical_spread_ticks=int(
                    overrides.get("typical_spread_ticks", profile.typical_spread_ticks)
                ),
                target_depth_shares=int(
                    overrides.get("target_depth_shares", profile.target_depth_shares)
                ),
                limit_arrival_rate=float(
                    overrides.get("limit_arrival_rate", profile.limit_arrival_rate)
                ),
                market_arrival_rate=float(
                    overrides.get("market_arrival_rate", profile.market_arrival_rate)
                ),
                cancel_rate=float(overrides.get("cancel_rate", profile.cancel_rate)),
                size_median=int(overrides.get("size_median", profile.size_median)),
                size_sigma=float(overrides.get("size_sigma", profile.size_sigma)),
                min_order_qty=int(overrides.get("min_order_qty", profile.min_order_qty)),
                max_order_qty=int(overrides.get("max_order_qty", profile.max_order_qty)),
                daily_volatility_pct=float(
                    overrides.get("daily_volatility_pct", profile.daily_volatility_pct)
                ),
            )

        engine = MatchingEngine(tick_size=profile.tick_size, lot_size=profile.lot_size)
        simulator = FlowSimulator(profile=profile, seed=seed)
        if warmup_seconds > 0:
            simulator.warmup(engine, seconds=warmup_seconds)

        session = SimulationSession(
            id=session_id,
            profile=profile,
            engine=engine,
            simulator=simulator,
            seed=seed,
            warmup_seconds=warmup_seconds,
        )
        self._sessions[session_id] = session
        return session

    def get(self, session_id: str) -> SimulationSession | None:
        """Retrieve a session by its ID."""
        return self._sessions.get(session_id)

    def delete(self, session_id: str) -> bool:
        """Delete a session."""
        return self._sessions.pop(session_id, None) is not None


session_store = SessionStore()
