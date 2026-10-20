"use client";

import { useMemo } from "react";
import {
  Area,
  AreaChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { LevelSchema } from "@/lib/api";
import { formatPrice, formatShares } from "@/lib/format";

interface DepthChartProps {
  bids: LevelSchema[];
  asks: LevelSchema[];
}

export function DepthChart({ bids, asks }: DepthChartProps) {
  const chartData = useMemo(() => {
    // Cumulative bids: from lowest price up to best bid
    let cumBid = 0;
    const sortedBids = [...bids].reverse(); // lowest to highest
    const bidPoints = sortedBids.map((b) => {
      cumBid += b.qty;
      return {
        pricePaise: b.price,
        priceRs: (b.price / 100).toFixed(2),
        bidDepth: cumBid,
        askDepth: null,
      };
    });

    // Cumulative asks: from best ask up to highest price
    let cumAsk = 0;
    const sortedAsks = [...asks]; // lowest to highest
    const askPoints = sortedAsks.map((a) => {
      cumAsk += a.qty;
      return {
        pricePaise: a.price,
        priceRs: (a.price / 100).toFixed(2),
        bidDepth: null,
        askDepth: cumAsk,
      };
    });

    return [...bidPoints, ...askPoints];
  }, [bids, asks]);

  if (chartData.length === 0) {
    return (
      <div className="h-64 rounded-xl border border-neutral-800 bg-neutral-900/40 flex items-center justify-center text-neutral-400 text-sm">
        No depth data available
      </div>
    );
  }

  return (
    <div className="rounded-xl border border-neutral-800 bg-neutral-900/60 p-4 space-y-2">
      <div className="flex items-center justify-between text-xs font-mono">
        <h3 className="font-semibold text-neutral-200">Cumulative Market Depth</h3>
        <div className="flex items-center gap-4 text-[11px]">
          <span className="flex items-center gap-1.5 text-emerald-400">
            <span className="w-2.5 h-2.5 rounded-full bg-emerald-500 inline-block" /> Bids (Buy Depth)
          </span>
          <span className="flex items-center gap-1.5 text-rose-400">
            <span className="w-2.5 h-2.5 rounded-full bg-rose-500 inline-block" /> Asks (Sell Depth)
          </span>
        </div>
      </div>

      <div className="h-64 w-full">
        <ResponsiveContainer width="100%" height="100%">
          <AreaChart data={chartData} margin={{ top: 10, right: 10, left: 0, bottom: 0 }}>
            <XAxis
              dataKey="priceRs"
              stroke="#525252"
              fontSize={11}
              fontFamily="monospace"
              tickFormatter={(v) => `₹${v}`}
            />
            <YAxis
              stroke="#525252"
              fontSize={11}
              fontFamily="monospace"
              tickFormatter={(v) => formatShares(v)}
            />
            <Tooltip
              content={({ active, payload }) => {
                if (!active || !payload || !payload.length) return null;
                const d = payload[0].payload;
                return (
                  <div className="rounded bg-neutral-900 border border-neutral-700 p-2 shadow-xl font-mono text-xs space-y-1">
                    <p className="font-bold text-neutral-200">Price: {formatPrice(d.pricePaise)}</p>
                    {d.bidDepth !== null && (
                      <p className="text-emerald-400">Bid Depth: {formatShares(d.bidDepth)} shares</p>
                    )}
                    {d.askDepth !== null && (
                      <p className="text-rose-400">Ask Depth: {formatShares(d.askDepth)} shares</p>
                    )}
                  </div>
                );
              }}
            />
            <Area
              type="stepAfter"
              dataKey="bidDepth"
              stroke="#10b981"
              fill="#10b981"
              fillOpacity={0.2}
              strokeWidth={2}
            />
            <Area
              type="stepBefore"
              dataKey="askDepth"
              stroke="#f43f5e"
              fill="#f43f5e"
              fillOpacity={0.2}
              strokeWidth={2}
            />
          </AreaChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
