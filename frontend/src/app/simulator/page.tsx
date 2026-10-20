"use client";

import { useEffect, useRef, useState } from "react";
import {
  api,
  BookResponse,
  OrderSubmitResponse,
  SessionResponse,
  StockProfile,
  TradeSchema,
} from "@/lib/api";
import { DepthChart } from "@/components/DepthChart";
import { OrderBookLadder } from "@/components/OrderBookLadder";
import { OrderTicket } from "@/components/OrderTicket";
import { TradeTape } from "@/components/TradeTape";
import { Clock, Play, RefreshCw, Zap } from "lucide-react";

export default function SimulatorPage() {
  const [profiles, setProfiles] = useState<StockProfile[]>([]);
  const [selectedProfile, setSelectedProfile] = useState<string>("mid_cap");
  const [session, setSession] = useState<SessionResponse | null>(null);
  const [book, setBook] = useState<BookResponse | null>(null);
  const [trades, setTrades] = useState<TradeSchema[]>([]);
  const [loading, setLoading] = useState(true);
  const [advancing, setAdvancing] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const wsRef = useRef<WebSocket | null>(null);

  // 1. Initial load: fetch profiles & create session
  useEffect(() => {
    async function init() {
      try {
        setLoading(true);
        const profs = await api.getProfiles();
        setProfiles(profs);
        const sess = await api.createSession("mid_cap", 1, 15.0);
        setSession(sess);
        const b = await api.getBook(sess.session_id, 10);
        setBook(b);
      } catch (err: unknown) {
        setError(err instanceof Error ? err.message : "Failed to load simulator");
      } finally {
        setLoading(false);
      }
    }
    init();
  }, []);

  // 2. Setup WebSocket connection whenever session changes
  useEffect(() => {
    if (!session?.session_id) return;

    const wsUrl = `ws://localhost:8000/ws/sessions/${session.session_id}`;
    const ws = new WebSocket(wsUrl);
    wsRef.current = ws;

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        if (data.type === "book_update" && data.book) {
          setBook(data.book);
          if (data.trades && Array.isArray(data.trades) && data.trades.length > 0) {
            setTrades((prev) => [...prev, ...data.trades].slice(-50));
          }
        }
      } catch {
        // ignore malformed
      }
    };

    return () => {
      ws.close();
    };
  }, [session?.session_id]);

  // Handle profile change
  const handleProfileChange = async (newProf: string) => {
    try {
      setLoading(true);
      setError(null);
      setSelectedProfile(newProf);
      const sess = await api.createSession(newProf, 1, 15.0);
      setSession(sess);
      const b = await api.getBook(sess.session_id, 10);
      setBook(b);
      setTrades([]);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to switch profile");
    } finally {
      setLoading(false);
    }
  };

  // Advance simulated time
  const handleAdvance = async (seconds: number) => {
    if (!session) return;
    try {
      setAdvancing(true);
      const res = await api.advanceTime(session.session_id, seconds);
      setBook(res.book);
      setSession((prev) =>
        prev ? { ...prev, current_time_us: res.current_time_us } : null
      );
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Advance failed");
    } finally {
      setAdvancing(false);
    }
  };

  // Submit order from OrderTicket
  const handleOrderSubmit = async (order: {
    side: "BUY" | "SELL";
    type: string;
    qty: number;
    price?: number;
  }): Promise<OrderSubmitResponse> => {
    if (!session) throw new Error("No active session");
    const res = await api.submitOrder(session.session_id, order);
    const b = await api.getBook(session.session_id, 10);
    setBook(b);
    if (res.trades && res.trades.length > 0) {
      setTrades((prev) => [...prev, ...res.trades].slice(-50));
    }
    return res;
  };

  return (
    <div className="space-y-6">
      {/* Top Header / Profile Switcher */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 p-4 rounded-xl bg-neutral-900/60 border border-neutral-800">
        <div>
          <h1 className="text-xl font-bold text-neutral-100 flex items-center gap-2">
            Continuous Trading Simulator
            <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
          </h1>
          <p className="text-xs text-neutral-400 mt-0.5">
            Price-time priority matching engine with synthetic Poisson order flow.
          </p>
        </div>

        {/* Profile Tabs */}
        <div className="flex items-center gap-2 bg-neutral-950 p-1 rounded-lg border border-neutral-800">
          {profiles.map((p) => {
            const active = selectedProfile === p.name;
            return (
              <button
                key={p.name}
                onClick={() => handleProfileChange(p.name)}
                className={`px-3 py-1.5 rounded-md text-xs font-semibold transition-all ${
                  active
                    ? "bg-emerald-500 text-neutral-950 shadow"
                    : "text-neutral-400 hover:text-neutral-200"
                }`}
              >
                {p.name.replace("_", " ").toUpperCase()}
              </button>
            );
          })}
        </div>
      </div>

      {error && (
        <div className="p-3 rounded-lg bg-rose-950/40 border border-rose-800/60 text-xs text-rose-300">
          {error}
        </div>
      )}

      {/* Simulator Controls & Layout */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Left Column: Order Ticket & Advance Time (4 cols) */}
        <div className="lg:col-span-4 space-y-6">
          <OrderTicket
            onSubmit={handleOrderSubmit}
            bestBid={book?.best_bid ?? null}
            bestAsk={book?.best_ask ?? null}
          />

          {/* Advance Time Controls */}
          <div className="p-4 rounded-xl bg-neutral-900/60 border border-neutral-800 space-y-3 font-mono text-xs">
            <div className="flex items-center justify-between border-b border-neutral-800 pb-2">
              <span className="font-semibold text-neutral-200 flex items-center gap-1.5">
                <Clock className="w-4 h-4 text-emerald-400" /> Simulated Clock
              </span>
              <span className="text-[11px] text-neutral-400">
                {session ? `${(session.current_time_us / 1_000_000).toFixed(1)}s elapsed` : "-"}
              </span>
            </div>

            <div className="grid grid-cols-4 gap-2">
              {[1, 5, 10, 30].map((sec) => (
                <button
                  key={sec}
                  disabled={advancing || loading}
                  onClick={() => handleAdvance(sec)}
                  className="py-2 rounded-lg bg-neutral-800 hover:bg-neutral-700 text-neutral-200 text-xs font-bold transition-all disabled:opacity-50 flex items-center justify-center gap-1"
                >
                  <Play className="w-3 h-3 text-emerald-400" /> +{sec}s
                </button>
              ))}
            </div>

            <button
              onClick={() => handleProfileChange(selectedProfile)}
              disabled={loading}
              className="w-full py-2 rounded-lg bg-neutral-950 border border-neutral-800 hover:border-neutral-700 text-neutral-300 text-xs font-medium flex items-center justify-center gap-2 transition-colors"
            >
              <RefreshCw className="w-3.5 h-3.5 text-neutral-400" /> Reset Steady State
            </button>
          </div>
        </div>

        {/* Center Column: Order Book Ladder & Cumulative Depth (5 cols) */}
        <div className="lg:col-span-5 space-y-6">
          <OrderBookLadder
            bids={book?.bids ?? []}
            asks={book?.asks ?? []}
            spread={book?.spread ?? null}
            spreadFormatted={book?.spread_formatted ?? "₹0.00"}
            midFormatted={book?.mid_formatted ?? "₹0.00"}
          />

          <DepthChart
            bids={book?.bids ?? []}
            asks={book?.asks ?? []}
          />
        </div>

        {/* Right Column: Execution Trade Tape (3 cols) */}
        <div className="lg:col-span-3 space-y-6">
          <TradeTape trades={trades} />

          <div className="p-4 rounded-xl bg-neutral-900/60 border border-neutral-800 font-mono text-xs space-y-2">
            <h4 className="font-semibold text-neutral-300 flex items-center gap-1.5">
              <Zap className="w-3.5 h-3.5 text-amber-400" /> Session Rules
            </h4>
            <p className="text-neutral-400 text-[11px] leading-relaxed">
              NSE tick size: ₹0.05. Resting orders rest on price-time priority. Taker orders cross spread and fill at maker prices.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
