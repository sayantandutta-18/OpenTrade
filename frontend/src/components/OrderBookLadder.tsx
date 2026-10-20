"use client";

import { LevelSchema } from "@/lib/api";
import { formatPrice, formatShares } from "@/lib/format";

interface OrderBookLadderProps {
  bids: LevelSchema[];
  asks: LevelSchema[];
  spread: number | null;
  spreadFormatted: string;
  midFormatted: string;
  tickSize?: number;
}

export function OrderBookLadder({
  bids,
  asks,
  spread,
  spreadFormatted,
  midFormatted,
  tickSize = 5,
}: OrderBookLadderProps) {
  const maxQty = Math.max(
    ...bids.map((b) => b.qty),
    ...asks.map((a) => a.qty),
    1
  );

  // Show top asks in reverse order (highest ask at top, lowest/best ask at bottom)
  const displayAsks = [...asks].slice(0, 10).reverse();
  const displayBids = bids.slice(0, 10);

  const spreadTicks = spread !== null ? Math.round(spread / tickSize) : 0;

  return (
    <div className="rounded-xl border border-neutral-800 bg-neutral-900/60 overflow-hidden font-mono text-xs">
      <div className="p-3 bg-neutral-900 border-b border-neutral-800 flex items-center justify-between">
        <h3 className="font-semibold text-neutral-200">Order Book Depth Ladder</h3>
        <span className="text-[11px] text-neutral-400">Price-Time FIFO Priority</span>
      </div>

      <div className="grid grid-cols-4 px-3 py-2 bg-neutral-950/60 text-[11px] font-semibold text-neutral-400 border-b border-neutral-800/80">
        <div>Side</div>
        <div className="text-right">Price</div>
        <div className="text-right">Qty</div>
        <div className="text-right">Depth %</div>
      </div>

      {/* Asks (Sell Orders) */}
      <div className="divide-y divide-neutral-900/40">
        {displayAsks.length === 0 ? (
          <div className="py-6 text-center text-neutral-400">No resting asks</div>
        ) : (
          displayAsks.map((lvl) => {
            const depthPct = Math.min(100, (lvl.qty / maxQty) * 100);
            return (
              <div
                key={`ask-${lvl.price}`}
                className="relative grid grid-cols-4 px-3 py-1.5 items-center hover:bg-rose-950/20 transition-colors"
              >
                <div
                  className="absolute right-0 top-0 bottom-0 bg-rose-500/10 pointer-events-none"
                  style={{ width: `${depthPct}%` }}
                />
                <span className="text-rose-400 font-bold flex items-center gap-1">
                  ▲ ASK
                </span>
                <span className="text-right font-medium text-rose-300">
                  {formatPrice(lvl.price)}
                </span>
                <span className="text-right text-neutral-200">
                  {formatShares(lvl.qty)}
                </span>
                <span className="text-right text-neutral-400 text-[10px]">
                  {depthPct.toFixed(0)}%
                </span>
              </div>
            );
          })
        )}
      </div>

      {/* Spread & Mid Price Bar */}
      <div className="py-2.5 px-3 bg-neutral-950/90 border-y border-neutral-800 flex items-center justify-between text-xs font-semibold">
        <div className="flex items-center gap-2">
          <span className="text-neutral-400">SPREAD:</span>
          <span className="text-amber-400 font-bold">{spreadFormatted}</span>
          <span className="text-[10px] text-neutral-400 font-normal">
            ({spreadTicks} ticks)
          </span>
        </div>
        <div className="flex items-center gap-2">
          <span className="text-neutral-400">MID:</span>
          <span className="text-emerald-400 font-bold">{midFormatted}</span>
        </div>
      </div>

      {/* Bids (Buy Orders) */}
      <div className="divide-y divide-neutral-900/40">
        {displayBids.length === 0 ? (
          <div className="py-6 text-center text-neutral-400">No resting bids</div>
        ) : (
          displayBids.map((lvl) => {
            const depthPct = Math.min(100, (lvl.qty / maxQty) * 100);
            return (
              <div
                key={`bid-${lvl.price}`}
                className="relative grid grid-cols-4 px-3 py-1.5 items-center hover:bg-emerald-950/20 transition-colors"
              >
                <div
                  className="absolute right-0 top-0 bottom-0 bg-emerald-500/10 pointer-events-none"
                  style={{ width: `${depthPct}%` }}
                />
                <span className="text-emerald-400 font-bold flex items-center gap-1">
                  ▼ BID
                </span>
                <span className="text-right font-medium text-emerald-300">
                  {formatPrice(lvl.price)}
                </span>
                <span className="text-right text-neutral-200">
                  {formatShares(lvl.qty)}
                </span>
                <span className="text-right text-neutral-400 text-[10px]">
                  {depthPct.toFixed(0)}%
                </span>
              </div>
            );
          })
        )}
      </div>
    </div>
  );
}
