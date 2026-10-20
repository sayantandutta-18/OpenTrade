# context.md: ImpactLab End-to-End Build Guide (for vibe coding)

> Paste this whole file into your AI coding tool (Claude Code, Cursor, etc.) at the start of every session.
> Then work **one step at a time** using the prompts in Section 14. Do not skip ahead.

---

## 0. How to use this file

1. Read Sections 1-5 once so you understand the project.
2. Keep this file in the repo root as `context.md`. Keep `PRD.md` next to it.
3. Start each coding session with: *"Read context.md and PRD.md. We are on Step N. Do only Step N."*
4. After each step, run the tests, commit, and tick the checklist in Section 15.
5. If the AI drifts from the rules in Section 3, tell it: *"Re-read Section 3 of context.md."*

---

## 1. Project in one paragraph

ImpactLab simulates a price-time priority limit order book for an NSE-style stock, feeds it synthetic order flow, and measures the true cost of executing a hypothetical order (average price, slippage, price impact, Indian charges). A web dashboard visualizes the book, the slippage-vs-size curve, and experiment results. It is a **simulation and research tool**: no real trading, no advice.

## 2. Core concepts (glossary)

| Term | Meaning |
|---|---|
| Bid | Buy order resting in the book |
| Ask | Sell order resting in the book |
| Best bid / best ask | Highest bid / lowest ask |
| Spread | best_ask - best_bid |
| Mid price | (best_bid + best_ask) / 2 |
| Price-time priority | Better price executes first; same price: earlier order first |
| Market order | Executes immediately against the book at whatever prices exist |
| Limit order | Executes only at the limit price or better; remainder rests |
| IOC | Immediate-or-cancel: fill what you can now, cancel the rest |
| FOK | Fill-or-kill: fill entirely now or cancel entirely |
| Post-only | Rejected if it would execute immediately |
| Slippage | Difference between expected price and actual average fill price |
| Market impact | How far your own trade moves the price |
| Arrival price | Mid price at the moment you decide to trade (benchmark) |
| Implementation shortfall | Total cost versus trading at the arrival price |
| TWAP / VWAP | Slicing an order evenly over time / in proportion to expected volume |
| Tick size | Smallest price step (NSE equities: Rs 0.05 for most stocks) |
| Lot size | Minimum quantity multiple (equity cash: 1) |

## 3. Non-negotiable rules for the AI (read before every task)

1. **Prices are integers in paise** inside the engine (Rs 100.00 = 10000). Never use float for prices or money in the engine. Convert to rupees only at the API/UI edge.
2. **Quantities are integers** (shares).
3. **Determinism**: all randomness comes from a seeded `random.Random` / `numpy.random.Generator` passed in explicitly. No global random, no `time.time()` inside the engine. Time is a simulated integer counter (`ts`, in microseconds or event sequence).
4. **The engine knows nothing about FastAPI, the database, or the UI.** It is a pure Python package with no network or disk I/O.
5. **Every state change emits an event.** The event log is the source of truth; the book can be rebuilt from it.
6. **Invariants** must hold after every operation (see Section 6.4). Write tests for them first.
7. **Test first** for the engine: write tests from the spec, then implement.
8. **Type hints everywhere**, `dataclass(slots=True)` for core models, `ruff` + `mypy` clean.
9. **One step at a time.** Do not build UI while the engine is incomplete.
10. **No trading advice language** ("buy", "sell now", "recommended") anywhere in UI copy. Use "simulated", "estimated".
11. **Do not hardcode charge rates** in logic; load from `charges.yaml` with an `as_of` date.
12. **Do not invent results.** Charts and numbers shown must come from actual simulation runs.
13. Keep functions small, name things clearly, add docstrings with examples for engine public methods.

---

## 4. Tech stack

