"use client";

import { ImpactSimulateResponse } from "@/lib/api";
import { formatBps, formatShares } from "@/lib/format";
import { Info, Layers, Receipt } from "lucide-react";

interface ResultCardProps {
  result: ImpactSimulateResponse;
}

export function ResultCard({ result }: ResultCardProps) {
  const isBuy = result.side === "BUY";

  return (
    <div className="space-y-6 font-mono text-xs">
      {/* Primary Execution Metrics Card */}
      <div className="rounded-xl border border-neutral-800 bg-neutral-900/60 p-5 space-y-4">
        <div className="flex items-center justify-between border-b border-neutral-800 pb-3">
          <div className="flex items-center gap-2">
            <span
              className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                isBuy ? "bg-emerald-500/20 text-emerald-400 border border-emerald-500/30" : "bg-rose-500/20 text-rose-400 border border-rose-500/30"
              }`}
            >
              {result.side}
            </span>
            <h3 className="font-semibold text-neutral-100 text-sm">
              Hypothetical Execution Outcome
            </h3>
          </div>
          <span className="text-[11px] text-neutral-400">
            {result.mode.toUpperCase()} MODE
          </span>
        </div>

        {/* Highlight Stats Grid */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
          <div className="p-3 rounded-lg bg-neutral-950/80 border border-neutral-800/80 space-y-1">
            <span className="text-[10px] text-neutral-400 uppercase">Avg Fill Price</span>
            <p className="text-base font-bold text-neutral-100">
              {result.avg_price_formatted}
            </p>
          </div>
          <div className="p-3 rounded-lg bg-neutral-950/80 border border-neutral-800/80 space-y-1">
            <span className="text-[10px] text-neutral-400 uppercase">Slippage vs Mid</span>
            <p className="text-base font-bold text-amber-400">
              {formatBps(result.slippage_bps)}
            </p>
          </div>
          <div className="p-3 rounded-lg bg-neutral-950/80 border border-neutral-800/80 space-y-1">
            <span className="text-[10px] text-neutral-400 uppercase">Price Impact</span>
            <p className="text-base font-bold text-rose-400">
              {formatBps(result.price_impact_bps)}
            </p>
          </div>
          <div className="p-3 rounded-lg bg-neutral-950/80 border border-neutral-800/80 space-y-1">
            <span className="text-[10px] text-neutral-400 uppercase">Total Notional</span>
            <p className="text-base font-bold text-emerald-400">
              {result.total_notional_formatted}
            </p>
          </div>
        </div>

        {/* Detailed Benchmarks */}
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 pt-2 text-neutral-300">
          <div className="flex justify-between py-1 border-b border-neutral-800/50">
            <span className="text-neutral-400">Arrival Best ({isBuy ? "Ask" : "Bid"}):</span>
            <span className="font-semibold">{result.arrival_best_formatted}</span>
          </div>
          <div className="flex justify-between py-1 border-b border-neutral-800/50">
            <span className="text-neutral-400">Arrival Mid Price:</span>
            <span className="font-semibold">{result.arrival_mid_formatted}</span>
          </div>
          <div className="flex justify-between py-1 border-b border-neutral-800/50">
            <span className="text-neutral-400">Slippage vs Best:</span>
            <span className="font-semibold">{result.slippage_vs_best_formatted} / share</span>
          </div>
          <div className="flex justify-between py-1 border-b border-neutral-800/50">
            <span className="text-neutral-400">Post-Trade Mid:</span>
            <span className="font-semibold">{result.post_mid_formatted}</span>
          </div>
          <div className="flex justify-between py-1 border-b border-neutral-800/50">
            <span className="text-neutral-400">Filled / Requested:</span>
            <span className="font-semibold text-emerald-400">
              {formatShares(result.filled_qty)} / {formatShares(result.requested_qty)} (
              {(result.fill_ratio * 100).toFixed(1)}%)
            </span>
          </div>
          <div className="flex justify-between py-1 border-b border-neutral-800/50">
            <span className="text-neutral-400">Levels Consumed:</span>
            <span className="font-semibold">{result.levels_consumed} levels</span>
          </div>
        </div>
      </div>

      {/* Levels Consumed Breakdown Table */}
      {result.level_fills && result.level_fills.length > 0 && (
        <div className="rounded-xl border border-neutral-800 bg-neutral-900/60 overflow-hidden">
          <div className="p-3 bg-neutral-900 border-b border-neutral-800 flex items-center justify-between">
            <h4 className="font-semibold text-neutral-200 flex items-center gap-1.5">
              <Layers className="w-4 h-4 text-emerald-400" /> Walked Price Levels
            </h4>
            <span className="text-[11px] text-neutral-400">
              {result.level_fills.length} levels touched
            </span>
          </div>

          <div className="grid grid-cols-4 px-3 py-2 bg-neutral-950/60 font-semibold text-neutral-400 border-b border-neutral-800/80 text-[11px]">
            <div>Level Price</div>
            <div className="text-right">Shares Filled</div>
            <div className="text-right">Level Notional</div>
            <div className="text-right">Cum Qty</div>
          </div>

          <div className="divide-y divide-neutral-900/40">
            {result.level_fills.map((lf, i) => {
              const cumShares = result.level_fills
                .slice(0, i + 1)
                .reduce((acc, curr) => acc + curr.qty, 0);
              return (
                <div
                  key={`lvl-${lf.price}`}
                  className="grid grid-cols-4 px-3 py-1.5 items-center hover:bg-neutral-800/40"
                >
                  <span className="font-bold text-neutral-200">{lf.price_formatted}</span>
                  <span className="text-right text-emerald-400">
                    {formatShares(lf.qty)}
                  </span>
                  <span className="text-right text-neutral-300">
                    {lf.notional_formatted}
                  </span>
                  <span className="text-right text-neutral-400">
                    {formatShares(cumShares)}
                  </span>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* Itemized Indian Trading Charges Breakdown */}
      <div className="rounded-xl border border-neutral-800 bg-neutral-900/60 p-5 space-y-4">
        <div className="flex items-center justify-between border-b border-neutral-800 pb-3">
          <h4 className="font-semibold text-neutral-200 flex items-center gap-1.5">
            <Receipt className="w-4 h-4 text-amber-400" /> Statutory &amp; Brokerage Charges
          </h4>
          <span className="text-[10px] px-2 py-0.5 rounded bg-amber-500/10 text-amber-400 border border-amber-500/20">
            Schedule As Of: {result.charges.as_of}
          </span>
        </div>

        <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
          <div className="p-2.5 rounded bg-neutral-950/60 border border-neutral-800/60">
            <span className="text-[10px] text-neutral-400">Brokerage</span>
            <p className="font-bold text-neutral-200">{result.charges.brokerage_formatted}</p>
          </div>
          <div className="p-2.5 rounded bg-neutral-950/60 border border-neutral-800/60">
            <span className="text-[10px] text-neutral-400">STT / CTT</span>
            <p className="font-bold text-neutral-200">{result.charges.stt_formatted}</p>
          </div>
          <div className="p-2.5 rounded bg-neutral-950/60 border border-neutral-800/60">
            <span className="text-[10px] text-neutral-400">Exchange Txn Fee</span>
            <p className="font-bold text-neutral-200">
              {result.charges.exchange_txn_fee_formatted}
            </p>
          </div>
          <div className="p-2.5 rounded bg-neutral-950/60 border border-neutral-800/60">
            <span className="text-[10px] text-neutral-400">SEBI Turnover Fee</span>
            <p className="font-bold text-neutral-200">{result.charges.sebi_fee_formatted}</p>
          </div>
          <div className="p-2.5 rounded bg-neutral-950/60 border border-neutral-800/60">
            <span className="text-[10px] text-neutral-400">Stamp Duty</span>
            <p className="font-bold text-neutral-200">{result.charges.stamp_duty_formatted}</p>
          </div>
          <div className="p-2.5 rounded bg-neutral-950/60 border border-neutral-800/60">
            <span className="text-[10px] text-neutral-400">GST (18%)</span>
            <p className="font-bold text-neutral-200">{result.charges.gst_formatted}</p>
          </div>
        </div>

        <div className="pt-2 border-t border-neutral-800/80 flex items-center justify-between text-sm font-bold">
          <span className="text-neutral-300">Total Statutory &amp; Broker Charges:</span>
          <span className="text-amber-400">{result.charges.total_charges_formatted}</span>
        </div>

        {/* All-in execution total */}
        <div className="p-3.5 rounded-lg bg-emerald-950/30 border border-emerald-500/20 flex items-center justify-between text-sm font-bold">
          <span className="text-emerald-200">
            All-In Execution Cost (Shortfall + Charges):
          </span>
          <span className="text-emerald-400 text-base">{result.all_in_cost_formatted}</span>
        </div>
      </div>

      {/* Regulatory Disclaimer */}
      <div className="p-3.5 rounded-lg bg-amber-950/20 border border-amber-500/20 flex items-start gap-2.5 text-[11px] text-amber-200/80 leading-relaxed">
        <Info className="w-4 h-4 text-amber-400 shrink-0 mt-0.5" />
        <span>{result.disclaimer}</span>
      </div>
    </div>
  );
}
