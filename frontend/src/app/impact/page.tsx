"use client";

import { useEffect, useState } from "react";
import {
  api,
  ImpactSimulateResponse,
  SessionResponse,
  StockProfile,
} from "@/lib/api";
import { ResultCard } from "@/components/ResultCard";
import { SlippageCurve } from "@/components/SlippageCurve";
import { formatShares } from "@/lib/format";
import { Layers, Sliders } from "lucide-react";

export default function ImpactPage() {
  const [profiles, setProfiles] = useState<StockProfile[]>([]);
  const [selectedProfile, setSelectedProfile] = useState<string>("mid_cap");
  const [session, setSession] = useState<SessionResponse | null>(null);

  // Form controls
  const [side, setSide] = useState<"BUY" | "SELL">("BUY");
  const [sizeMode, setSizeMode] = useState<"shares" | "rupees">("shares");
  const [sizeValue, setSizeValue] = useState<number>(500);
  const [simMode, setSimMode] = useState<"static" | "dynamic">("static");
  const [strategy, setStrategy] = useState<string>("twap");

  // Results & status
  const [result, setResult] = useState<ImpactSimulateResponse | null>(null);
  const [curveData, setCurveData] = useState<Array<{ size: number; slippageBps: number }>>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // 1. Initial load: profiles & session
  useEffect(() => {
    async function init() {
      try {
        const profs = await api.getProfiles();
        setProfiles(profs);
        const sess = await api.createSession("mid_cap", 1, 20.0);
        setSession(sess);
      } catch (err: unknown) {
        setError(err instanceof Error ? err.message : "Initialization failed");
      }
    }
    init();
  }, []);

  // 2. Compute impact and slippage curve whenever inputs or session change
  useEffect(() => {
    if (!session?.session_id) return;

    let isMounted = true;

    async function runImpactSimulation() {
      try {
        setLoading(true);
        setError(null);

        // Run main simulation for current size
        const simRes = await api.simulateImpact({
          session_id: session!.session_id,
          side,
          size: { mode: sizeMode, value: sizeValue },
          mode: simMode,
          strategy: { name: strategy, duration_seconds: 30.0, num_slices: 5 },
        });

        if (!isMounted) return;
        setResult(simRes);

        // Precompute slippage curve points for static mode
        if (sizeMode === "shares") {
          const sweepSizes = [50, 100, 250, 500, 1000, 2000, 3500, 5000, 7500, 10000];
          const curvePromises = sweepSizes.map((s) =>
            api.simulateImpact({
              session_id: session!.session_id,
              side,
              size: { mode: "shares", value: s },
              mode: "static",
            })
          );
          const sweepResults = await Promise.all(curvePromises);
          if (!isMounted) return;
          const points = sweepResults.map((r, i) => ({
            size: sweepSizes[i],
            slippageBps: r.slippage_bps ?? 0,
          }));
          setCurveData(points);
        }
      } catch (err: unknown) {
        if (!isMounted) return;
        setError(err instanceof Error ? err.message : "Impact simulation failed");
      } finally {
        if (isMounted) setLoading(false);
      }
    }

    const timer = setTimeout(runImpactSimulation, 150); // slight debounce for slider
    return () => {
      isMounted = false;
      clearTimeout(timer);
    };
  }, [session, side, sizeMode, sizeValue, simMode, strategy]);

  // Handle profile switch
  const handleProfileSwitch = async (newProf: string) => {
    try {
      setSelectedProfile(newProf);
      setLoading(true);
      const sess = await api.createSession(newProf, 1, 20.0);
      setSession(sess);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Profile change failed");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 p-4 rounded-xl bg-neutral-900/60 border border-neutral-800">
        <div>
          <h1 className="text-xl font-bold text-neutral-100 flex items-center gap-2">
            Market Impact &amp; Slippage Analyzer
            <Layers className="w-5 h-5 text-emerald-400" />
          </h1>
          <p className="text-xs text-neutral-400 mt-0.5">
            Evaluate price impact, non-linear slippage, and statutory charges without touching the live book.
          </p>
        </div>

        {/* Profile Tabs */}
        <div className="flex items-center gap-2 bg-neutral-950 p-1 rounded-lg border border-neutral-800">
          {profiles.map((p) => (
            <button
              key={p.name}
              onClick={() => handleProfileSwitch(p.name)}
              className={`px-3 py-1.5 rounded-md text-xs font-semibold transition-all ${
                selectedProfile === p.name
                  ? "bg-emerald-500 text-neutral-950 shadow"
                  : "text-neutral-400 hover:text-neutral-200"
              }`}
            >
              {p.name.replace("_", " ").toUpperCase()}
            </button>
          ))}
        </div>
      </div>

      {error && (
        <div className="p-3 rounded-lg bg-rose-950/40 border border-rose-800/60 text-xs text-rose-300">
          {error}
        </div>
      )}

      {/* Main 2-column layout */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Left Column: Interactive What-If Controls (4 cols) */}
        <div className="lg:col-span-4 space-y-6">
          <div className="rounded-xl border border-neutral-800 bg-neutral-900/60 p-5 space-y-5 font-mono text-xs">
            <div className="flex items-center justify-between border-b border-neutral-800 pb-3">
              <h3 className="font-semibold text-neutral-200 flex items-center gap-2">
                <Sliders className="w-4 h-4 text-emerald-400" /> What-If Parameter Controls
              </h3>
            </div>

            {/* Side Toggle */}
            <div className="grid grid-cols-2 gap-2">
              <button
                type="button"
                onClick={() => setSide("BUY")}
                className={`py-2 rounded-lg font-bold text-center transition-all ${
                  side === "BUY"
                    ? "bg-emerald-500 text-neutral-950 shadow"
                    : "bg-neutral-800 text-neutral-400 hover:text-neutral-200"
                }`}
              >
                BUY (Walk Asks)
              </button>
              <button
                type="button"
                onClick={() => setSide("SELL")}
                className={`py-2 rounded-lg font-bold text-center transition-all ${
                  side === "SELL"
                    ? "bg-rose-500 text-neutral-950 shadow"
                    : "bg-neutral-800 text-neutral-400 hover:text-neutral-200"
                }`}
              >
                SELL (Walk Bids)
              </button>
            </div>

            {/* Size Mode Toggle */}
            <div>
              <label className="text-[11px] text-neutral-400 block mb-1">Size Input Unit</label>
              <div className="grid grid-cols-2 gap-2">
                <button
                  type="button"
                  onClick={() => setSizeMode("shares")}
                  className={`py-1.5 rounded-lg text-xs font-semibold ${
                    sizeMode === "shares"
                      ? "bg-neutral-800 text-emerald-400 border border-emerald-500/30"
                      : "bg-neutral-950 text-neutral-400 border border-neutral-800"
                  }`}
                >
                  Shares (Quantity)
                </button>
                <button
                  type="button"
                  onClick={() => setSizeMode("rupees")}
                  className={`py-1.5 rounded-lg text-xs font-semibold ${
                    sizeMode === "rupees"
                      ? "bg-neutral-800 text-emerald-400 border border-emerald-500/30"
                      : "bg-neutral-950 text-neutral-400 border border-neutral-800"
                  }`}
                >
                  Rupees (Budget ₹)
                </button>
              </div>
            </div>

            {/* Order Size Input & What-If Slider */}
            <div className="space-y-2">
              <div className="flex justify-between items-center text-xs">
                <label className="text-neutral-300 font-semibold">
                  {sizeMode === "shares" ? "Order Size (Shares)" : "Budget (Rupees ₹)"}
                </label>
                <span className="text-emerald-400 font-bold">
                  {sizeMode === "shares" ? formatShares(sizeValue) : `₹${sizeValue.toLocaleString("en-IN")}`}
                </span>
              </div>

              <input
                type="range"
                min="10"
                max={sizeMode === "shares" ? "10000" : "500000"}
                step={sizeMode === "shares" ? "10" : "500"}
                value={sizeValue}
                onChange={(e) => setSizeValue(parseInt(e.target.value, 10))}
                className="w-full accent-emerald-500 cursor-pointer"
              />

              <div className="flex justify-between text-[10px] text-neutral-400">
                <span>{sizeMode === "shares" ? "10 shs" : "₹10"}</span>
                <span>{sizeMode === "shares" ? "5,000 shs" : "₹2,50,000"}</span>
                <span>{sizeMode === "shares" ? "10,000 shs" : "₹5,00,000"}</span>
              </div>
            </div>

            {/* Simulation Mode Toggle */}
            <div>
              <label className="text-[11px] text-neutral-400 block mb-1">Execution Mode</label>
              <select
                value={simMode}
                onChange={(e) => setSimMode(e.target.value as "static" | "dynamic")}
                className="w-full bg-neutral-950 border border-neutral-800 rounded-lg px-3 py-2 text-neutral-200"
              >
                <option value="static">Static Walk (Frozen snapshot, instantaneous)</option>
                <option value="dynamic">Dynamic Slicing (With Poisson active flow)</option>
              </select>
            </div>

            {/* Dynamic Strategy Choice */}
            {simMode === "dynamic" && (
              <div>
                <label className="text-[11px] text-neutral-400 block mb-1">Strategy</label>
                <select
                  value={strategy}
                  onChange={(e) => setStrategy(e.target.value)}
                  className="w-full bg-neutral-950 border border-neutral-800 rounded-lg px-3 py-2 text-neutral-200"
                >
                  <option value="market">Immediate Market Order</option>
                  <option value="twap">TWAP (Equal Slices over Time)</option>
                  <option value="vwap">VWAP (U-Curve Volume Allocation)</option>
                  <option value="passive">Passive Limit (Pegged to Touch)</option>
                </select>
              </div>
            )}
          </div>
        </div>

        {/* Right Column: Slippage Curve & Result Card (8 cols) */}
        <div className="lg:col-span-8 space-y-6">
          {sizeMode === "shares" && (
            <SlippageCurve
              data={curveData}
              currentSize={sizeValue}
              currentSlippageBps={result?.slippage_bps ?? null}
            />
          )}

          {result ? (
            <ResultCard result={result} />
          ) : (
            <div className="p-8 text-center text-neutral-400 border border-neutral-800 rounded-xl bg-neutral-900/40">
              {loading ? "Calculating market impact..." : "Select parameters to view impact"}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