| Layer | Choice | Notes |
|---|---|---|
| Language (backend) | Python 3.12+ | |
| Engine data structures | `dict[int, deque[Order]]` per side + `sortedcontainers.SortedDict` for price levels | O(log n) level insert, O(1) best price |
| API | FastAPI + Uvicorn | OpenAPI at `/docs` |
| Validation | Pydantic v2 | |
| Numerics | NumPy, SciPy, pandas | experiments, stats |
| Background jobs | Start with `ProcessPoolExecutor`; upgrade to Celery/RQ + Redis in Step 12 | |
| Database | PostgreSQL 16 (+ SQLAlchemy 2, Alembic) | SQLite acceptable for first local runs |
| Live updates | WebSockets (FastAPI native) | |
| Frontend | Next.js 15 (App Router) + TypeScript + Tailwind | |
| Charts | Recharts | lightweight-charts optional for price series |
| UI components | shadcn/ui | |
| Testing | pytest, Hypothesis, pytest-cov; Vitest + Playwright (frontend) | |
| Lint/format | ruff, mypy; ESLint, Prettier | |
| Packaging | uv or poetry / pip | pick one and stay consistent |
| Containers | Docker, docker-compose | |
| CI | GitHub Actions | |
| Deploy | Frontend: Vercel. Backend + DB: Railway, Render, or Fly.io | |

---

## 5. Repository layout

```
impactlab/
├── PRD.md
├── context.md
├── README.md
├── docker-compose.yml
├── .github/workflows/ci.yml
├── backend/
│   ├── pyproject.toml
│   ├── alembic.ini
│   ├── migrations/
│   ├── src/impactlab/
│   │   ├── engine/                # PURE: no I/O
│   │   │   ├── models.py          # Order, Trade, Event, enums
│   │   │   ├── book.py            # OrderBook
│   │   │   ├── matcher.py         # MatchingEngine
│   │   │   ├── validation.py      # tick/lot/band checks
│   │   │   └── events.py
│   │   ├── impact/
│   │   │   ├── static_walk.py     # walk a frozen snapshot
│   │   │   ├── dynamic.py         # run via engine with flow
│   │   │   └── metrics.py         # slippage, impact, shortfall
│   │   ├── flow/
│   │   │   ├── profiles.py        # large/mid/small cap configs
│   │   │   ├── generators.py      # Poisson arrivals, sizes
│   │   │   └── agents.py
│   │   ├── execution/
│   │   │   ├── base.py
│   │   │   ├── twap.py
│   │   │   ├── vwap.py
│   │   │   └── passive.py
│   │   ├── charges/
│   │   │   ├── calculator.py
│   │   │   └── charges.yaml
│   │   ├── experiments/
│   │   │   ├── runner.py          # size sweep, monte carlo
│   │   │   └── stats.py
│   │   ├── api/
│   │   │   ├── main.py
│   │   │   ├── routes/
│   │   │   ├── schemas.py
│   │   │   └── ws.py
│   │   ├── db/
│   │   │   ├── models.py
│   │   │   └── session.py
│   │   └── config.py
│   └── tests/
│       ├── engine/
│       ├── impact/
│       ├── flow/
│       ├── api/
│       └── golden/                # golden replay files
└── frontend/
    ├── package.json
    └── src/
        ├── app/
        │   ├── page.tsx           # landing
        │   ├── simulator/
        │   ├── impact/
        │   ├── experiments/
        │   ├── replay/
        │   └── about/
        ├── components/
        │   ├── DepthChart.tsx
        │   ├── OrderBookLadder.tsx
        │   ├── OrderTicket.tsx
        │   ├── SlippageCurve.tsx
        │   ├── TradeTape.tsx
        │   └── ResultCard.tsx
        └── lib/
            ├── api.ts
            ├── format.ts          # rupees, lakh/crore
            └── ws.ts
```

---

## 6. Matching engine specification (the heart)

### 6.1 Data models

```python
class Side(Enum): BUY, SELL
class OrderType(Enum): LIMIT, MARKET, IOC, FOK, POST_ONLY
class Status(Enum): NEW, PARTIAL, FILLED, CANCELED, REJECTED

@dataclass(slots=True)
class Order:
    id: int                # assigned by engine, monotonically increasing
    side: Side
    type: OrderType
    price: int | None      # paise; None for MARKET
    qty: int               # original quantity
    remaining: int
    ts: int                # simulated timestamp / sequence
    owner: str             # "user", "mm_1", "noise_17" ...
    status: Status

@dataclass(slots=True)
class Trade:
    id: int
    price: int
    qty: int
    taker_order_id: int
    maker_order_id: int
    taker_side: Side
    ts: int

@dataclass(slots=True)
class Event:
    seq: int
    ts: int
    kind: str              # ACCEPTED | TRADE | CANCELED | REJECTED | MODIFIED
    payload: dict
```

