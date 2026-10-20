"""Indian statutory and broker trading charges calculator.

All money values in inputs and outputs are in integer paise (Rs 1.00 = 100 paise).
Charges configuration is loaded from charges.yaml with an as_of audit date.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from impactlab.engine.models import Side


@dataclass(frozen=True, slots=True)
class ChargesBreakdown:
    """Itemized breakdown of Indian equity trading charges."""

    product_type: str  # equity_delivery | equity_intraday
    side: Side
    notional: int  # trade value in paise
    brokerage: int  # brokerage in paise
    stt: int  # Securities Transaction Tax in paise
    exchange_txn_fee: int  # Exchange transaction turnover fee in paise
    sebi_fee: int  # SEBI turnover fee in paise
    stamp_duty: int  # Stamp duty in paise (buy side only)
    gst: int  # Goods and Services Tax in paise
    total_charges: int  # sum of all charges in paise
    as_of: str  # effective date of the charges schedule
    source_note: str  # regulatory/broker disclaimer note


class ChargesCalculator:
    """Calculates Indian regulatory and brokerage fees for equity trades."""

    __slots__ = ("_config", "_as_of", "_source_note")

    def __init__(self, config_or_path: dict[str, Any] | str | Path | None = None) -> None:
        if config_or_path is None:
            # Default to bundled charges.yaml
            default_path = Path(__file__).parent / "charges.yaml"
            with open(default_path, encoding="utf-8") as f:
                self._config: dict[str, Any] = yaml.safe_load(f)
        elif isinstance(config_or_path, (str, Path)):
            with open(config_or_path, encoding="utf-8") as f:
                self._config = yaml.safe_load(f)
        else:
            self._config = dict(config_or_path)

        self._as_of = str(self._config.get("as_of", "unknown"))
        self._source_note = str(self._config.get("source_note", ""))

    @property
    def as_of(self) -> str:
        """Effective schedule date."""
        return self._as_of

    @property
    def source_note(self) -> str:
        """Informational note."""
        return self._source_note

    def calculate(
        self,
        side: Side,
        notional: int,
        product_type: str = "equity_delivery",
    ) -> ChargesBreakdown:
        """Compute itemized charges for a trade notional.

        Args:
            side: BUY or SELL.
            notional: Order value in paise.
            product_type: 'equity_delivery' or 'equity_intraday'.

        Returns:
            ChargesBreakdown with each fee component and total in paise.
        """
        cfg = self._config.get(product_type, self._config.get("equity_delivery", {}))

        # 1. Brokerage
        brok_cfg = cfg.get("brokerage", {})
        brok_type = brok_cfg.get("type", "flat")
        if brok_type == "percent":
            brok_val = int(round(notional * brok_cfg.get("value", 0.0)))
            max_cap = brok_cfg.get("max_cap_paise")
            if max_cap is not None:
                brok_val = min(brok_val, int(max_cap))
        else:
            brok_val = int(round(brok_cfg.get("value", 0.0)))

        # 2. STT (Securities Transaction Tax)
        stt_cfg = cfg.get("stt", {})
        stt_pct = stt_cfg.get("buy_pct", 0.0) if side == Side.BUY else stt_cfg.get("sell_pct", 0.0)
        stt_val = int(round(notional * stt_pct))

        # 3. Exchange transaction fee
        txn_pct = cfg.get("exchange_txn_pct", 0.0)
        txn_fee = int(round(notional * txn_pct))

        # 4. SEBI turnover fee (1 crore = 10^7 rupees = 10^9 paise)
        sebi_per_crore = cfg.get("sebi_fee_per_crore_paise", 0)
        sebi_fee = int(round((notional / 1_000_000_000.0) * sebi_per_crore))

        # 5. Stamp duty (applies on buy trades)
        if side == Side.BUY:
            stamp_pct = cfg.get("stamp_duty_buy_pct", 0.0)
            stamp_duty = int(round(notional * stamp_pct))
        else:
            stamp_duty = 0

        # 6. GST on (brokerage + exchange txn fee + SEBI fee)
        taxable_services = brok_val + txn_fee + sebi_fee
        gst_pct = cfg.get("gst_pct", 0.18)
        gst = int(round(taxable_services * gst_pct))

        # Total
        total = brok_val + stt_val + txn_fee + sebi_fee + stamp_duty + gst

        return ChargesBreakdown(
            product_type=product_type,
            side=side,
            notional=notional,
            brokerage=brok_val,
            stt=stt_val,
            exchange_txn_fee=txn_fee,
            sebi_fee=sebi_fee,
            stamp_duty=stamp_duty,
            gst=gst,
            total_charges=total,
            as_of=self._as_of,
            source_note=self._source_note,
        )
