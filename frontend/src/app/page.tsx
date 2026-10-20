import Link from "next/link";
import { Activity, ArrowRight, BarChart3, ChevronRight, Layers, ShieldCheck, Zap } from "lucide-react";

export default function Home() {
  return (
    <div className="space-y-16 py-8">
      {/* Hero */}
      <section className="text-center max-w-3xl mx-auto space-y-6">
        <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-emerald-500/10 border border-emerald-500/30 text-emerald-400 text-xs font-mono">
          <Zap className="w-3.5 h-3.5" /> Deterministic Order Book Simulation
        </div>
        <h1 className="text-4xl sm:text-6xl font-extrabold tracking-tight text-neutral-100">
          Measure What It <span className="text-emerald-400">Really Costs</span> to Trade.
        </h1>
        <p className="text-lg text-neutral-400 leading-relaxed">
          Simulate a price-time priority limit order book for Indian equities (NSE-style), inspect depth queues, and calculate true market impact, slippage, and statutory charges before executing.
        </p>

        <div className="flex flex-wrap items-center justify-center gap-4 pt-2">
          <Link
            href="/simulator"
            className="inline-flex items-center gap-2 px-6 py-3 rounded-lg bg-emerald-500 hover:bg-emerald-400 text-neutral-950 font-semibold transition-colors shadow-lg shadow-emerald-500/10"
          >
            Open Live Simulator <ArrowRight className="w-4 h-4" />
          </Link>
          <Link
            href="/impact"
            className="inline-flex items-center gap-2 px-6 py-3 rounded-lg bg-neutral-900 hover:bg-neutral-800 border border-neutral-700 text-neutral-100 font-semibold transition-colors"
          >
            What-If Impact Calculator
          </Link>
        </div>
      </section>

      {/* Feature cards */}
      <section className="grid grid-cols-1 md:grid-cols-3 gap-6 pt-4">
        <Link
          href="/simulator"
          className="group p-6 rounded-xl bg-neutral-900/50 hover:bg-neutral-900 border border-neutral-800 hover:border-emerald-500/50 transition-all space-y-3"
        >
          <div className="w-10 h-10 rounded-lg bg-emerald-500/10 flex items-center justify-center text-emerald-400 border border-emerald-500/20">
            <Activity className="w-5 h-5" />
          </div>
          <h2 className="text-lg font-semibold text-neutral-100 group-hover:text-emerald-400 transition-colors flex items-center justify-between">
            Live Order Book <ChevronRight className="w-4 h-4 opacity-0 group-hover:opacity-100 transition-opacity" />
          </h2>
          <p className="text-sm text-neutral-400 leading-relaxed">
            Step through bids and asks, place limit and market orders, view live depth ladders, and advance synthetic Poisson order flow.
          </p>
        </Link>

        <Link
          href="/impact"
          className="group p-6 rounded-xl bg-neutral-900/50 hover:bg-neutral-900 border border-neutral-800 hover:border-emerald-500/50 transition-all space-y-3"
        >
          <div className="w-10 h-10 rounded-lg bg-emerald-500/10 flex items-center justify-center text-emerald-400 border border-emerald-500/20">
            <Layers className="w-5 h-5" />
          </div>
          <h2 className="text-lg font-semibold text-neutral-100 group-hover:text-emerald-400 transition-colors flex items-center justify-between">
            Impact &amp; Slippage <ChevronRight className="w-4 h-4 opacity-0 group-hover:opacity-100 transition-opacity" />
          </h2>
          <p className="text-sm text-neutral-400 leading-relaxed">
            Walk frozen book levels with interactive what-if sliders to see non-linear slippage curves, price impact, and itemized Indian trading charges.
          </p>
        </Link>

        <Link
          href="/experiments"
          className="group p-6 rounded-xl bg-neutral-900/50 hover:bg-neutral-900 border border-neutral-800 hover:border-emerald-500/50 transition-all space-y-3"
        >
          <div className="w-10 h-10 rounded-lg bg-emerald-500/10 flex items-center justify-center text-emerald-400 border border-emerald-500/20">
            <BarChart3 className="w-5 h-5" />
          </div>
          <h2 className="text-lg font-semibold text-neutral-100 group-hover:text-emerald-400 transition-colors flex items-center justify-between">
            Monte Carlo Experiments <ChevronRight className="w-4 h-4 opacity-0 group-hover:opacity-100 transition-opacity" />
          </h2>
          <p className="text-sm text-neutral-400 leading-relaxed">
            Run multi-seed sweeps across large, mid, and small-cap profiles. Compare single market orders against TWAP, VWAP, and passive limit execution.
          </p>
        </Link>
      </section>

      {/* Trust & Methodology highlight */}
      <section className="p-8 rounded-2xl bg-neutral-900/40 border border-neutral-800 flex flex-col sm:flex-row items-center justify-between gap-6">
        <div className="space-y-1">
          <div className="flex items-center gap-2 text-emerald-400 font-semibold text-sm">
            <ShieldCheck className="w-4 h-4" /> 100% Deterministic Engine
          </div>
          <p className="text-sm text-neutral-300">
            Built with strict integer paise arithmetic, price-time FIFO matching, and reproducible random seed derivations.
          </p>
        </div>
        <Link
          href="/about"
          className="px-4 py-2 rounded-lg bg-neutral-800 hover:bg-neutral-700 text-sm font-medium text-neutral-200 transition-colors shrink-0"
        >
          Read Methodology &rarr;
        </Link>
      </section>
    </div>
  );
}
