"""Tests for the Indian trading charges calculator."""

from impactlab.charges.calculator import ChargesCalculator
from impactlab.engine.models import Side

FIXTURE_CONFIG = {
    "as_of": "2024-04-01",
    "source_note": "Test fixture rates",
    "equity_delivery": {
        "brokerage": {"type": "flat", "value": 2000},  # Rs 20
        "stt": {"buy_pct": 0.001, "sell_pct": 0.001},  # 0.1%
        "exchange_txn_pct": 0.00003,  # 0.003%
        "sebi_fee_per_crore_paise": 1000,  # Rs 10 per crore
        "stamp_duty_buy_pct": 0.00015,  # 0.015%
        "gst_pct": 0.18,
    },
    "equity_intraday": {
        "brokerage": {"type": "flat", "value": 2000},
        "stt": {"buy_pct": 0.0, "sell_pct": 0.00025},  # STT only on sell
        "exchange_txn_pct": 0.00003,
        "sebi_fee_per_crore_paise": 1000,
        "stamp_duty_buy_pct": 0.00003,
        "gst_pct": 0.18,
    },
}


def test_default_charges_yaml_loads() -> None:
    calc = ChargesCalculator()
    assert calc.as_of == "2024-04-01"
    assert "Verify current official rates" in calc.source_note

    # Calculate on Rs 1,00,000 (10,000,000 paise)
    res = calc.calculate(side=Side.BUY, notional=10_000_000, product_type="equity_delivery")
    assert res.total_charges > 0
    assert isinstance(res.brokerage, int)
    assert isinstance(res.stt, int)
    assert isinstance(res.exchange_txn_fee, int)
    assert isinstance(res.stamp_duty, int)
    assert isinstance(res.gst, int)
    assert res.total_charges == (
        res.brokerage + res.stt + res.exchange_txn_fee + res.sebi_fee + res.stamp_duty + res.gst
    )


def test_fixture_delivery_buy() -> None:
    calc = ChargesCalculator(FIXTURE_CONFIG)
    # Notional: Rs 10,000 = 1,000,000 paise
    notional = 1_000_000
    res = calc.calculate(side=Side.BUY, notional=notional, product_type="equity_delivery")

    assert res.brokerage == 2000  # Rs 20
    assert res.stt == 1000  # 0.1% of 1,000,000 = 1000 paise (Rs 10)
    assert res.exchange_txn_fee == 30  # 0.003% of 1,000,000 = 30 paise
    assert res.sebi_fee == 1  # 1,000,000 / 10^9 * 1000 = 1 paise
    assert res.stamp_duty == 150  # 0.015% of 1,000,000 = 150 paise
    # GST: 18% on (2000 + 30 + 1) = 366 paise
    assert res.gst == int(round((2000 + 30 + 1) * 0.18))
    assert res.total_charges == 2000 + 1000 + 30 + 1 + 150 + res.gst


def test_fixture_delivery_sell_no_stamp_duty() -> None:
    calc = ChargesCalculator(FIXTURE_CONFIG)
    notional = 1_000_000
    res = calc.calculate(side=Side.SELL, notional=notional, product_type="equity_delivery")

    assert res.stamp_duty == 0  # stamp duty only on buy
    assert res.stt == 1000  # delivery STT on sell too


def test_fixture_intraday_buy_no_stt() -> None:
    calc = ChargesCalculator(FIXTURE_CONFIG)
    notional = 1_000_000
    res = calc.calculate(side=Side.BUY, notional=notional, product_type="equity_intraday")

    assert res.stt == 0  # intraday has no STT on buy
    assert res.stamp_duty == 30  # 0.003% of 1,000,000 = 30 paise
