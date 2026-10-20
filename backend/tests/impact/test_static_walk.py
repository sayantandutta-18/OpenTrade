"""Tests for static order book walk impact calculations."""

from hypothesis import given
from hypothesis import strategies as st

from impactlab.engine.book import OrderBook
from impactlab.engine.models import Order, OrderType, Side
from impactlab.impact.metrics import SizeMode
from impactlab.impact.static_walk import walk_book


def make_reference_book() -> OrderBook:
    book = OrderBook()
    for oid, price, qty in [(1, 10000, 100), (2, 10010, 200), (3, 10020, 300)]:
        book.add_resting(
            Order(
                id=oid,
                side=Side.SELL,
                type=OrderType.LIMIT,
                price=price,
                qty=qty,
                remaining=qty,
                ts=oid,
                owner="mm",
            )
        )
    for oid, price, qty in [(4, 9990, 100), (5, 9980, 200), (6, 9970, 300)]:
        book.add_resting(
            Order(
                id=oid,
                side=Side.BUY,
                type=OrderType.LIMIT,
                price=price,
                qty=qty,
                remaining=qty,
                ts=oid,
                owner="mm",
            )
        )
    return book


def test_reference_example_static_walk() -> None:
    book = make_reference_book()
    snap = book.snapshot()

    res = walk_book(snap, side=Side.BUY, size=400, mode=SizeMode.SHARES)

    assert res.filled_qty == 400
    assert res.unfilled_qty == 0
    assert res.fill_ratio == 1.0
    assert res.total_notional == 4_004_000  # Rs 40,040
    assert res.avg_price == 10010.0  # Rs 100.10
    assert res.arrival_best == 10000
    assert res.arrival_mid == 9995.0
    assert res.slippage_vs_best == 10.0  # Rs 0.10 / share
    assert res.slippage_vs_mid == 15.0  # includes half-spread 5 paise
    assert res.levels_consumed == 3
    assert len(res.level_fills) == 3
    assert res.level_fills[0].qty == 100 and res.level_fills[0].price == 10000
    assert res.level_fills[1].qty == 200 and res.level_fills[1].price == 10010
    assert res.level_fills[2].qty == 100 and res.level_fills[2].price == 10020


def test_rupee_mode_static_walk() -> None:
    book = make_reference_book()
    snap = book.snapshot()

    # Budget Rs 40,040 should exactly buy 400 shares
    res = walk_book(snap, side=Side.BUY, size=40040, mode=SizeMode.RUPEES)
    assert res.filled_qty == 400
    assert res.total_notional == 4_004_000
    assert res.avg_price == 10010.0


def test_sell_static_walk() -> None:
    book = make_reference_book()
    snap = book.snapshot()

    res = walk_book(snap, side=Side.SELL, size=400, mode=SizeMode.SHARES)
    assert res.filled_qty == 400
    assert res.total_notional == 3_992_000  # Rs 39,920
    assert res.avg_price == 9980.0  # Rs 99.80
    assert res.arrival_best == 9990
    assert res.slippage_vs_best == 10.0
    assert res.levels_consumed == 3


def test_size_exceeds_book_depth() -> None:
    book = make_reference_book()
    snap = book.snapshot()

    # Total asks depth is 600 shares, request 1000 shares
    res = walk_book(snap, side=Side.BUY, size=1000, mode=SizeMode.SHARES)
    assert res.requested_qty == 1000
    assert res.filled_qty == 600
    assert res.unfilled_qty == 400
    assert res.fill_ratio == 0.6
    assert res.levels_consumed == 3


def test_empty_book_walk() -> None:
    book = OrderBook()
    snap = book.snapshot()

    res = walk_book(snap, side=Side.BUY, size=100, mode=SizeMode.SHARES)
    assert res.filled_qty == 0
    assert res.unfilled_qty == 100
    assert res.avg_price is None
    assert res.fill_ratio == 0.0


@given(
    step_sizes=st.lists(
        st.integers(min_value=1, max_value=100),
        min_size=2,
        max_size=5,
    )
)
def test_hypothesis_slippage_curve_non_decreasing(step_sizes: list[int]) -> None:
    book = make_reference_book()
    snap = book.snapshot()

    # Generate strictly increasing order sizes
    sizes: list[int] = []
    curr = 10
    for step in step_sizes:
        curr += step
        sizes.append(curr)

    prev_slippage = -1.0
    for s in sizes:
        res = walk_book(snap, side=Side.BUY, size=s, mode=SizeMode.SHARES)
        if res.slippage_vs_best is not None:
            assert res.slippage_vs_best >= prev_slippage - 1e-9, (
                f"Slippage decreased from {prev_slippage} to {res.slippage_vs_best} at size {s}"
            )
            prev_slippage = res.slippage_vs_best
