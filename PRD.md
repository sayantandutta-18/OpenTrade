# PRD: ImpactLab
### Limit Order Book Simulator with Market Impact Analysis (NSE-style)

Version 1.0 | Status: Draft | Owner: You

---

## 1. Summary

ImpactLab is a web application that simulates a price-time priority limit order book for an Indian equity (NSE-style rules), feeds it synthetic order flow, and lets a user place a hypothetical order to measure what it actually costs to execute: average fill price, slippage, price impact, and total cost including Indian trading charges.

It answers one core question: **"If I trade this much of this stock right now, what will it really cost me?"**

It is a simulation and research tool. It does not connect to a real broker, does not place real trades, and does not give buy/sell advice.

## 2. Problem

- Retail and small algo traders in India often assume a fixed slippage (for example 0.05%) in backtests. Real slippage depends on order size relative to book depth, spread, and volatility.
- Students and early-career engineers have no hands-on way to see market microstructure (queues, spreads, depth, impact) in action.
- Real order book tick data in India is expensive or licensed, so most people cannot experiment.

## 3. Target users

| Persona | Need | How ImpactLab helps |
|---|---|---|
| Retail algo trader (primary) | More realistic fill assumptions for backtests | Impact curves per stock profile, exportable slippage tables |
| Finance / CS student | Learn how order books work | Interactive book, step-through matching, replay |
| Small fund / PMS analyst | Estimate cost of larger orders | Pre-trade cost estimator, TWAP/VWAP comparison |
| Recruiter / interviewer (secondary) | Judge engineering quality | Clean architecture, tests, benchmarks, write-up |

## 4. Goals and non-goals

### Goals
1. A correct, deterministic, well-tested matching engine (price-time priority).
2. A market impact calculator that works on any order book snapshot.
3. Synthetic order flow with selectable stock profiles (deep large-cap, mid-cap, thin small-cap).
4. Experiments that show nonlinear impact vs order size with statistical confidence (Monte Carlo).
5. Execution strategy comparison (single market order vs TWAP vs VWAP vs passive limit).
6. Fully reproducible runs (same seed and config gives the same result).
7. A clear dashboard that explains results to a non-expert.

### Non-goals (v1)
- Live trading or broker integration.
- Real-time NSE/BSE market data redistribution.
- Trade recommendations or investment advice.
- Multi-asset or derivatives pricing (F&O is a stretch goal, not v1).
- Mobile app (responsive web only).
- Claiming statistically calibrated realism for any specific real stock.

## 5. Scope by release

### MVP (v0.1): "It works"
- Single stock, single session.
- Limit and market orders, cancel.
- Price-time priority matching with partial fills.
- Seed the book from a stock profile.
- Impact calculator for a hypothetical market buy or sell.
- Depth chart and slippage-vs-size chart.
- Rupee formatting (lakh/crore), tick size Rs 0.05.

### v0.5: "It's realistic"
- Synthetic order flow (Poisson arrivals, cancellations, heavy-tailed sizes).
- IOC, FOK, post-only, modify order.
- Stock profiles: Large-cap, Mid-cap, Small-cap.
- Indian charges breakdown (brokerage, STT, exchange charges, GST, SEBI fee, stamp duty).
- Experiments: size sweep, spread sweep, depth sweep.
- Live updates over WebSocket.

### v1.0: "It's research-grade"
- Monte Carlo with confidence intervals.
- Execution algos: TWAP, VWAP, passive limit; compare cost vs risk.
- Temporary vs permanent impact analysis.
- Event log, deterministic replay with play/pause/speed.
- Saved experiments, shareable report (CSV/PDF export).
- Auth, rate limiting, Docker, CI, monitoring, public demo.

### v1.5+: Stretch
- Almgren-Chriss optimal execution.
- Square-root law fit check.
- Circuit-limit (price band) scenarios and pre-open call auction.
- F&O mode with lot sizes.
- RL execution agent, LLM explainer.
- Rust hot path via PyO3.

## 6. User stories and acceptance criteria

### Order book and matching
- **US-1** As a user, I can see the live order book (top N bids/asks, quantities, spread, mid price).
  - AC: Bids sorted high to low, asks low to high; best bid is always lower than best ask.
- **US-2** As a user, I can submit a limit order and see it rest or fill.
  - AC: Order that crosses the spread fills immediately at the resting order's price; remainder rests.
- **US-3** As a user, I can submit a market order and see each fill.
  - AC: Fills walk price levels in order; fills at the same price follow arrival order.
- **US-4** As a user, I can cancel a resting order.
  - AC: Cancelled order disappears from the book; its queue position is released.

### Impact analysis
- **US-5** As a user, I can enter a hypothetical order (shares or rupee amount, side) and see impact without changing the live book.
  - AC: Result shows average price, slippage (Rs, %, bps), levels consumed, unfilled quantity, total charges.
  - AC: The reference example (400 shares against the sample book) yields avg Rs 100.10 and total Rs 40,040.
- **US-6** As a user, I can see how slippage changes with order size.
  - AC: A chart plots slippage vs size from the same starting book; curve is non-decreasing.
- **US-7** As a user, I can compare liquid vs illiquid stock profiles.
  - AC: Same order size on three profiles gives three distinct results on one chart.

### Experiments
- **US-8** As a user, I can run an experiment of N Monte Carlo runs with a seed.
  - AC: Results show mean, median, p5/p95 of slippage; same seed gives identical output.
- **US-9** As a user, I can compare one big order vs sliced execution.
  - AC: Output shows cost, shortfall vs arrival price, and variance for each strategy.

### Replay and reproducibility
- **US-10** As a user, I can replay a saved session.
  - AC: Replay reproduces the exact same trades from the event log.