### 6.2 Book structure

- `bids: SortedDict[int, deque[Order]]` keyed by negative price (so first key is best bid), or use a reverse-ordered structure.
- `asks: SortedDict[int, deque[Order]]` keyed by price (first key is best ask).
- `orders_by_id: dict[int, Order]` for O(1) cancel lookup.
- Remove price level when its deque becomes empty.
- Cancel: mark and remove from deque (use lazy removal or `deque.remove` for MVP; optimize later).

### 6.3 Matching algorithm (buy taker; mirror for sell)

```
submit(order):
  validate (tick, lot, qty > 0, price present for limit types) else REJECT
  if POST_ONLY and would cross: REJECT
  if FOK and available liquidity at acceptable prices < qty: REJECT (or CANCEL), no fills
  while order.remaining > 0 and asks not empty:
      best_ask_price = asks.first_price
      if order is LIMIT/IOC/FOK/POST_ONLY and order.price < best_ask_price: break
      level = asks[best_ask_price]
      maker = level[0]
      fill_qty = min(order.remaining, maker.remaining)
      emit TRADE at maker.price (the resting order's price)
      reduce both remainings; if maker.remaining == 0: popleft, status FILLED
      if level empty: delete level
  if order.remaining > 0:
      if LIMIT or POST_ONLY: rest in book at its price (append to deque), status NEW/PARTIAL
      if MARKET or IOC: cancel remainder (status PARTIAL or CANCELED) and emit CANCELED
      if FOK: already handled
```

Trade price is always the **resting (maker) order's price**.

### 6.4 Invariants (test after every operation)

1. `best_bid < best_ask` whenever both exist (book never crossed).
2. No order in the book has `remaining <= 0`.
3. Sum of quantities in `orders_by_id` equals sum over all price levels.
4. Within a price level, orders are sorted by `ts` ascending.
5. Total quantity conservation: submitted qty = filled qty + canceled qty + resting qty.
6. Every trade has `qty > 0` and price on the tick grid.
7. Event `seq` is strictly increasing with no gaps.

### 6.5 The reference example (must pass, put in `tests/engine/test_reference_example.py`)

Tick size 5 paise. Book:

| Side | Price (Rs) | Qty |
|---|---|---|
| Ask | 100.00 | 100 |
| Ask | 100.10 | 200 |
| Ask | 100.20 | 300 |
| Bid | 99.90 | 100 |
| Bid | 99.80 | 200 |
| Bid | 99.70 | 300 |

Market BUY 400 gives trades: 100 @ 100.00, 200 @ 100.10, 100 @ 100.20.
Total cost = 10,000 + 20,020 + 10,020 = **Rs 40,040**. Average = **Rs 100.10**.
Slippage vs best ask (100.00) = Rs 0.10 per share = Rs 40 total = 10 bps.
Spread before = Rs 0.10. After: best ask becomes 100.20 with 200 remaining.

### 6.6 More engine tests to write

- Same-price time priority (two asks at 100.00; earlier one fills first).
- Partial fill leaves remainder resting for limit orders.
- Limit buy below best ask rests; does not trade.
- Crossing limit buy trades at maker price, not its own limit.
- IOC partial fill cancels remainder; FOK rejects when insufficient depth.
- Post-only rejected when crossing.
- Cancel unknown id returns error, not crash.
- Modify: qty down keeps priority; qty up or price change loses priority.
- Market order on empty side: no fills, canceled, no crash.
- Hypothesis property test: random sequences of submit/cancel never violate invariants.
- Replay test: replaying the event log reproduces identical book and trades.

---

## 7. Impact calculator specification

### 7.1 Two modes

