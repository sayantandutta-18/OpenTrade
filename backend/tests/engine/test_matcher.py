"""Tests for MatchingEngine execution logic and invariants."""

from hypothesis import given
from hypothesis import strategies as st

from impactlab.engine.matcher import MatchingEngine
from impactlab.engine.models import Order, OrderType, Side, Status


def test_time_priority_matching() -> None:
    engine = MatchingEngine()
    # Add two asks at same price 10000
    engine.submit(
        Order(
            id=1,
            side=Side.SELL,
            type=OrderType.LIMIT,
            price=10000,
            qty=100,
            remaining=100,
            ts=1,
            owner="mm1",
        )
    )
    engine.submit(
        Order(
            id=2,
            side=Side.SELL,
            type=OrderType.LIMIT,
            price=10000,
            qty=100,
            remaining=100,
            ts=2,
            owner="mm2",
        )
    )

    # Market buy 150
    trades = engine.submit(
        Order(
            id=3,
            side=Side.BUY,
            type=OrderType.MARKET,
            price=None,
            qty=150,
            remaining=150,
            ts=3,
            owner="u",
        )
    )

    assert len(trades) == 2
    # First trade fills order 1 entirely
    assert trades[0].maker_order_id == 1
    assert trades[0].qty == 100
    # Second trade fills 50 of order 2
    assert trades[1].maker_order_id == 2
    assert trades[1].qty == 50

    assert engine.book.best_ask == 10000
    assert engine.book.asks[10000][0].remaining == 50
    assert engine.book.asks[10000][0].id == 2
    engine.check_invariants()


def test_limit_partial_fill_rests_remainder() -> None:
    engine = MatchingEngine()
    engine.submit(
        Order(
            id=1,
            side=Side.SELL,
            type=OrderType.LIMIT,
            price=10000,
            qty=50,
            remaining=50,
            ts=1,
            owner="mm",
        )
    )

    # Limit buy 100 @ 10000 -> 50 fills, 50 rests as a bid @ 10000
    trades = engine.submit(
        Order(
            id=2,
            side=Side.BUY,
            type=OrderType.LIMIT,
            price=10000,
            qty=100,
            remaining=100,
            ts=2,
            owner="u",
        )
    )

    assert len(trades) == 1
    assert trades[0].qty == 50
    assert engine.book.best_bid == 10000
    assert engine.book.best_ask is None
    assert engine.book.bids[-10000][0].remaining == 50
    assert engine.book.bids[-10000][0].id == 2
    engine.check_invariants()


def test_limit_buy_below_best_ask_rests() -> None:
    engine = MatchingEngine()
    engine.submit(
        Order(
            id=1,
            side=Side.SELL,
            type=OrderType.LIMIT,
            price=10000,
            qty=50,
            remaining=50,
            ts=1,
            owner="mm",
        )
    )
    trades = engine.submit(
        Order(
            id=2,
            side=Side.BUY,
            type=OrderType.LIMIT,
            price=9990,
            qty=50,
            remaining=50,
            ts=2,
            owner="u",
        )
    )

    assert len(trades) == 0
    assert engine.book.best_bid == 9990
    assert engine.book.best_ask == 10000
    engine.check_invariants()


def test_crossing_limit_executes_at_maker_price() -> None:
    engine = MatchingEngine()
    # Maker asks at 10000
    engine.submit(
        Order(
            id=1,
            side=Side.SELL,
            type=OrderType.LIMIT,
            price=10000,
            qty=50,
            remaining=50,
            ts=1,
            owner="mm",
        )
    )
    # Taker bids at 10050
    trades = engine.submit(
        Order(
            id=2,
            side=Side.BUY,
            type=OrderType.LIMIT,
            price=10050,
            qty=50,
            remaining=50,
            ts=2,
            owner="u",
        )
    )

    assert len(trades) == 1
    assert trades[0].price == 10000
    engine.check_invariants()


def test_ioc_and_fok_orders() -> None:
    engine = MatchingEngine()
    engine.submit(
        Order(
            id=1,
            side=Side.SELL,
            type=OrderType.LIMIT,
            price=10000,
            qty=50,
            remaining=50,
            ts=1,
            owner="mm",
        )
    )

    # FOK buy 100 @ 10000 -> not enough depth (50 available), should reject without fills
    fok_order = Order(
        id=2,
        side=Side.BUY,
        type=OrderType.FOK,
        price=10000,
        qty=100,
        remaining=100,
        ts=2,
        owner="u",
    )
    trades = engine.submit(fok_order)
    assert len(trades) == 0
    assert fok_order.status == Status.REJECTED
    assert engine.book.best_ask == 10000

    # IOC buy 100 @ 10000 -> fills 50, cancels remainder 50
    ioc_order = Order(
        id=3,
        side=Side.BUY,
        type=OrderType.IOC,
        price=10000,
        qty=100,
        remaining=100,
        ts=3,
        owner="u",
    )
    trades = engine.submit(ioc_order)
    assert len(trades) == 1
    assert trades[0].qty == 50
    assert ioc_order.remaining == 0
    assert ioc_order.status == Status.PARTIAL
    assert engine.book.best_ask is None
    engine.check_invariants()


