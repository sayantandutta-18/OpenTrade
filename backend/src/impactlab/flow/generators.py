"""Synthetic order flow generator and market simulation.

Purely deterministic: driven by an explicit seeded numpy.random.Generator.
Simulated time is tracked as an integer in microseconds.
"""

from __future__ import annotations

import numpy as np

from impactlab.engine.matcher import MatchingEngine
from impactlab.engine.models import Order, OrderType, Side
from impactlab.flow.profiles import StockProfile


class FlowSimulator:
    """Simulates realistic synthetic order flow for a given stock profile.

    Features:
    - Dedicated Market Maker quoting symmetric bids/asks around mid price.
    - Poisson arrivals for limit orders, market orders, and cancellations.
    - Log-normally distributed order sizes.
    - Power-law/geometric price offset distribution around the touch.
    - 100% deterministic given the same seed.
    """

    __slots__ = (
        "profile",
        "rng",
        "current_time_us",
        "_order_id_counter",
        "_mm_order_ids",
        "fundamental_price",
    )

    def __init__(self, profile: StockProfile, seed: int = 42) -> None:
        self.profile = profile
        self.rng = np.random.default_rng(seed)
        self.current_time_us: int = 0
        self._order_id_counter: int = 1
        self._mm_order_ids: set[int] = set()
        self.fundamental_price: int = profile.reference_price

    def _next_order_id(self) -> int:
        oid = self._order_id_counter
        self._order_id_counter += 1
        return oid

    def _sample_size(self) -> int:
        """Sample an order size from the log-normal distribution."""
        raw = float(self.rng.lognormal(self.profile.size_mu, self.profile.size_sigma))
        clamped = int(np.clip(raw, self.profile.min_order_qty, self.profile.max_order_qty))
        lot = max(1, self.profile.lot_size)
        return max(lot, (clamped // lot) * lot)

    def _snap_to_tick(self, price: int) -> int:
        """Align price to tick grid."""
        tick = self.profile.tick_size
        return max(tick, (price // tick) * tick)

    def _refresh_market_maker(self, engine: MatchingEngine) -> None:
        """Refresh market maker quotes around current mid/fundamental price."""
        # Cancel old MM quotes
        for oid in list(self._mm_order_ids):
            engine.cancel(oid)
        self._mm_order_ids.clear()

        mid = engine.book.mid
        ref = int(round(mid)) if mid is not None else self.fundamental_price
        tick = self.profile.tick_size
        half_spread_ticks = max(1, self.profile.typical_spread_ticks // 2)

        # Quote 5 levels on each side
        base_qty = max(10, self.profile.target_depth_shares // 50)

        for lvl in range(5):
            spread_offset = (half_spread_ticks + lvl) * tick
            bid_price = self._snap_to_tick(ref - spread_offset)
            ask_price = self._snap_to_tick(ref + spread_offset)
            lvl_qty = base_qty * (lvl + 1)

            if bid_price > 0:
                bid_order = Order(
                    id=self._next_order_id(),
                    side=Side.BUY,
                    type=OrderType.LIMIT,
                    price=bid_price,
                    qty=lvl_qty,
                    remaining=lvl_qty,
                    ts=self.current_time_us,
                    owner="mm",
                )
                engine.submit(bid_order)
                self._mm_order_ids.add(bid_order.id)

            if ask_price > 0:
                ask_order = Order(
                    id=self._next_order_id(),
                    side=Side.SELL,
                    type=OrderType.LIMIT,
                    price=ask_price,
                    qty=lvl_qty,
                    remaining=lvl_qty,
                    ts=self.current_time_us,
                    owner="mm",
                )
                engine.submit(ask_order)
                self._mm_order_ids.add(ask_order.id)

    def warmup(self, engine: MatchingEngine, seconds: float = 60.0) -> None:
        """Warm up the order book to reach a stationary depth and spread."""
        self._refresh_market_maker(engine)
        self.advance(engine, seconds)

    def advance(self, engine: MatchingEngine, seconds: float) -> int:
        """Advance simulated time by feeding synthetic events into the engine.

        Args:
            engine: The MatchingEngine instance.
            seconds: Duration in simulated seconds to advance.

        Returns:
            Number of events generated.
        """
        end_time_us = self.current_time_us + int(round(seconds * 1_000_000))
        events_processed = 0

        # Rate parameters
        rate_limit = self.profile.limit_arrival_rate
        rate_market = self.profile.market_arrival_rate
        total_arrival_rate = rate_limit + rate_market

        if total_arrival_rate <= 0:
            self.current_time_us = end_time_us
            return 0

        tick = self.profile.tick_size

        while self.current_time_us < end_time_us:
            # 1. Sample inter-arrival time (exponential)
            dt_sec = float(self.rng.exponential(1.0 / total_arrival_rate))
            dt_us = max(1, int(round(dt_sec * 1_000_000)))
            self.current_time_us += dt_us
            if self.current_time_us >= end_time_us:
                break

            # 2. Random walk drift on fundamental price
            vol_per_sec = (self.profile.daily_volatility_pct / 100.0) / np.sqrt(252 * 22500)
            drift_std = self.fundamental_price * vol_per_sec * np.sqrt(max(0.001, dt_sec))
            drift = int(round(float(self.rng.normal(0, drift_std))))
            if drift != 0:
                self.fundamental_price = self._snap_to_tick(self.fundamental_price + drift)

            # 3. Handle cancellations periodically
            resting_orders = list(engine.book.orders_by_id.values())
            if resting_orders and float(self.rng.random()) < (
                self.profile.cancel_rate * dt_sec * len(resting_orders)
            ):
                non_mm_orders = [o for o in resting_orders if o.owner != "mm"]
                candidates = non_mm_orders if non_mm_orders else resting_orders
                if candidates:
                    idx = int(self.rng.integers(0, len(candidates)))
                    chosen = candidates[idx]
                    engine.cancel(chosen.id)
                    events_processed += 1

            # 4. Decide event type: Market order vs Limit order
            is_market = float(self.rng.random()) < (rate_market / total_arrival_rate)
            side = Side.BUY if float(self.rng.random()) < 0.5 else Side.SELL
            size = self._sample_size()

            if is_market:
                order = Order(
                    id=self._next_order_id(),
                    side=side,
                    type=OrderType.MARKET,
                    price=None,
                    qty=size,
                    remaining=size,
                    ts=self.current_time_us,
                    owner=f"noise_{self._order_id_counter}",
                )
                engine.submit(order)
                events_processed += 1
            else:
                # Limit order: pick price offset in ticks from current touch
                touch = engine.book.best_bid if side == Side.BUY else engine.book.best_ask
                if touch is None:
                    touch = self.fundamental_price

                # Exponential offset in ticks (steep drop-off into depth)
                offset_ticks = int(self.rng.geometric(p=0.35)) - 1
                if side == Side.BUY:
                    limit_price = self._snap_to_tick(touch - (offset_ticks * tick))
                else:
                    limit_price = self._snap_to_tick(touch + (offset_ticks * tick))

                order = Order(
                    id=self._next_order_id(),
                    side=side,
                    type=OrderType.LIMIT,
                    price=limit_price,
                    qty=size,
                    remaining=size,
                    ts=self.current_time_us,
                    owner=f"noise_{self._order_id_counter}",
                )
                engine.submit(order)
                events_processed += 1

            # Periodically maintain MM quotes if book spreads blow out or either side is empty
            if engine.book.best_bid is None or engine.book.best_ask is None:
                self._refresh_market_maker(engine)
            elif engine.book.spread is not None and engine.book.spread > (
                self.profile.typical_spread_ticks * 4 * tick
            ):
                self._refresh_market_maker(engine)

        self.current_time_us = end_time_us
        return events_processed
