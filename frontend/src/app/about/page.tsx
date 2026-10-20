export default function AboutPage() {
  return (
    <div className="max-w-4xl mx-auto space-y-10 py-6">
      <div className="border-b border-neutral-800 pb-6">
        <h1 className="text-3xl font-bold tracking-tight text-neutral-100">
          Methodology & Microstructure Guide
        </h1>
        <p className="mt-2 text-neutral-400">
          How ImpactLab models NSE-style continuous limit order books, synthetic Poisson order flow, and non-linear market impact.
        </p>
      </div>

      <section className="space-y-4">
        <h2 className="text-xl font-semibold text-neutral-200">1. Core Question</h2>
        <p className="text-neutral-300 leading-relaxed">
          In typical backtesting software, traders frequently assume a flat slippage (e.g., 0.05% or 5 bps). In reality, slippage is highly non-linear and depends heavily on order size relative to resting book depth, prevailing bid-ask spread, and immediate market impact.
        </p>
        <div className="p-4 rounded-lg bg-neutral-900 border border-neutral-800 font-mono text-sm text-emerald-400">
          &quot;If I trade Q shares of this stock right now, what will it really cost me?&quot;
        </div>
      </section>

      <section className="space-y-4">
        <h2 className="text-xl font-semibold text-neutral-200">2. Engine Microstructure Invariants</h2>
        <ul className="list-disc list-inside space-y-2 text-neutral-300">
          <li><strong>Integer Paise Pricing:</strong> All prices inside the matching engine are integers in paise (e.g., ₹100.00 = 10,000 paise) preventing float rounding bugs.</li>
          <li><strong>Price-Time Priority (FIFO):</strong> At any price level, orders that arrived earlier in simulated sequence execute first.</li>
          <li><strong>No Crossed Book:</strong> Best bid is strictly lower than best ask whenever both exist.</li>
          <li><strong>Quantity Conservation:</strong> Submitted quantity = filled quantity + canceled quantity + resting quantity.</li>
          <li><strong>Maker Trade Pricing:</strong> Trade executions occur at the resting (maker) order&apos;s price.</li>
        </ul>
      </section>

      <section className="space-y-4">
        <h2 className="text-xl font-semibold text-neutral-200">3. Stock Liquidity Profiles</h2>
        <div className="overflow-x-auto border border-neutral-800 rounded-lg">
          <table className="w-full text-left text-sm text-neutral-300">
            <thead className="bg-neutral-900 text-neutral-400 text-xs uppercase font-mono">
              <tr>
                <th className="p-3">Profile</th>
                <th className="p-3">Ref Price</th>
                <th className="p-3">Typical Spread</th>
                <th className="p-3">Depth (Shares)</th>
                <th className="p-3">Arrival Rate</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-neutral-800">
              <tr>
                <td className="p-3 font-medium text-neutral-100">Large-cap</td>
                <td className="p-3 font-mono">₹2,500.00</td>
                <td className="p-3">1 - 2 ticks (5 - 10 paise)</td>
                <td className="p-3 font-mono">~50,000</td>
                <td className="p-3">40 orders / sec</td>
              </tr>
              <tr>
                <td className="p-3 font-medium text-neutral-100">Mid-cap</td>
                <td className="p-3 font-mono">₹450.00</td>
                <td className="p-3">3 - 6 ticks (15 - 30 paise)</td>
                <td className="p-3 font-mono">~6,000</td>
                <td className="p-3">8 orders / sec</td>
              </tr>
              <tr>
                <td className="p-3 font-medium text-neutral-100">Small-cap</td>
                <td className="p-3 font-mono">₹85.00</td>
                <td className="p-3">8 - 20 ticks (40 - 100 paise)</td>
                <td className="p-3 font-mono">~800</td>
                <td className="p-3">1.5 orders / sec</td>
              </tr>
            </tbody>
          </table>
        </div>
      </section>

      <section className="space-y-4">
        <h2 className="text-xl font-semibold text-neutral-200">4. Indian Statutory Charges Breakdown</h2>
        <p className="text-neutral-300 leading-relaxed text-sm">
          ImpactLab calculates itemized Indian equity trading costs based on standard schedules (Schedule As Of: <strong>2024-04-01</strong>):
        </p>
        <ul className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-sm text-neutral-300">
          <li className="p-3 bg-neutral-900/60 rounded border border-neutral-800">
            <strong>Brokerage:</strong> Flat or percentage (e.g. ₹20 max per order).
          </li>
          <li className="p-3 bg-neutral-900/60 rounded border border-neutral-800">
            <strong>STT:</strong> 0.1% on equity delivery (buy &amp; sell); 0.025% on intraday sell.
          </li>
          <li className="p-3 bg-neutral-900/60 rounded border border-neutral-800">
            <strong>Exchange Txn Fee:</strong> ~0.00325% on NSE equity turnover.
          </li>
          <li className="p-3 bg-neutral-900/60 rounded border border-neutral-800">
            <strong>SEBI Fee:</strong> ₹10 per crore of turnover.
          </li>
          <li className="p-3 bg-neutral-900/60 rounded border border-neutral-800">
            <strong>Stamp Duty:</strong> 0.015% on delivery buy side; 0.003% on intraday buy side.
          </li>
          <li className="p-3 bg-neutral-900/60 rounded border border-neutral-800">
            <strong>GST:</strong> 18% applied on (Brokerage + Exchange Txn + SEBI Fee).
          </li>
        </ul>
      </section>

      <section className="p-6 rounded-xl bg-amber-950/20 border border-amber-500/20 space-y-2">
        <h3 className="font-semibold text-amber-300 text-sm">Regulatory Notice &amp; Disclaimer</h3>
        <p className="text-xs text-amber-200/80 leading-relaxed">
          ImpactLab is an educational and academic research tool. It uses synthetic order flow generated by Poisson processes and does not connect to real exchanges or brokers. Nothing here constitutes investment advice or a trade recommendation.
        </p>
      </section>
    </div>
  );
}
