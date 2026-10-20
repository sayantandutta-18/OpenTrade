"""Tests for OrderBook data structures and invariants."""

import pytest
from hypothesis import given
from hypothesis import strategies as st

from impactlab.engine.book import OrderBook
from impactlab.engine.models import Order, OrderType, Side, Status


def test_empty_book() -> None:
    book = OrderBook()
    assert book.best_bid is None
    assert book.best_ask is None
    assert book.spread is None
    assert book.mid is None
    bids, asks = book.depth(5)
    assert bids == []
    assert asks == []
    book.check_invariants()


def test_add_resting_and_best_prices() -> None:
    book = OrderBook()

    # Add bids
    book.add_resting(
        Order(
            id=1,
            side=Side.BUY,
            type=OrderType.LIMIT,
            price=9950,
            qty=100,
            remaining=100,
            ts=1,
            owner="u1",
        )
    )
    book.add_resting(
        Order(
            id=2,
            side=Side.BUY,
            type=OrderType.LIMIT,
            price=9970,
            qty=200,
            remaining=200,
            ts=2,
            owner="u2",
        )
    )

    # Add asks
    book.add_resting(
        Order(
            id=3,
            side=Side.SELL,
            type=OrderType.LIMIT,
            price=10000,
            qty=150,
            remaining=150,
            ts=3,
            owner="u3",
        )
    )
    book.add_resting(
        Order(
            id=4,
            side=Side.SELL,
            type=OrderType.LIMIT,
            price=10020,
            qty=250,
            remaining=250,
            ts=4,
            owner="u4",
        )
    )

    book.check_invariants()
    assert book.best_bid == 9970
    assert book.best_ask == 10000
    assert book.spread == 30
    assert book.mid == 9985.0


def test_time_priority_at_same_price() -> None:
    book = OrderBook()
    o1 = Order(
        id=1,
        side=Side.BUY,
        type=OrderType.LIMIT,
        price=10000,
        qty=50,
        remaining=50,
        ts=10,
        owner="u1",
    )
    o2 = Order(
        id=2,
        side=Side.BUY,
        type=OrderType.LIMIT,
        price=10000,
        qty=100,
        remaining=100,
        ts=20,
        owner="u2",
    )
    book.add_resting(o1)
    book.add_resting(o2)

    level_orders = list(book.bids[-10000])
    assert level_orders[0].id == 1
    assert level_orders[1].id == 2
    book.check_invariants()


def test_depth_and_snapshot() -> None:
    book = OrderBook()
    # 3 bids
    for oid, price, qty in [(1, 9990, 100), (2, 9980, 200), (3, 9970, 300)]:
        book.add_resting(
            Order(
                id=oid,
                side=Side.BUY,
                type=OrderType.LIMIT,
                price=price,
                qty=qty,
                remaining=qty,
                ts=oid,
                owner=f"u{oid}",
            )
        )
    # 3 asks
    for oid, price, qty in [(4, 10000, 100), (5, 10010, 200), (6, 10020, 300)]:
        book.add_resting(
            Order(
                id=oid,
                side=Side.SELL,
                type=OrderType.LIMIT,
                price=price,
                qty=qty,
                remaining=qty,
                ts=oid,
                owner=f"u{oid}",
            )
        )

    bids_depth, asks_depth = book.depth(2)
    assert len(bids_depth) == 2
    assert bids_depth[0].price == 9990
    assert bids_depth[0].qty == 100
    assert bids_depth[1].price == 9980

    assert len(asks_depth) == 2
    assert asks_depth[0].price == 10000
    assert asks_depth[0].qty == 100
    assert asks_depth[1].price == 10010

    snap = book.snapshot(ts=100)
    assert snap.ts == 100
    assert snap.best_bid == 9990
    assert snap.best_ask == 10000
    assert snap.spread == 10
    assert snap.mid == 9995.0
    assert snap.total_bid_qty == 600
    assert snap.total_ask_qty == 600
    book.check_invariants()


def test_remove_order_and_cleanup_level() -> None:
    book = OrderBook()
    o1 = Order(
        id=1,
        side=Side.BUY,
        type=OrderType.LIMIT,
        price=9990,
        qty=100,
        remaining=100,
        ts=1,
        owner="u1",
    )
    book.add_resting(o1)
    assert book.best_bid == 9990

    removed = book.remove(1)
    assert removed is not None
    assert removed.id == 1
    assert book.best_bid is None
    assert len(book.bids) == 0
    assert len(book.orders_by_id) == 0
    book.check_invariants()

    assert book.remove(999) is None


def test_cannot_add_crossed_order() -> None:
    book = OrderBook()
    book.add_resting(
        Order(
            id=1,
            side=Side.SELL,
            type=OrderType.LIMIT,
            price=10000,
            qty=100,
            remaining=100,
            ts=1,
            owner="u1",
        )
    )

    with pytest.raises(ValueError, match="Crossed book"):
        book.add_resting(
            Order(
                id=2,
                side=Side.BUY,
                type=OrderType.LIMIT,
                price=10000,
                qty=50,
                remaining=50,
                ts=2,
                owner="u2",
            )
        )

    with pytest.raises(ValueError, match="Crossed book"):
        book.add_resting(
            Order(
                id=3,
                side=Side.BUY,
                type=OrderType.LIMIT,
                price=10005,
                qty=50,
                remaining=50,
                ts=3,
                owner="u3",
            )
        )


@given(
    bids=st.lists(
        st.tuples(
            st.integers(min_value=1000, max_value=9995),
            st.integers(min_value=1, max_value=500),
        ),
        max_size=20,
    ),
    asks=st.lists(
        st.tuples(
            st.integers(min_value=10005, max_value=20000),
            st.integers(min_value=1, max_value=500),
        ),
        max_size=20,
    ),
)
def test_hypothesis_book_invariants(
    bids: list[tuple[int, int]],
    asks: list[tuple[int, int]],
) -> None:
    book = OrderBook()
    order_id = 1
    ts = 1
    added_ids: list[int] = []

    for price, qty in bids:
        o = Order(
            id=order_id,
            side=Side.BUY,
            type=OrderType.LIMIT,
            price=price,
            qty=qty,
            remaining=qty,
            ts=ts,
            owner="hypo",
            status=Status.NEW,
        )
        book.add_resting(o)
        added_ids.append(order_id)
        order_id += 1
        ts += 1

    for price, qty in asks:
        o = Order(
            id=order_id,
            side=Side.SELL,
            type=OrderType.LIMIT,
            price=price,
            qty=qty,
            remaining=qty,
            ts=ts,
            owner="hypo",
            status=Status.NEW,
        )
        book.add_resting(o)
        added_ids.append(order_id)
        order_id += 1
        ts += 1

    book.check_invariants()

    for oid in added_ids[::2]:
        book.remove(oid)
        book.check_invariants()

    for oid in added_ids[1::2]:
        book.remove(oid)
        book.check_invariants()

    assert len(book.orders_by_id) == 0
    assert len(book.bids) == 0
    assert len(book.asks) == 0