### Safety and trust
- **US-11** As a user, I always see a clear note that results are simulated and not advice.
  - AC: Disclaimer is visible on every results page and on /about.

## 7. Functional requirements

### FR-1 Matching engine
- Price-time priority; integer prices (paise) to avoid float errors.
- Tick size and lot size validation (default tick Rs 0.05, lot 1).
- Order types: LIMIT, MARKET; v0.5 adds IOC, FOK, POST_ONLY.
- Operations: submit, cancel, modify (reduce keeps priority; increase or price change loses it).
- Partial fills with remaining quantity updated.
- Self-trade prevention (v0.5).
- Every state change emits an event (ACCEPTED, TRADE, CANCELED, REJECTED, MODIFIED).
- Invariants always hold: no crossed book, quantity conserved, no negative quantities.

### FR-2 Impact calculator
- Two modes: **static** (walk a frozen snapshot, no new arrivals) and **dynamic** (run through the engine while synthetic flow continues).
- Outputs: average fill price, VWAP, slippage vs best price and vs mid, price impact (post-trade mid vs pre-trade mid), cost in Rs, levels consumed, fill ratio.

### FR-3 Synthetic order flow
- Configurable per profile: arrival rates, cancel rate, size distribution, spread target, depth shape, volatility.
- Deterministic given a seed.
- Agent types: market maker, noise trader (v0.5); informed/momentum (v1).

### FR-4 Execution strategies (v1)
- Market, TWAP, VWAP (volume curve), passive limit, with parameters (duration, slices, participation rate).

### FR-5 Charges
- Itemized charges for equity delivery and intraday; rates in a config file with an "as of" date so they can be updated. Display a note to verify current rates.

### FR-6 Dashboard
- Pages: Simulator, Impact, Experiments, Replay, About (methodology and disclaimer).
- Charts: depth chart, trade tape, spread over time, slippage vs size, strategy comparison.

### FR-7 API
- REST for commands and queries, WebSocket for live updates, OpenAPI docs at /docs.

### FR-8 Persistence
- Store sessions, event logs, experiments, and results (PostgreSQL).

### FR-9 Auth and limits (v1)
- Email or OAuth login, per-user experiments, rate limiting on heavy endpoints.

## 8. Non-functional requirements

| Area | Requirement |
|---|---|
| Correctness | 100% of matching engine invariants covered by unit and property-based tests |
| Determinism | Same seed + config + code version gives byte-identical event log |
| Performance (Python engine) | At least 50,000 order events/sec on a laptop in benchmark; documented |
| API latency | Impact simulate for 10,000 shares under 200 ms (static mode) |
| Reliability | Heavy experiments run in background jobs; API stays responsive |
| Security | Input validation, rate limits, no secrets in repo, CORS locked down |
| Accessibility | Keyboard-navigable, color-blind-safe chart palette, sufficient contrast |
| Observability | Structured logs, health endpoint, basic metrics |
| Maintainability | Type hints, linting, CI on every PR, README with architecture diagram |

## 9. Success metrics

Product / project:
- Matching engine test suite passes with 90%+ coverage on engine module.
- A user can go from landing page to first impact result in under 60 seconds.
- Monte Carlo experiment of 200 runs completes in under 30 seconds on the demo server.
- Published write-up with at least three findings backed by experiments.

Portfolio / adoption:
- GitHub repo with CI badge, docs, and a live demo link.
- Stars, forks, or users trying the demo (track simple page analytics).

## 10. Key experiments to ship (the "findings")

1. Slippage vs order size on large-cap, mid-cap, small-cap profiles (show nonlinearity).
2. Effect of wider spread on execution cost.
3. Effect of thinner depth on price impact.
4. One big order vs TWAP vs VWAP: cost and variance.
5. Temporary vs permanent impact: does the price recover after the order?
6. Does the simulator reproduce the square-root impact shape? (report honestly either way)

## 11. Risks and mitigations

| Risk | Mitigation |
|---|---|
| Synthetic data does not match real markets | Label as synthetic; validate against known stylized facts; state limitations on About page |
| Scope creep (dashboard, AI, Rust) | Strict phase order; engine and experiments first |
| Float rounding bugs in prices | Integer paise everywhere in engine |
| Performance too slow for Monte Carlo | Benchmark early; background jobs; optional Rust hot path |
| Regulatory misinterpretation (advice) | No buy/sell language; disclaimers; research framing |
| Data licensing | Do not redistribute NSE/BSE data; use only synthetic or properly licensed data |
| Charge rates become outdated | Rates in config with "as of" date and verification note |

## 12. Legal and compliance notes

- Simulation and education only; not investment advice.
- Do not display or redistribute exchange data without a license.
- SEBI rules on algorithmic trading and advisory change over time; verify current rules before adding any live-trading or recommendation features.
- Show the disclaimer: "Results are produced by a simulation using synthetic data and simplifying assumptions. Real execution costs will differ."

## 13. Milestones (suggested, solo builder)

| Weeks | Milestone |
|---|---|
| 1-2 | Repo setup, matching engine, unit tests, worked example passes |
| 3-4 | Impact calculator, stock profiles, CLI demo |
| 5-6 | Synthetic order flow, determinism, property tests |
| 7-8 | FastAPI, charges module, WebSocket |
| 9-10 | Next.js dashboard (Simulator, Impact) |
| 11-12 | Experiments, Monte Carlo, execution algos |
| 13-14 | Postgres, event log, replay, background jobs |
| 15-16 | Auth, Docker, CI, deploy, docs, write-up |

## 14. Open questions

1. Public demo only, or accounts and saved experiments from day one?
2. Is F&O a must-have or a later add-on?
3. Is the primary audience traders, students, or recruiters? (Affects polish priorities.)
4. Which hosting budget? (Free tiers limit Monte Carlo throughput.)