- **Static walk**: take a frozen snapshot, walk price levels for a hypothetical order, no new arrivals. Fast, great for the size-vs-slippage curve.
- **Dynamic**: clone the engine state, submit the order (or schedule slices) while synthetic flow keeps arriving. Slower, closer to reality.

Neither mode may mutate the live session book. Work on a deep copy.

### 7.2 Formulas (buy side; mirror signs for sell)

```
arrival_mid        = (best_bid + best_ask) / 2          # at decision time
avg_price          = sum(price_i * qty_i) / sum(qty_i)
filled_qty         = sum(qty_i)
fill_ratio         = filled_qty / requested_qty
slippage_vs_best   = avg_price - best_ask               # Rs per share
slippage_vs_mid    = avg_price - arrival_mid            # includes half-spread
slippage_bps       = slippage_vs_mid / arrival_mid * 10_000
total_cost         = sum(price_i * qty_i)               # notional paid
price_impact_bps   = (post_mid - arrival_mid) / arrival_mid * 10_000
impl_shortfall     = total_cost - filled_qty * arrival_mid   # buy
levels_consumed    = number of distinct price levels touched
charges            = charges.calculate(side, notional, product_type)
all_in_cost        = impl_shortfall + charges
```

For sells: `impl_shortfall = filled_qty * arrival_mid - total_proceeds`.

Report **both** slippage vs best price and vs mid so users see the half-spread component.

### 7.3 Rupee-amount input

If the user enters a rupee amount instead of shares, convert by walking the book until notional is exhausted (`qty = floor(budget / price)` per level).

### 7.4 Temporary vs permanent impact (v1)

- Permanent: `post_mid` measured after a quiet period (flow continues, no more user orders), e.g., after T seconds of simulated time.
- Temporary: peak deviation during execution minus permanent.

---

## 8. Synthetic order flow specification

### 8.1 Stock profiles (`flow/profiles.py`)

Illustrative defaults to tune; these are **not** calibrated to real stocks:

| Parameter | Large-cap | Mid-cap | Small-cap |
|---|---|---|---|
| Reference price (Rs) | 2,500 | 450 | 85 |
| Typical spread (ticks) | 1-2 | 3-6 | 8-20 |
| Depth within 10 bps (shares) | ~50,000 | ~6,000 | ~800 |
| Limit order arrival rate (per sec) | 40 | 8 | 1.5 |
| Market order arrival rate (per sec) | 6 | 1.2 | 0.2 |
| Cancel rate (fraction of resting per sec) | 0.02 | 0.03 | 0.05 |
| Order size distribution | log-normal, median 80 | log-normal, median 40 | log-normal, median 25 |
| Daily volatility (annualized %) | 22 | 35 | 55 |

Put every parameter in a dataclass `StockProfile` so the UI can override them.

### 8.2 Generator behaviour

- Event times: Poisson process (exponential inter-arrival) per event type.
- Limit order price: offset from mid drawn from a geometric / exponential distribution in ticks, so most orders sit near the touch.
- Side: 50/50 with optional imbalance parameter.
- Sizes: log-normal, clipped to a max.
- Cancellations: pick a random resting order with probability proportional to age or uniformly.
- Mid price drifts via the book's own activity; optionally add a slow random walk for fundamental value that market makers quote around.
- Market maker agent: keeps quotes at mid +/- k ticks, refreshes when mid moves, bounded inventory.
- Warm-up: run flow for N simulated seconds before the user can trade so the book reaches a steady shape.

### 8.3 Stylized facts to sanity-check (report results honestly)

- Spread widens when depth thins.
- Depth is concentrated near the touch.
- Returns are roughly mean-zero with fat tails.
- Impact grows sublinearly to superlinearly in size depending on regime; record what your simulator produces and do not claim a fit you did not measure.

---

## 9. Execution strategies

```python
class ExecutionStrategy(Protocol):
    def next_slice(self, state: MarketState, remaining: int, t: int) -> list[OrderRequest]: ...
```

- **Market**: one market order.
- **TWAP**: N equal slices over duration D.
- **VWAP**: slice sizes proportional to a volume curve (U-shaped intraday curve default).
- **Passive limit**: post at best bid/ask, re-peg on price move, fall back to market after timeout.
- Compare on: avg price, implementation shortfall, std dev across Monte Carlo runs, fill ratio.

