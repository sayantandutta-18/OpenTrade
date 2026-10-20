# ImpactLab 📈

> **High-Performance Limit Order Book Simulator & Market Impact Analysis (NSE-Style)**

[![CI](https://github.com/opentrade/impactlab/actions/workflows/ci.yml/badge.svg)](https://github.com/opentrade/impactlab/actions/workflows/ci.yml)
[![Python 3.12+](https://img.shields.io/badge/python-3.12%2B-blue.svg)](https://www.python.org/)
[![Next.js 15](https://img.shields.io/badge/next.js-15-black.svg)](https://nextjs.org/)
[![TypeScript 5](https://img.shields.io/badge/typescript-5-blue.svg)](https://www.typescriptlang.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.110%2B-009688.svg)](https://fastapi.tiangolo.com/)

---

> **Important Legal Disclaimer:**  
> *Results are produced by a simulation using synthetic data and simplifying assumptions. Not investment advice. Real execution costs will differ. Do not use or redistribute real exchange data without a license.*

---

## 1. What is ImpactLab?

ImpactLab answers one core question:  
**"If I trade this quantity of this Indian equity right now, what will it really cost me?"**

Retail traders and algo backtests often assume an arbitrary fixed slippage (e.g., 0.05%). Real execution cost depends non-linearly on order size relative to order book depth, bid-ask spread, queue position, market resilience, and statutory trading fees.

ImpactLab provides:
1. **Price-Time Priority Matching Engine**: Pure Python, zero float-rounding errors (integer paise arithmetic), strict runtime invariants, and deterministic event serialization.
2. **Indian Market Microstructure Rules**: NSE ₹0.05 tick size, lot sizes, itemized statutory charges (STT, Exchange Txn Fees, SEBI turnover fees, Stamp Duty, and 18% GST).
3. **Synthetic Order Flow**: Poisson arrival processes, log-normal order sizing, and symmetric Market Maker quoting agents calibrated across Large-Cap, Mid-Cap, and Small-Cap profiles.
4. **Static & Dynamic Impact Analysis**: Instantaneous frozen book walks and dynamic multi-strategy simulations (TWAP, VWAP, Passive Limit).
5. **Monte Carlo Experiments**: Parallel sweeps with reproducible child seeds (`SeedSequence`), confidence bands ($p_5 - p_{95}$), and CSV export.
6. **Deterministic Event Replay**: Reconstructs byte-identical order books from persistent event logs with an interactive timeline scrubber and speed controls.
7. **Production-Grade Next.js Dashboard**: Real-time Order Book Depth Ladder, Depth Chart, Trade Tape, What-If Slider, and statistical summary reporting.

---

## 2. Benchmark Results

Measured on an x86_64 laptop with Python 3.14 (`backend/benchmarks/benchmark_engine.py`):

| Metric | PRD Target | Measured Result |
|---|---|---|
| **Matching Engine Throughput** | $\ge 50,000$ orders/sec | **96,081 orders/sec** |
| **Median Execution Latency (p50)** | $< 20.0 \ \mu\text{s}$ | **3.90 $\mu\text{s}$** |
| **95th Percentile Latency (p95)** | $< 50.0 \ \mu\text{s}$ | **12.50 $\mu\text{s}$** |
| **99th Percentile Latency (p99)** | $< 100.0 \ \mu\text{s}$ | **23.30 $\mu\text{s}$** |
| **Static Impact Walk Throughput** | $\ge 20,000$ walks/sec | **238,915 walks/sec** (4.19 $\mu\text{s}$/walk) |

See the full empirical analysis in [`docs/findings.md`](docs/findings.md).

---

## 3. Architecture & Monorepo Layout

```
impactlab/
├── backend/
│   ├── benchmarks/               # Throughput & latency benchmarking suite
│   ├── src/impactlab/
│   │   ├── engine/               # PURE ENGINE: Price-time priority, integer paise, no I/O
│   │   ├── impact/               # Static walks & dynamic what-if simulation
│   │   ├── flow/                 # Synthetic Poisson flow & stock profile presets
│   │   ├── execution/            # Execution strategies (TWAP, VWAP, Passive Limit)
│   │   ├── charges/              # Indian statutory charges module & charges.yaml
│   │   ├── experiments/          # Monte Carlo parallel sweeps & statistical aggregation
│   │   ├── db/                   # SQLAlchemy models, SQLite/PostgreSQL session & repo
│   │   ├── api/                  # FastAPI REST routes, WebSockets & rate limiting
│   │   └── cli.py                # Standalone CLI demo tool
│   ├── tests/                    # Unit, Hypothesis property-based & golden tests (64 passed)
│   └── Dockerfile                # Multi-stage production container
├── frontend/
│   ├── src/app/
│   │   ├── simulator/            # Live order book ladder, depth chart, trade tape
│   │   ├── impact/               # Pre-trade impact what-if slider & charge breakdown
│   │   ├── replay/               # Interactive session replay with timeline scrubber
│   │   ├── experiments/          # Monte Carlo runner with confidence bands & CSV export
│   │   └── about/                # Microstructure methodology & regulatory disclaimer
│   ├── src/components/           # Modular Recharts & UI components
│   └── Dockerfile                # Next.js standalone container
├── docs/
│   └── findings.md               # Empirical research report on 6 PRD experiments
├── docker-compose.yml            # Full-stack composition (API, DB, Redis, Frontend)
├── context.md                    # 16-step implementation roadmap
└── PRD.md                        # Product requirements document
```

---

## 4. Quick Start

### Option A: Local Development

#### 1. Backend

```bash
cd backend
python -m venv .venv

# Windows:
.\.venv\Scripts\activate
# macOS/Linux:
source .venv/bin/activate

pip install -e ".[dev]"
pytest
uvicorn impactlab.api.main:app --reload --port 8000
```

#### 2. Frontend

```bash
cd frontend
npm install
npm run dev
```

Visit [http://localhost:3000](http://localhost:3000) for the UI and [http://localhost:8000/docs](http://localhost:8000/docs) for the interactive Swagger API documentation.

### Option B: Docker Compose

```bash
docker compose up --build
```

---

## 5. CLI Usage

ImpactLab includes a full-featured terminal CLI for headless research:

```bash
# View live order book ladder
python -m impactlab.cli book --profile mid_cap --warmup 15

# Calculate static impact for a hypothetical order
python -m impactlab.cli impact --profile mid_cap --side BUY --shares 1000

# Run a multi-size sweep and export results to CSV
python -m impactlab.cli sweep --profile mid_cap --sizes 100,500,1000,2500,5000 --out sweep.csv
```

---

## 6. Implementation Progress (All 16 Steps Complete)

- [x] **Step 0**: Repo layout, tooling, CI, docker-compose
- [x] **Step 1**: Engine models & OrderBook data structures (SortedDict + deque)
- [x] **Step 2**: Matching engine (price-time priority, FIFO, partial fills, cancellations)
- [x] **Step 3**: Event log & deterministic replay verification
- [x] **Step 4**: Static impact calculator (shares & rupee budget modes)
- [x] **Step 5**: Indian statutory charges module (`charges.yaml`)
- [x] **Step 6**: Stock profiles (Large/Mid/Small-cap) & synthetic Poisson order flow
- [x] **Step 7**: CLI demo tool & CSV export
- [x] **Step 8**: Execution strategies (TWAP, VWAP, Passive Limit) & dynamic impact
- [x] **Step 9**: Monte Carlo experiments runner with reproducible child seeds
- [x] **Step 10**: FastAPI REST endpoints & WebSocket streaming
- [x] **Step 11**: Frontend foundation, Indian number formatting, API client
- [x] **Step 12**: Simulator & Impact UI pages with depth chart & slippage curve
- [x] **Step 13**: Database persistence, session history, and timeline replay UI
- [x] **Step 14**: Experiments UI with confidence bands & CSV download
- [x] **Step 15**: Production hardening, Dockerfiles, rate limiting, and security headers
- [x] **Step 16**: Benchmarks (96k orders/sec) & empirical findings report (`docs/findings.md`)

---

## 7. License

MIT License. Designed and built for market microstructure research and algorithmic execution education.
