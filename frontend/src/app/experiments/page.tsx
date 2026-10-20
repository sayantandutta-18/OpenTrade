"use client";

import { useEffect, useState } from "react";
import {
  Area,
  Bar,
  BarChart,
  CartesianGrid,
  ComposedChart,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import {
  api,
  ExperimentResponse,
  ExperimentSummary,
  StockProfile,
} from "@/lib/api";
import {
  BarChart3,
  Download,
  History,
  Play,
  ShieldAlert,
  TrendingUp,
} from "lucide-react";

export default function ExperimentsPage() {
  const [profiles, setProfiles] = useState<StockProfile[]>([]);
  const [selectedProfile, setSelectedProfile] = useState<string>("mid_cap");
  const [experimentType, setExperimentType] = useState<
    "size_sweep" | "strategy_comparison" | "spread_sweep"
  >("size_sweep");
  const [runs, setRuns] = useState<number>(25);
  const [seed, setSeed] = useState<number>(42);
  const [side, setSide] = useState<"BUY" | "SELL">("BUY");
  const [qty, setQty] = useState<number>(1000);
  const [durationSeconds, setDurationSeconds] = useState<number>(30);
  const [numSlices, setNumSlices] = useState<number>(5);

  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<ExperimentResponse | null>(null);
  const [history, setHistory] = useState<ExperimentSummary[]>([]);

  useEffect(() => {
    async function init() {
      try {
        const [profs, exps] = await Promise.all([
          api.getProfiles(),
          api.listExperiments(10),
        ]);
        setProfiles(profs);
        setHistory(exps);
      } catch (err) {
        console.error("Failed to load initial experiment metadata:", err);
      }
    }
    init();
  }, []);

  const handleRunExperiment = async () => {
    setLoading(true);
    setError(null);
    try {
      const params: Record<string, unknown> = {
        profile: selectedProfile,
        side,
        warmup_seconds: 10.0,
      };

      if (experimentType === "size_sweep") {
        params.sizes = [100, 250, 500, 1000, 2500, 5000];
      } else if (experimentType === "strategy_comparison") {
        params.qty = qty;
        params.duration_seconds = durationSeconds;
        params.num_slices = numSlices;
      } else if (experimentType === "spread_sweep") {
        params.qty = qty;
        params.spread_ticks = [1, 2, 4, 8, 16];
      }

      const expRes = await api.createExperiment({
        type: experimentType,
        params,
        seed: Number(seed),
        runs: Number(runs),
      });

      setResult(expRes);

      // Refresh experiment history
      api.listExperiments(10).then(setHistory).catch(() => {});
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Experiment execution failed";
      setError(msg);
    } finally {
      setLoading(false);
    }
  };

  const handleLoadExperiment = async (expId: string) => {
    setLoading(true);
    setError(null);
    try {
      const expRes = await api.getExperiment(expId);
      setResult(expRes);
      setExperimentType(
        expRes.experiment_type as
          | "size_sweep"
          | "strategy_comparison"
          | "spread_sweep"
      );
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed to load experiment";
      setError(msg);
    } finally {
      setLoading(false);
    }
  };

  const handleExportCSV = () => {
    if (!result || !result.chart_data || result.chart_data.length === 0) return;

    const headers = Object.keys(result.chart_data[0]);
    const csvRows = [
      headers.join(","),
      ...result.chart_data.map((row) =>
        headers.map((h) => JSON.stringify(row[h] ?? "")).join(",")
      ),
    ];
    const blob = new Blob([csvRows.join("\n")], { type: "text/csv;charset=utf-8;" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `impactlab_${result.experiment_type}_seed${result.master_seed}_runs${result.runs}.csv`;
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-8">
      {/* Page Header */}
      <div className="border-b border-neutral-800 pb-6 flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-lg bg-emerald-500/10 border border-emerald-500/20 flex items-center justify-center text-emerald-400">
              <BarChart3 className="w-4 h-4" />
            </div>
            <h1 className="text-2xl font-bold text-neutral-100 tracking-tight">
              Monte Carlo Impact Experiments
            </h1>
          </div>
          <p className="text-sm text-neutral-400 mt-1">
            Execute parallel Monte Carlo sweeps with reproducible child seeds, confidence intervals, and statistical aggregation.
          </p>
        </div>

        {result && (
          <button
            onClick={handleExportCSV}
            className="self-start md:self-auto flex items-center gap-2 px-3.5 py-2 rounded-lg bg-neutral-900 border border-neutral-800 text-xs font-mono font-medium text-neutral-200 hover:text-white hover:bg-neutral-800 transition-colors"
          >
            <Download className="w-3.5 h-3.5" />
            Export CSV
          </button>
        )}
      </div>

      {/* Experiment Controls Configurator */}
      <div className="bg-neutral-900/60 border border-neutral-800 rounded-xl p-5 space-y-5">
        <div className="flex items-center justify-between">
          <div className="text-sm font-semibold text-neutral-200 flex items-center gap-2">
            <TrendingUp className="w-4 h-4 text-emerald-400" />
            <span>Experiment Configuration</span>
          </div>

          <div className="flex items-center gap-2">
            <span className="text-xs font-mono text-neutral-400">Type:</span>
            <div className="flex rounded-lg bg-neutral-950 p-1 border border-neutral-800 text-xs font-mono">
              <button
                onClick={() => setExperimentType("size_sweep")}
                className={`px-3 py-1 rounded transition-colors ${
                  experimentType === "size_sweep"
                    ? "bg-emerald-500/20 text-emerald-400 font-bold"
                    : "text-neutral-400 hover:text-neutral-200"
                }`}
              >
                Size Sweep
              </button>
              <button
                onClick={() => setExperimentType("strategy_comparison")}
                className={`px-3 py-1 rounded transition-colors ${
                  experimentType === "strategy_comparison"
                    ? "bg-emerald-500/20 text-emerald-400 font-bold"
                    : "text-neutral-400 hover:text-neutral-200"
                }`}
              >
                Execution Strategies
              </button>
              <button
                onClick={() => setExperimentType("spread_sweep")}
                className={`px-3 py-1 rounded transition-colors ${
                  experimentType === "spread_sweep"
                    ? "bg-emerald-500/20 text-emerald-400 font-bold"
                    : "text-neutral-400 hover:text-neutral-200"
                }`}
              >
                Spread Sweep
              </button>
            </div>
          </div>
        </div>

        {/* Parameters Grid */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-4 items-end text-xs font-mono">
          <div>
            <label className="block text-neutral-400 mb-1">Stock Profile</label>
            <select
              value={selectedProfile}
              onChange={(e) => setSelectedProfile(e.target.value)}
              className="w-full bg-neutral-950 border border-neutral-800 rounded-lg px-3 py-2 text-neutral-200 focus:outline-none focus:border-emerald-500"
            >
              {profiles.map((p) => (
                <option key={p.name} value={p.name}>
                  {p.name.replace("_", "-").toUpperCase()}
                </option>
              ))}
            </select>
          </div>

          <div>
            <label className="block text-neutral-400 mb-1">Monte Carlo Runs (N)</label>
            <select
              value={runs}
              onChange={(e) => setRuns(Number(e.target.value))}
              className="w-full bg-neutral-950 border border-neutral-800 rounded-lg px-3 py-2 text-neutral-200 focus:outline-none focus:border-emerald-500"
            >
              <option value={10}>10 runs (Fast)</option>
              <option value={25}>25 runs (Balanced)</option>
              <option value={50}>50 runs (High Confidence)</option>
              <option value={100}>100 runs (Research)</option>
              <option value={200}>200 runs (Publication)</option>
            </select>
          </div>

          <div>
            <label className="block text-neutral-400 mb-1">Master Random Seed</label>
            <input
              type="number"
              value={seed}
              onChange={(e) => setSeed(Number(e.target.value))}
              className="w-full bg-neutral-950 border border-neutral-800 rounded-lg px-3 py-2 text-neutral-200 focus:outline-none focus:border-emerald-500"
            />
          </div>

          <div>
            <label className="block text-neutral-400 mb-1">Order Side</label>
            <div className="grid grid-cols-2 gap-1 bg-neutral-950 p-1 border border-neutral-800 rounded-lg">
              <button
                onClick={() => setSide("BUY")}
                className={`py-1 text-center rounded font-semibold transition-colors ${
                  side === "BUY"
                    ? "bg-emerald-500/20 text-emerald-400"
                    : "text-neutral-400 hover:text-neutral-200"
                }`}
              >
                BUY
              </button>
              <button
                onClick={() => setSide("SELL")}
                className={`py-1 text-center rounded font-semibold transition-colors ${
                  side === "SELL"
                    ? "bg-rose-500/20 text-rose-400"
                    : "text-neutral-400 hover:text-neutral-200"
                }`}
              >
                SELL
              </button>
            </div>
          </div>

          <div>
            <button
              onClick={handleRunExperiment}
              disabled={loading}
              className="w-full flex items-center justify-center gap-2 bg-emerald-500 hover:bg-emerald-400 text-neutral-950 font-bold px-4 py-2.5 rounded-lg text-xs font-sans transition-colors disabled:opacity-50"
            >
              <Play className="w-3.5 h-3.5 fill-current" />
              {loading ? "Running Monte Carlo..." : "Run Experiment"}
            </button>
          </div>
        </div>

        {/* Dynamic extra parameters for Strategy Comparison */}
        {experimentType === "strategy_comparison" && (
          <div className="pt-3 border-t border-neutral-800/80 grid grid-cols-1 sm:grid-cols-3 gap-4 text-xs font-mono">
            <div>
              <label className="block text-neutral-400 mb-1">Total Quantity (Shares)</label>
              <input
                type="number"
                value={qty}
                onChange={(e) => setQty(Number(e.target.value))}
                className="w-full bg-neutral-950 border border-neutral-800 rounded-lg px-3 py-1.5 text-neutral-200 focus:outline-none focus:border-emerald-500"
              />
            </div>
            <div>
              <label className="block text-neutral-400 mb-1">Execution Duration (Sec)</label>
              <input
                type="number"
                value={durationSeconds}
                onChange={(e) => setDurationSeconds(Number(e.target.value))}
                className="w-full bg-neutral-950 border border-neutral-800 rounded-lg px-3 py-1.5 text-neutral-200 focus:outline-none focus:border-emerald-500"
              />
            </div>
            <div>
              <label className="block text-neutral-400 mb-1">Number of Slices (N)</label>
              <input
                type="number"
                value={numSlices}
                onChange={(e) => setNumSlices(Number(e.target.value))}
                className="w-full bg-neutral-950 border border-neutral-800 rounded-lg px-3 py-1.5 text-neutral-200 focus:outline-none focus:border-emerald-500"
              />
            </div>
          </div>
        )}
      </div>

      {error && (
        <div className="p-4 rounded-xl border border-rose-500/30 bg-rose-500/10 text-rose-300 text-xs font-mono">
          {error}
        </div>
      )}

      {/* Main Results Display */}
      {result && result.chart_data && (
        <div className="space-y-6">
          {/* Chart Card */}
          <div className="bg-neutral-900/60 border border-neutral-800 rounded-xl p-5 space-y-4">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-neutral-800 pb-3">
              <div>
                <h3 className="font-semibold text-neutral-100 text-sm">
                  {experimentType === "size_sweep" && "Market Impact Curve vs Order Size"}
                  {experimentType === "strategy_comparison" &&
                    "Slippage Across Execution Strategies"}
                  {experimentType === "spread_sweep" &&
                    "Execution Slippage vs Quoted Spread"}
                </h3>
                <p className="text-xs text-neutral-400 font-mono mt-0.5">
                  Aggregated from {result.runs} independent Monte Carlo runs with Seed {result.master_seed}
                </p>
              </div>

              <div className="flex items-center gap-3 text-xs font-mono">
                <span className="flex items-center gap-1 text-emerald-400">
                  <span className="w-2.5 h-2.5 rounded-full bg-emerald-500 inline-block" />
                  Median / Mean
                </span>
                {experimentType === "size_sweep" && (
                  <span className="flex items-center gap-1 text-emerald-500/60">
                    <span className="w-2.5 h-2.5 rounded bg-emerald-500/20 border border-emerald-500/40 inline-block" />
                    p5 - p95 Band
                  </span>
                )}
              </div>
            </div>

            <div className="h-80 w-full pt-2">
              <ResponsiveContainer width="100%" height="100%">
                {experimentType === "size_sweep" ? (
                  <ComposedChart data={result.chart_data}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#262626" />
                    <XAxis
                      dataKey="size"
                      stroke="#737373"
                      fontSize={11}
                      tickFormatter={(v) => `${v} sh`}
                    />
                    <YAxis
                      stroke="#737373"
                      fontSize={11}
                      tickFormatter={(v) => `${v.toFixed(1)} bps`}
                    />
                    <Tooltip
                      contentStyle={{
                        backgroundColor: "#0a0a0a",
                        borderColor: "#262626",
                        borderRadius: "8px",
                        fontSize: "12px",
                        fontFamily: "monospace",
                      }}
                    />
                    <Area
                      type="monotone"
                      dataKey="p95"
                      stroke="transparent"
                      fill="#10b981"
                      fillOpacity={0.12}
                    />
                    <Line
                      type="monotone"
                      dataKey="mean"
                      name="Mean Slippage (bps)"
                      stroke="#0284c7"
                      strokeWidth={2}
                      dot={{ r: 3 }}
                    />
                    <Line
                      type="monotone"
                      dataKey="median"
                      name="Median Slippage (bps)"
                      stroke="#10b981"
                      strokeWidth={2.5}
                      dot={{ r: 4 }}
                    />
                  </ComposedChart>
                ) : experimentType === "strategy_comparison" ? (
                  <BarChart data={result.chart_data}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#262626" />
                    <XAxis
                      dataKey="strategy"
                      stroke="#737373"
                      fontSize={11}
                      tickFormatter={(v) => v.toUpperCase().replace("_", " ")}
                    />
                    <YAxis
                      stroke="#737373"
                      fontSize={11}
                      tickFormatter={(v) => `${v.toFixed(1)} bps`}
                    />
                    <Tooltip
                      contentStyle={{
                        backgroundColor: "#0a0a0a",
                        borderColor: "#262626",
                        borderRadius: "8px",
                        fontSize: "12px",
                        fontFamily: "monospace",
                      }}
                    />
                    <Bar
                      dataKey="mean_slippage_bps"
                      name="Mean Slippage (bps)"
                      fill="#10b981"
                      radius={[4, 4, 0, 0]}
                    />
                  </BarChart>
                ) : (
                  <LineChart data={result.chart_data}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#262626" />
                    <XAxis
                      dataKey="spread_ticks"
                      stroke="#737373"
                      fontSize={11}
                      tickFormatter={(v) => `${v} ticks`}
                    />
                    <YAxis
                      stroke="#737373"
                      fontSize={11}
                      tickFormatter={(v) => `${v.toFixed(1)} bps`}
                    />
                    <Tooltip
                      contentStyle={{
                        backgroundColor: "#0a0a0a",
                        borderColor: "#262626",
                        borderRadius: "8px",
                        fontSize: "12px",
                        fontFamily: "monospace",
                      }}
                    />
                    <Line
                      type="monotone"
                      dataKey="mean_slippage_bps"
                      name="Mean Slippage (bps)"
                      stroke="#10b981"
                      strokeWidth={2}
                      dot={{ r: 4 }}
                    />
                  </LineChart>
                )}
              </ResponsiveContainer>
            </div>
          </div>

          {/* Results Summary Table */}
          <div className="bg-neutral-900/60 border border-neutral-800 rounded-xl overflow-hidden p-5 space-y-3 font-mono text-xs">
            <h4 className="font-semibold text-neutral-200">
              Statistical Summary Table
            </h4>
            <div className="overflow-x-auto">
              <table className="w-full text-left">
                <thead className="bg-neutral-950/80 text-neutral-400 border-b border-neutral-800">
                  <tr>
                    {Object.keys(result.chart_data[0]).map((col) => (
                      <th key={col} className="px-4 py-2.5 font-semibold capitalize">
                        {col.replace(/_/g, " ")}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody className="divide-y divide-neutral-800/60">
                  {result.chart_data.map((row, idx) => (
                    <tr key={`row-${idx}`} className="hover:bg-neutral-800/40">
                      {Object.keys(row).map((k) => (
                        <td key={k} className="px-4 py-2.5 text-neutral-300">
                          {typeof row[k] === "number"
                            ? (row[k] as number).toFixed(2)
                            : String(row[k])}
                        </td>
                      ))}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}

      {/* Recent Experiments History */}
      {history.length > 0 && (
        <div className="bg-neutral-900/60 border border-neutral-800 rounded-xl p-5 space-y-3">
          <div className="flex items-center gap-2 text-sm font-semibold text-neutral-200">
            <History className="w-4 h-4 text-neutral-400" />
            <span>Recent Monte Carlo Sweeps</span>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-left font-mono text-xs">
              <thead className="bg-neutral-950/80 text-neutral-400 border-b border-neutral-800">
                <tr>
                  <th className="px-4 py-2 font-semibold">Experiment ID</th>
                  <th className="px-4 py-2 font-semibold">Type</th>
                  <th className="px-4 py-2 font-semibold">Seed</th>
                  <th className="px-4 py-2 font-semibold">Status</th>
                  <th className="px-4 py-2 font-semibold">Created At</th>
                  <th className="px-4 py-2 font-semibold text-right">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-neutral-800/60">
                {history.map((h) => (
                  <tr key={h.experiment_id} className="hover:bg-neutral-800/40">
                    <td className="px-4 py-2.5 text-neutral-300">
                      {h.experiment_id.slice(0, 12)}...
                    </td>
                    <td className="px-4 py-2.5 text-emerald-400 font-bold">
                      {h.experiment_type}
                    </td>
                    <td className="px-4 py-2.5 text-neutral-400">{h.master_seed}</td>
                    <td className="px-4 py-2.5 text-neutral-300">
                      <span className="px-2 py-0.5 rounded bg-neutral-800 text-[11px]">
                        {h.status}
                      </span>
                    </td>
                    <td className="px-4 py-2.5 text-neutral-500">
                      {h.created_at ? new Date(h.created_at).toLocaleTimeString() : "-"}
                    </td>
                    <td className="px-4 py-2.5 text-right">
                      <button
                        onClick={() => handleLoadExperiment(h.experiment_id)}
                        className="px-3 py-1 rounded bg-neutral-800 hover:bg-neutral-700 text-neutral-200 text-xs font-sans font-medium transition-colors"
                      >
                        Load
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Regulatory Disclaimer Strip */}
      <div className="bg-neutral-900/40 border border-neutral-800 rounded-xl p-4 flex items-center gap-3 text-xs text-neutral-400">
        <ShieldAlert className="w-5 h-5 text-amber-400 shrink-0" />
        <span>
          <strong>Research Disclaimer:</strong> Simulated results produced using synthetic order flow and simplifying assumptions. Not investment advice. Real execution costs will differ.
        </span>
      </div>
    </div>
  );
}