---

## 10. Charges module

`charges.yaml` (illustrative structure; **fill in current official rates and set `as_of`**):

```yaml
as_of: "YYYY-MM-DD"        # update when you verify
source_note: "Verify current rates on NSE, SEBI and your broker's website."
equity_delivery:
  brokerage: { type: flat_or_percent, value: 0 }
  stt: { buy_pct: 0, sell_pct: 0 }
  exchange_txn_pct: 0
  sebi_fee_per_crore: 0
  stamp_duty_buy_pct: 0
  gst_pct_on: [brokerage, exchange_txn, sebi_fee]
equity_intraday:
  # same keys
```

- Leave the numbers as placeholders in the repo until you verify them from official sources. Show the `as_of` date in the UI next to the charges breakdown.
- `calculate(side, notional, product_type) -> ChargesBreakdown` returns each component and total.

---

## 11. API specification

Base path `/api/v1`. All money in responses: paise (int) plus a formatted rupee string.

| Method | Path | Purpose |
|---|---|---|
| GET | `/profiles` | List stock profiles |
| POST | `/sessions` | Create session `{profile, seed, warmup_seconds, overrides?}` returns `session_id` |
| GET | `/sessions/{id}` | Session metadata |
| GET | `/sessions/{id}/book?depth=10` | Current book ladder, spread, mid |
| POST | `/sessions/{id}/orders` | Submit order `{side, type, qty, price?}` returns fills and events |
| DELETE | `/sessions/{id}/orders/{order_id}` | Cancel |
| POST | `/sessions/{id}/advance` | Advance simulated time `{seconds}` with flow |
| POST | `/impact/simulate` | Hypothetical order on a session snapshot, no mutation |
| POST | `/experiments` | Start experiment `{type, params, seed, runs}` returns `experiment_id` |
| GET | `/experiments/{id}` | Status and results |
| GET | `/sessions/{id}/events?from_seq=` | Event log (for replay) |
| GET | `/health` | Liveness |
| WS | `/ws/sessions/{id}` | Streams book updates and trades |

`/impact/simulate` request:

```json
{
  "session_id": "...",
  "side": "BUY",
  "size": { "mode": "shares", "value": 400 },
  "mode": "static",
  "product_type": "equity_delivery",
  "strategy": { "name": "market" }
}
```

Response includes: avg price, filled qty, fill ratio, slippage (Rs / % / bps, vs best and vs mid), price impact bps, levels consumed with per-level fills, charges breakdown, all-in cost, and a `disclaimer` string.

Errors: consistent JSON `{ "error": { "code", "message" } }`, with 422 for validation, 404 for unknown session, 429 for rate limiting.

---

## 12. Database schema (Postgres)

```
stock_profiles(id, name, params_json, created_at)
sessions(id, user_id nullable, profile_id, seed, config_json, status, created_at)
events(session_id, seq, ts, kind, payload_json, PRIMARY KEY(session_id, seq))
experiments(id, user_id nullable, type, params_json, seed, status, created_at, finished_at)
experiment_runs(id, experiment_id, run_index, seed, metrics_json)
experiment_results(experiment_id, summary_json, charts_json)
users(id, email, created_at)          -- v1 only
```

Index `events(session_id, seq)`. Store the code version (git SHA) in `experiments.params_json` for reproducibility.

---

## 13. Frontend specification

### Pages

1. **Landing `/`**: one-line pitch, "Try the simulator" button, disclaimer strip.
2. **Simulator `/simulator`**: profile picker, order book ladder (top 10), live depth chart, trade tape, order ticket, spread and mid display, "advance time" controls.
3. **Impact `/impact`**: order size input (shares or rupees), side toggle, **what-if slider** that updates the slippage curve, result card (avg price, slippage, impact, charges, all-in), comparison of profiles.
4. **Experiments `/experiments`**: choose experiment type (size sweep, spread sweep, depth sweep, strategy comparison), runs and seed, progress bar, results with confidence bands, CSV export.
5. **Replay `/replay/[sessionId]`**: play/pause/speed, book + trades animate from the event log.
6. **About `/about`**: methodology, assumptions, limitations, disclaimer, charges "as of" date.