def test_post_only_order() -> None:
    engine = MatchingEngine()
    engine.submit(
        Order(
            id=1,
            side=Side.SELL,
            type=OrderType.LIMIT,
            price=10000,
            qty=50,
            remaining=50,
            ts=1,
            owner="mm",
        )
    )

    # Post-only buy at 10000 would cross best ask -> must be rejected
    po_order = Order(
        id=2,
        side=Side.BUY,
        type=OrderType.POST_ONLY,
        price=10000,
        qty=50,
        remaining=50,
        ts=2,
        owner="u",
    )
    trades = engine.submit(po_order)
    assert len(trades) == 0
    assert po_order.status == Status.REJECTED

    # Post-only buy at 9990 does not cross -> rests
    po_order2 = Order(
        id=3,
        side=Side.BUY,
        type=OrderType.POST_ONLY,
        price=9990,
        qty=50,
        remaining=50,
        ts=3,
        owner="u",
    )
    trades = engine.submit(po_order2)
    assert len(trades) == 0
    assert po_order2.status == Status.NEW
    assert engine.book.best_bid == 9990
    engine.check_invariants()


def test_cancel_order() -> None:
    engine = MatchingEngine()
    engine.submit(
        Order(
            id=1,
            side=Side.BUY,
            type=OrderType.LIMIT,
            price=9990,
            qty=100,
            remaining=100,
            ts=1,
            owner="u",
        )
    )
    assert engine.book.best_bid == 9990

    canceled = engine.cancel(1)
    assert canceled is not None
    assert canceled.status == Status.CANCELED
    assert canceled.remaining == 0
    assert engine.book.best_bid is None

    # Cancel unknown id returns None without crash
    assert engine.cancel(999) is None
    engine.check_invariants()


def test_modify_order() -> None:
    engine = MatchingEngine()
    # Two orders at 9990
    engine.submit(
        Order(
            id=1,
            side=Side.BUY,
            type=OrderType.LIMIT,
            price=9990,
            qty=100,
            remaining=100,
            ts=1,
            owner="u1",
        )
    )
    engine.submit(
        Order(
            id=2,
            side=Side.BUY,
            type=OrderType.LIMIT,
            price=9990,
            qty=100,
            remaining=100,
            ts=2,
            owner="u2",
        )
    )

    # Modify qty down: reduces remaining, keeps priority
    modified = engine.modify(1, new_qty=50)
    assert modified is not None
    assert modified.remaining == 50
    assert list(engine.book.bids[-9990])[0].id == 1

    # Modify price up: loses priority, moves to new price
    modified2 = engine.modify(1, new_price=9995)
    assert modified2 is not None
    assert engine.book.best_bid == 9995
    assert engine.book.bids[-9990][0].id == 2

    # Modify unknown id returns None
    assert engine.modify(999, new_qty=10) is None
    engine.check_invariants()


def test_market_order_on_empty_side() -> None:
    engine = MatchingEngine()
    # No asks in book
    order = Order(
        id=1,
        side=Side.BUY,
        type=OrderType.MARKET,
        price=None,
        qty=100,
        remaining=100,
        ts=1,
        owner="u",
    )
    trades = engine.submit(order)
    assert len(trades) == 0
    assert order.status == Status.CANCELED
    assert order.remaining == 0
    engine.check_invariants()


@given(
    actions=st.lists(
        st.tuples(
            st.sampled_from(["limit_buy", "limit_sell", "market_buy", "market_sell", "cancel"]),
            st.integers(min_value=9900, max_value=10100),
            st.integers(min_value=1, max_value=200),
        ),
        max_size=30,
    )
)
def test_hypothesis_matching_engine_invariants(actions: list[tuple[str, int, int]]) -> None:
    engine = MatchingEngine(tick_size=5, lot_size=1)
    order_id = 1
    active_ids: list[int] = []

    for action, raw_price, qty in actions:
        price = (raw_price // 5) * 5
        if price == 0:
            price = 5

        if action == "limit_buy":
            o = Order(
                id=order_id,
                side=Side.BUY,
                type=OrderType.LIMIT,
                price=price,
                qty=qty,
                remaining=qty,
                ts=order_id,
                owner="h",
            )
            engine.submit(o)
            if o.status in (Status.NEW, Status.PARTIAL):
                active_ids.append(order_id)
            order_id += 1
        elif action == "limit_sell":
            o = Order(
                id=order_id,
                side=Side.SELL,
                type=OrderType.LIMIT,
                price=price,
                qty=qty,
                remaining=qty,
                ts=order_id,
                owner="h",
            )
            engine.submit(o)
            if o.status in (Status.NEW, Status.PARTIAL):
                active_ids.append(order_id)
            order_id += 1
        elif action == "market_buy":
            o = Order(
                id=order_id,
                side=Side.BUY,
                type=OrderType.MARKET,
                price=None,
                qty=qty,
                remaining=qty,
                ts=order_id,
                owner="h",
            )
            engine.submit(o)
            order_id += 1
        elif action == "market_sell":
            o = Order(
                id=order_id,
                side=Side.SELL,
                type=OrderType.MARKET,
                price=None,
                qty=qty,
                remaining=qty,
                ts=order_id,
                owner="h",
            )
            engine.submit(o)
            order_id += 1
        elif action == "cancel":
            if active_ids:
                cid = active_ids.pop(0)
                engine.cancel(cid)

        engine.check_invariants()
