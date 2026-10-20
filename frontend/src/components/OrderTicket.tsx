"use client";

import { useState } from "react";
import { OrderSubmitResponse } from "@/lib/api";

interface OrderTicketProps {
  onSubmit: (order: {
    side: "BUY" | "SELL";
    type: string;
    qty: number;
    price?: number;
  }) => Promise<OrderSubmitResponse>;
  bestBid: number | null;
  bestAsk: number | null;
  tickSize?: number;
}

export function OrderTicket({
  onSubmit,
  bestBid,
  bestAsk,
  tickSize = 5,
}: OrderTicketProps) {
  const [side, setSide] = useState<"BUY" | "SELL">("BUY");
  const [orderType, setOrderType] = useState<string>("LIMIT");
  const [qty, setQty] = useState<string>("100");
  const [priceRs, setPriceRs] = useState<string>(
    bestAsk ? (bestAsk / 100).toFixed(2) : "100.00"
  );
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [lastResult, setLastResult] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    const qtyNum = parseInt(qty, 10);
    if (isNaN(qtyNum) || qtyNum <= 0) return;

    let pricePaise: number | undefined;
    if (orderType !== "MARKET") {
      const pNum = parseFloat(priceRs);
      if (isNaN(pNum) || pNum <= 0) return;
      pricePaise = Math.round(pNum * 100);
      // Snap to tick
      pricePaise = Math.round(pricePaise / tickSize) * tickSize;
    }

    try {
      setIsSubmitting(true);
      setLastResult(null);
      const res = await onSubmit({
        side,
        type: orderType,
        qty: qtyNum,
        price: pricePaise,
      });
      setLastResult(
        `Order #${res.order_id} ${res.status}: ${res.filled_qty} shares filled`
      );
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Order failed";
      setLastResult(`Error: ${msg}`);
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <form
      onSubmit={handleSubmit}
      className="rounded-xl border border-neutral-800 bg-neutral-900/60 p-4 space-y-4 font-mono text-xs"
    >
      <div className="flex items-center justify-between border-b border-neutral-800 pb-3">
        <h3 className="font-semibold text-neutral-200">Interactive Order Ticket</h3>
        <span className="text-[10px] text-neutral-400">Direct Engine Placement</span>
      </div>

      {/* Side Toggle */}
      <div className="grid grid-cols-2 gap-2">
        <button
          type="button"
          onClick={() => setSide("BUY")}
          className={`py-2 rounded-lg font-bold text-center transition-all ${
            side === "BUY"
              ? "bg-emerald-500 text-neutral-950 shadow-md shadow-emerald-500/20"
              : "bg-neutral-800/80 text-neutral-400 hover:text-neutral-200"
          }`}
        >
          BUY
        </button>
        <button
          type="button"
          onClick={() => setSide("SELL")}
          className={`py-2 rounded-lg font-bold text-center transition-all ${
            side === "SELL"
              ? "bg-rose-500 text-neutral-950 shadow-md shadow-rose-500/20"
              : "bg-neutral-800/80 text-neutral-400 hover:text-neutral-200"
          }`}
        >
          SELL
        </button>
      </div>

      {/* Order Type */}
      <div>
        <label className="text-[11px] text-neutral-400 block mb-1">Order Type</label>
        <select
          value={orderType}
          onChange={(e) => setOrderType(e.target.value)}
          className="w-full bg-neutral-950 border border-neutral-800 rounded-lg px-3 py-2 text-neutral-200 focus:outline-none focus:border-emerald-500"
        >
          <option value="LIMIT">LIMIT (Price-Time Priority)</option>
          <option value="MARKET">MARKET (Immediate Taker)</option>
          <option value="IOC">IOC (Immediate-or-Cancel)</option>
          <option value="FOK">FOK (Fill-or-Kill)</option>
          <option value="POST_ONLY">POST_ONLY (Maker Only)</option>
        </select>
      </div>

      {/* Quantity */}
      <div>
        <label className="text-[11px] text-neutral-400 block mb-1">Quantity (Shares)</label>
        <input
          type="number"
          min="1"
          step="1"
          value={qty}
          onChange={(e) => setQty(e.target.value)}
          className="w-full bg-neutral-950 border border-neutral-800 rounded-lg px-3 py-2 text-neutral-200 focus:outline-none focus:border-emerald-500"
          required
        />
      </div>

      {/* Limit Price */}
      {orderType !== "MARKET" && (
        <div>
          <div className="flex justify-between items-center mb-1">
            <label className="text-[11px] text-neutral-400">Limit Price (₹)</label>
            <div className="flex gap-2 text-[10px]">
              {bestBid && (
                <button
                  type="button"
                  onClick={() => setPriceRs((bestBid / 100).toFixed(2))}
                  className="text-emerald-400 hover:underline"
                >
                  Bid: ₹{(bestBid / 100).toFixed(2)}
                </button>
              )}
              {bestAsk && (
                <button
                  type="button"
                  onClick={() => setPriceRs((bestAsk / 100).toFixed(2))}
                  className="text-rose-400 hover:underline"
                >
                  Ask: ₹{(bestAsk / 100).toFixed(2)}
                </button>
              )}
            </div>
          </div>
          <input
            type="number"
            min="0.05"
            step="0.05"
            value={priceRs}
            onChange={(e) => setPriceRs(e.target.value)}
            className="w-full bg-neutral-950 border border-neutral-800 rounded-lg px-3 py-2 text-neutral-200 focus:outline-none focus:border-emerald-500"
            required
          />
        </div>
      )}

      {/* Submit Button */}
      <button
        type="submit"
        disabled={isSubmitting}
        className={`w-full py-2.5 rounded-lg font-bold transition-all ${
          side === "BUY"
            ? "bg-emerald-500 hover:bg-emerald-400 text-neutral-950"
            : "bg-rose-500 hover:bg-rose-400 text-neutral-950"
        } disabled:opacity-50`}
      >
        {isSubmitting ? "Matching..." : `Submit ${side} Order`}
      </button>

      {lastResult && (
        <div
          className={`p-2.5 rounded-lg text-xs border ${
            lastResult.startsWith("Error")
              ? "bg-rose-950/30 border-rose-800/50 text-rose-300"
              : "bg-emerald-950/30 border-emerald-800/50 text-emerald-300"
          }`}
        >
          {lastResult}
        </div>
      )}
    </form>
  );
}