### UI rules

- Format rupees with Indian grouping (`₹1,00,000`); helper in `lib/format.ts` using `toLocaleString('en-IN')`.
- Green for bids, red for asks, but add shape/labels so it is color-blind safe.
- Every results view shows the disclaimer.
- Loading and error states for every request.
- Responsive down to phone width; charts resize.
- Depth chart: cumulative quantity step-lines for bids and asks around mid.

---

## 14. Step-by-step build plan with prompts

Each step lists **goal, files, prompt to paste, and done-when**. Do them in order.

### Step 0: Project setup
### Step 1: Engine models and book
### Step 2: Matching engine (tests first)
### Step 3: Event log and deterministic replay
### Step 4: Impact calculator (static)
### Step 5: Charges module
### Step 6: Stock profiles and synthetic order flow
### Step 7: CLI demo and first experiment
### Step 8: Execution strategies
### Step 9: Experiments and Monte Carlo
### Step 10: FastAPI layer
### Step 11: Frontend foundation
### Step 12: Simulator and Impact pages
### Step 13: Persistence and replay
### Step 14: Experiments UI and reports
### Step 15: Hardening, auth, deploy
### Step 16: Benchmarks and write-up

---

## 15. Progress checklist

- [ ] 0 Setup
- [ ] 1 Models and book
- [ ] 2 Matching engine
- [ ] 3 Event log and replay
- [ ] 4 Static impact calculator
- [ ] 5 Charges
- [ ] 6 Profiles and synthetic flow
- [ ] 7 CLI and first sweep
- [ ] 8 Execution strategies
- [ ] 9 Experiments and Monte Carlo
- [ ] 10 FastAPI
- [ ] 11 Frontend foundation
- [ ] 12 Simulator and Impact pages
- [ ] 13 Persistence and replay UI
- [ ] 14 Experiments UI and reports
- [ ] 15 Hardening, auth, deploy
- [ ] 16 Benchmarks and write-up

---

## 16. Definition of done (every step)

1. Tests for the step are written and passing.
2. `ruff`, `mypy` (and ESLint for frontend) are clean.
3. No rule in Section 3 is violated.
4. Docs or README updated if behavior changed.
5. Committed with a clear message: `step N: <what changed>`.

## 17. Debugging playbook

- **Book looks crossed:** an invariant failed; run the Hypothesis test, shrink the failing sequence, add it as a regression test.
- **Results differ between runs:** something non-deterministic leaked in (global random, dict ordering from unsorted input, time). Search for `random.` and `time.`.
- **Float noise in money:** a float crept in; convert back to integer paise.
- **Slow Monte Carlo:** profile with `cProfile`, check deep-copy cost, consider snapshotting only the top N levels for static mode.
- **WebSocket floods the UI:** throttle updates to 10 per second and send diffs.
- **AI keeps rewriting finished code:** tell it which files are frozen, and ask for minimal diffs.

## 18. Prompting tips for vibe coding this project

- Give the AI one step, the relevant spec section, and the acceptance criteria.
- Ask it to **write tests first** for the engine and impact modules.
- After each step, ask: *"List assumptions you made that are not in context.md."*
- Ask for small diffs and run tests before accepting changes.
- Commit after every green step so you can roll back.
- When something is unclear, ask the AI to propose options before coding.

## 19. Legal and wording guardrails

- Footer on every results page: *"Simulated results using synthetic data and simplifying assumptions. Not investment advice. Real execution costs will differ."*
- Do not use or redistribute NSE/BSE data without a license.
- Verify current SEBI rules before adding live trading or recommendations.
- Show the charges `as_of` date and tell users to verify rates.

## 20. Environment setup (quick start)

```bash
# backend
cd backend
python -m venv .venv
.venv\Scripts\activate   # Windows
pip install -e ".[dev]"
pytest

# frontend
cd ../frontend
npm install
npm run dev
```
