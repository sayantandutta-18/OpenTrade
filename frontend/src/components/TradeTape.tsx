"use client";

import { TradeSchema } from "@/lib/api";
import { formatPrice, formatShares } from "@/lib/format";

interface TradeTapeProps {
  trades: TradeSchema[];
}

export function TradeTape({ trades }: TradeTapeProps) {
  const displayTrades = [...trades].slice(-15).reverse();

  return (
    <div className="rounded-xl border border-neutral-800 bg-neutral-900/60 overflow-hidden font-mono text-xs">
      <div className="p-3 bg-neutral-900 border-b border-neutral-800 flex items-center justify-between">
        <h3 className="font-semibold text-neutral-200">Execution Trade Tape</h3>
        <span className="text-[11px] text-neutral-400">Recent Fills</span>
      </div>

      <div className="grid grid-cols-4 px-3 py-2 bg-neutral-950/60 text-[11px] font-semibold text-neutral-400 border-b border-neutral-800/80">
        <div>Side</div>
        <div className="text-right">Price</div>
        <div className="text-right">Qty</div>
        <div className="text-right">Total</div>
      </div>

      <div className="divide-y divide-neutral-900/40 max-h-64 overflow-y-auto">
        {displayTrades.length === 0 ? (
          <div className="py-8 text-center text-neutral-400">No trades executed yet</div>
        ) : (
          displayTrades.map((t) => {
            const isBuy = t.taker_side === "BUY";
            const totalPaise = t.price * t.qty;
            return (
              <div
                key={`trade-${t.id}`}
                className="grid grid-cols-4 px-3 py-1.5 items-center hover:bg-neutral-800/40 transition-colors"
              >
                <span
                  className={`font-bold flex items-center gap-1 ${
                    isBuy ? "text-emerald-400" : "text-rose-400"
                  }`}
                >
                  {isBuy ? "BUY" : "SELL"}
                </span>
                <span className="text-right font-medium text-neutral-200">
                  {formatPrice(t.price)}
                </span>
                <span className="text-right text-neutral-300">
                  {formatShares(t.qty)}
                </span>
                <span className="text-right text-neutral-400 text-[11px]">
                  {formatPrice(totalPaise)}
                </span>
              </div>
            );
          })
        )}
      </div>
    </div>
  );
}
