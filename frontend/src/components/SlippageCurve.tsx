"use client";

import {
  CartesianGrid,
  Line,
  LineChart,
  ReferenceDot,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { formatBps, formatShares } from "@/lib/format";

interface SlippageCurvePoint {
  size: number;
  slippageBps: number;
}

interface SlippageCurveProps {
  data: SlippageCurvePoint[];
  currentSize: number;
  currentSlippageBps: number | null;
}

export function SlippageCurve({
  data,
  currentSize,
  currentSlippageBps,
}: SlippageCurveProps) {
  if (!data || data.length === 0) {
    return (
      <div className="h-64 rounded-xl border border-neutral-800 bg-neutral-900/40 flex items-center justify-center text-neutral-400 text-xs font-mono">
        No curve points calculated
      </div>
    );
  }

  return (
    <div className="rounded-xl border border-neutral-800 bg-neutral-900/60 p-4 space-y-2">
      <div className="flex items-center justify-between text-xs font-mono">
        <h3 className="font-semibold text-neutral-200">Non-Linear Slippage vs Order Size Curve</h3>
        <span className="text-[11px] text-emerald-400 font-semibold">
          Current: {formatShares(currentSize)} shares &rarr; {formatBps(currentSlippageBps)}
        </span>
      </div>

      <div className="h-64 w-full">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={data} margin={{ top: 10, right: 20, left: 0, bottom: 0 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#262626" />
            <XAxis
              dataKey="size"
              stroke="#737373"
              fontSize={11}
              fontFamily="monospace"
              tickFormatter={(v) => formatShares(v)}
            />
            <YAxis
              stroke="#737373"
              fontSize={11}
              fontFamily="monospace"
              tickFormatter={(v) => `${v.toFixed(1)} bps`}
            />
            <Tooltip
              content={({ active, payload }) => {
                if (!active || !payload || !payload.length) return null;
                const d = payload[0].payload as SlippageCurvePoint;
                return (
                  <div className="rounded bg-neutral-900 border border-neutral-700 p-2.5 shadow-xl font-mono text-xs space-y-1">
                    <p className="text-neutral-300 font-bold">Size: {formatShares(d.size)} shares</p>
                    <p className="text-emerald-400 font-semibold">Slippage: {formatBps(d.slippageBps)}</p>
                  </div>
                );
              }}
            />
            <Line
              type="monotone"
              dataKey="slippageBps"
              stroke="#10b981"
              strokeWidth={2.5}
              dot={{ r: 3, fill: "#10b981" }}
              activeDot={{ r: 6 }}
            />
            {currentSlippageBps !== null && (
              <ReferenceDot
                x={currentSize}
                y={currentSlippageBps}
                r={6}
                fill="#fbbf24"
                stroke="#78350f"
                strokeWidth={2}
              />
            )}
          </LineChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
