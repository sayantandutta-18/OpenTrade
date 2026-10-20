"""Order book implementation using SortedDict and deque for price-time priority.

Prices are integers in paise. Quantities are integers.
"""

from __future__ import annotations

from collections import deque

from sortedcontainers import SortedDict  # type: ignore[import-untyped]

from impactlab.engine.models import BookSnapshot, LevelSummary, Order, Side


class OrderBook:
    """A price-time priority limit order book.

    Bids are ordered from highest price to lowest price.
    Asks are ordered from lowest price to highest price.
    Within each price level, orders are matched in FIFO order of their arrival.
    """

    __slots__ = ("_bids", "_asks", "_orders_by_id")

    def __init__(self) -> None:
        # Bids keyed by -price so the first key is -best_bid (highest price)
        self._bids: SortedDict[int, deque[Order]] = SortedDict()
        # Asks keyed by +price so the first key is +best_ask (lowest price)
        self._asks: SortedDict[int, deque[Order]] = SortedDict()
        self._orders_by_id: dict[int, Order] = {}

    @property
    def bids(self) -> SortedDict[int, deque[Order]]:
        """Raw bids SortedDict."""
        return self._bids

    @property
    def asks(self) -> SortedDict[int, deque[Order]]:
        """Raw asks SortedDict."""
        return self._asks

    @property
    def orders_by_id(self) -> dict[int, Order]:
        """Map of order ID to resting Order."""
        return self._orders_by_id

    @property
    def best_bid(self) -> int | None:
        """Best (highest) bid price in paise, or None if no bids exist."""
        if not self._bids:
            return None
        neg_price, _ = self._bids.peekitem(0)
        return int(-neg_price)

    @property
    def best_ask(self) -> int | None:
        """Best (lowest) ask price in paise, or None if no asks exist."""
        if not self._asks:
            return None
        price, _ = self._asks.peekitem(0)
        return int(price)

    @property
    def spread(self) -> int | None:
        """Bid-ask spread in paise (best_ask - best_bid), or None if one side is empty."""
        bb = self.best_bid
        ba = self.best_ask
        if bb is None or ba is None:
            return None
        return ba - bb

    @property
    def mid(self) -> float | None:
        """Mid price in paise (best_bid + best_ask) / 2.0, or None if one side is empty."""
        bb = self.best_bid
        ba = self.best_ask
        if bb is None or ba is None:
            return None
        return (bb + ba) / 2.0

    def get(self, order_id: int) -> Order | None:
        """Get an order by its ID."""
        return self._orders_by_id.get(order_id)

    def add_resting(self, order: Order) -> None:
        """Add a resting order to the book.

        Args:
            order: Order to add. Must have price set and remaining > 0.

        Raises:
            ValueError: If order has invalid price, zero remaining, or would cross the book.
        """
        if order.price is None or order.price <= 0:
            raise ValueError(f"Resting order must have price > 0, got {order.price}")
        if order.remaining <= 0:
            raise ValueError(f"Resting order must have remaining > 0, got {order.remaining}")
        if order.id in self._orders_by_id:
            raise ValueError(f"Order ID {order.id} already exists in book")

        # Validate that adding this order does not produce a crossed book
        if order.side == Side.BUY:
            ba = self.best_ask
            if ba is not None and order.price >= ba:
                raise ValueError(f"Crossed book: Bid price {order.price} >= best ask {ba}")
            key = -order.price
            if key not in self._bids:
                self._bids[key] = deque()
            self._bids[key].append(order)
        else:
            bb = self.best_bid
            if bb is not None and order.price <= bb:
                raise ValueError(f"Crossed book: Ask price {order.price} <= best bid {bb}")
            key = order.price
            if key not in self._asks:
                self._asks[key] = deque()
            self._asks[key].append(order)

        self._orders_by_id[order.id] = order

    def remove(self, order_id: int) -> Order | None:
        """Remove a resting order from the book by ID.

        Args:
            order_id: ID of the order to remove.

        Returns:
            The removed Order, or None if not found.
        """
        order = self._orders_by_id.pop(order_id, None)
        if order is None:
            return None

        if order.price is None:
            return order

        if order.side == Side.BUY:
            key = -order.price
            level = self._bids.get(key)
            if level is not None:
                try:
                    level.remove(order)
                except ValueError:
                    pass
                if not level:
                    del self._bids[key]
        else:
            key = order.price
            level = self._asks.get(key)
            if level is not None:
                try:
                    level.remove(order)
                except ValueError:
                    pass
                if not level:
                    del self._asks[key]

        return order

    def depth(self, levels: int = 10) -> tuple[list[LevelSummary], list[LevelSummary]]:
        """Get aggregated depth for top N levels on both sides.

        Returns:
            Tuple of (bids_levels, asks_levels), where bids are sorted from
            highest price to lowest, and asks are sorted lowest to highest.
        """
        bid_summaries: list[LevelSummary] = []
        for i, (neg_price, queue) in enumerate(self._bids.items()):
            if i >= levels:
                break
            price = -neg_price
            tot_qty = sum(o.remaining for o in queue)
            bid_summaries.append(LevelSummary(price=price, qty=tot_qty, order_count=len(queue)))

        ask_summaries: list[LevelSummary] = []
        for i, (price, queue) in enumerate(self._asks.items()):
            if i >= levels:
                break
            tot_qty = sum(o.remaining for o in queue)
            ask_summaries.append(LevelSummary(price=price, qty=tot_qty, order_count=len(queue)))

        return bid_summaries, ask_summaries

    def snapshot(self, ts: int = 0) -> BookSnapshot:
        """Return an immutable snapshot of the current order book state."""
        bids_depth, asks_depth = self.depth(levels=1000)
        tot_bid = sum(lvl.qty for lvl in bids_depth)
        tot_ask = sum(lvl.qty for lvl in asks_depth)
        return BookSnapshot(
            ts=ts,
            bids=tuple(bids_depth),
            asks=tuple(asks_depth),
            best_bid=self.best_bid,
            best_ask=self.best_ask,
            spread=self.spread,
            mid=self.mid,
            total_bid_qty=tot_bid,
            total_ask_qty=tot_ask,
        )

    def check_invariants(self) -> None:
        """Validate all order book microstructure invariants.

        Raises:
            AssertionError: If any invariant is violated.
        """
        # Invariant 1: best_bid < best_ask whenever both exist
        bb = self.best_bid
        ba = self.best_ask
        if bb is not None and ba is not None:
            assert bb < ba, f"Crossed book: best_bid={bb} >= best_ask={ba}"

        # Invariant 2 & 4: orders have remaining > 0 and are sorted by ts within level
        total_level_qty = 0
        seen_order_ids: set[int] = set()

        for neg_price, queue in self._bids.items():
            assert len(queue) > 0, f"Empty queue kept for bid level {-neg_price}"
            prev_ts = -1
            for o in queue:
                assert o.remaining > 0, f"Order {o.id} has remaining {o.remaining} <= 0"
                assert o.price == -neg_price, f"Order price {o.price} != level {-neg_price}"
                assert o.side == Side.BUY, f"Non-buy order {o.id} in bids"
                assert o.ts >= prev_ts, f"Order time priority violated in bid level {-neg_price}"
                prev_ts = o.ts
                total_level_qty += o.remaining
                seen_order_ids.add(o.id)

        for price, queue in self._asks.items():
            assert len(queue) > 0, f"Empty queue kept for ask level {price}"
            prev_ts = -1
            for o in queue:
                assert o.remaining > 0, f"Order {o.id} has remaining {o.remaining} <= 0"
                assert o.price == price, f"Order price {o.price} != level {price}"
                assert o.side == Side.SELL, f"Non-sell order {o.id} in asks"
                assert o.ts >= prev_ts, f"Order time priority violated in ask level {price}"
                prev_ts = o.ts
                total_level_qty += o.remaining
                seen_order_ids.add(o.id)

        # Invariant 3: sum of quantities in orders_by_id equals sum over all price levels
        total_by_id = sum(o.remaining for o in self._orders_by_id.values())
        assert total_level_qty == total_by_id, (
            f"Quantity mismatch: levels total {total_level_qty} != orders_by_id total {total_by_id}"
        )
        assert seen_order_ids == set(self._orders_by_id.keys()), (
            "Order ID set mismatch between index and price levels"
        )
