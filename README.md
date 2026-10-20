

Readme · MD
<div align="center">
📈 ImpactLab
See what your trade really costs before you place it
A limit order book simulator with market impact analysis, built on NSE-style rules 🇮🇳

CI Python FastAPI Next.js TypeScript License: MIT

🚀 Quick Start · 🧪 Example · ✨ Features · 📊 Benchmarks · 🗺️ Roadmap

<!-- 📸 Add a screenshot or GIF here: docs/img/simulator.png --> </div>
⚠️ Disclaimer: ImpactLab is a simulation and education tool. Results use synthetic data and simplifying assumptions. They are not investment advice, and real execution costs will differ. Do not use or redistribute real exchange data without a license.

📚 Contents
🎯 What is it?	🧪 Example	✨ Features
🚀 Quick Start	💻 CLI	⚙️ How it works
🔌 API	🗂️ Layout	✅ Testing
📊 Benchmarks	🚧 Limitations	🗺️ Roadmap
🎯 What is ImpactLab?
💡 "If I trade this many shares of this stock right now, what will it actually cost me?"

Backtests often assume a flat slippage like 0.05%. In reality, cost depends on order size vs. book depth, bid-ask spread, how the book refills, and statutory charges.

ImpactLab simulates a price-time priority order book 📖, feeds it synthetic order flow 🌊, lets you place a hypothetical order 🛒, and reports the average fill price, slippage, price impact, and all-in cost in rupees 💰.

👥 Who is it for?
Who	What they get
🧑‍💻 Retail and algo traders	More realistic fill assumptions for backtests
🎓 Students	A hands-on way to learn market microstructure
📊 Analysts	One big order vs. sliced execution (TWAP, VWAP)
👀 Recruiters and reviewers	Clean architecture, tests, and benchmarks
🧪 A 30-second example
Take this book (tick size ₹0.05):

🔴 Side	💵 Price	📦 Qty
Ask	₹100.20	300
Ask	₹100.10	200
Ask	₹100.00	100
───	spread ₹0.10	───
Bid	₹99.90	100
Bid	₹99.80	200
Bid	₹99.70	300
🛒 A market BUY of 400 shares walks up the asks:

Fill	Price	Cost
100	₹100.00	₹10,000
200	₹100.10	₹20,020
100	₹100.20	₹10,020
✅ 400	avg ₹100.10	₹40,040
📉 You paid ₹0.10 more per share than the quoted ₹100.00 (10 bps of slippage). This exact case is a test in backend/tests/engine/test_reference_example.py.

🔑 The big idea: doubling your order size does not double your slippage. It gets worse faster, because each extra share eats a worse price level.

✨ Features
<table> <tr> <td width="50%" valign="top">
⚙️ Matching engine
🥇 Price-time priority, partial fills, cancel, modify
🏷️ Limit, market, IOC, FOK, post-only orders
🔢 Integer paise arithmetic (no float errors)
🛡️ Invariants enforced and property-tested
🇮🇳 NSE-style rules
📏 ₹0.05 tick size and lot validation
🧾 Itemized charges: brokerage, STT, exchange fees, SEBI fee, stamp duty, GST
📅 Rates live in charges.yaml with an as_of date
</td> <td width="50%" valign="top">
🌊 Simulation
🎲 Poisson arrivals, log-normal sizes, cancellations
🤖 Market-maker agent
🏢 Large-cap, mid-cap, small-cap profiles
🔁 Fully deterministic: same seed, same result
🔬 Analysis
📸 Static impact (frozen book) and dynamic impact
⏱️ Market, TWAP, VWAP, passive limit strategies
🎰 Monte Carlo with p5 to p95 confidence bands
📥 CSV export
</td> </tr> </table>
🖥️ Dashboard (Next.js)
Page	What it does
📖	Simulator	Live order book ladder, depth chart, trade tape
🎚️	Impact	What-if slider: slippage vs. order size, plus charges
⏪	Replay	Play, pause, speed control, timeline scrubber
🧬	Experiments	Monte Carlo runs with confidence bands and CSV
ℹ️	About	Methodology, assumptions, limits, disclaimer
🚀 Quick Start
📋 Requirements
🐍 Python 3.12+
🟩 Node.js 20+
🐳 Docker and Docker Compose (optional)
🅰️ Option A: Local development
1️⃣ Backend

bash
cd backend
python -m venv .venv
source .venv/bin/activate          # Windows: .\.venv\Scripts\activate
pip install -e ".[dev]"
pytest
uvicorn impactlab.api.main:app --reload --port 8000
2️⃣ Frontend

bash
cd frontend
npm install
npm run dev
3️⃣ Open it 🎉

🔗	URL
🖥️ App	http://localhost:3000
📘 API docs (Swagger)	http://localhost:8000/docs
🅱️ Option B: Docker Compose
bash
docker compose up --build
🧩 Starts the API, database, Redis, and frontend in one command.

<details> <summary>🔐 <b>Environment variables</b> (click to expand)</summary> <br>
Copy .env.example to .env. Never commit .env.

DATABASE_URL=sqlite:///./impactlab.db      # or a PostgreSQL URL
REDIS_URL=redis://localhost:6379/0
CORS_ORIGINS=http://localhost:3000
SECRET_KEY=change-me
</details>
💻 CLI
Run experiments from the terminal, no browser needed:

bash
# 📖 Print the live order book ladder
python -m impactlab.cli book --profile mid_cap --warmup 15

# 🛒 Estimate impact of a hypothetical order
python -m impactlab.cli impact --profile mid_cap --side BUY --shares 1000

# 📈 Sweep several sizes and save to CSV
python -m impactlab.cli sweep --profile mid_cap --sizes 100,500,1000,2500,5000 --out sweep.csv
⚙️ How it works
 🌊 Synthetic flow ──► ⚙️ Matching engine ──► 📜 Event log ──► 🔬 Analysis
   (seeded Poisson)     (price-time priority,   (JSONL, the      (static + dynamic
                         integer paise)          source of truth)  impact, Monte Carlo)
Step	What happens
1️⃣ Engine	Pure Python, no network, disk, or UI code. Sorted price levels with FIFO queues.
2️⃣ Event log	Every state change is an event, so any book can be rebuilt exactly.
3️⃣ Flow	A seeded simulator creates limit orders, market orders, and cancels around a drifting mid price.
4️⃣ Impact	Metrics come from the fills, then statutory charges are added.
5️⃣ Experiments	Many seeds run in parallel. Child seeds come from one master seed, so results are reproducible.
🧮 Key formulas (buy side)
avg_price        = Σ(price × qty) / Σ(qty)
slippage_vs_best = avg_price − best_ask
slippage_vs_mid  = avg_price − arrival_mid
price_impact_bps = (post_mid − arrival_mid) / arrival_mid × 10,000
🔌 API
Base path /api/v1 · 📘 interactive docs at /docs

Method	Path	Purpose
🟢 GET	/profiles	List stock profiles
🟡 POST	/sessions	Create a simulation session
🟢 GET	/sessions/{id}/book	Current order book ladder
🟡 POST	/sessions/{id}/orders	Submit an order
🔴 DELETE	/sessions/{id}/orders/{order_id}	Cancel an order
🟡 POST	/sessions/{id}/advance	Advance simulated time
🟡 POST	/impact/simulate	Hypothetical order, live book untouched
🟡 POST	/experiments	Start a Monte Carlo experiment
🟢 GET	/experiments/{id}	Experiment status and results
🟢 GET	/sessions/{id}/events	Event log (for replay)
🔵 WS	/ws/sessions/{id}	Live book and trade stream
🗂️ Project layout
impactlab/
├── 🐍 backend/
│   ├── benchmarks/          # ⏱️ throughput and latency scripts
│   ├── src/impactlab/
│   │   ├── engine/          # ⚙️ matching engine (pure, no I/O)
│   │   ├── impact/          # 🎯 static and dynamic impact
│   │   ├── flow/            # 🌊 synthetic flow and stock profiles
│   │   ├── execution/       # ⏱️ TWAP, VWAP, passive limit
│   │   ├── charges/         # 🧾 statutory charges + charges.yaml
│   │   ├── experiments/     # 🎰 Monte Carlo and statistics
│   │   ├── db/              # 🗄️ SQLAlchemy models and repos
│   │   ├── api/             # 🔌 FastAPI, WebSocket, rate limiting
│   │   └── cli.py           # 💻 terminal tool
│   └── tests/               # ✅ unit, property-based, golden-replay
├── 🖥️ frontend/
│   └── src/
│       ├── app/             # 📄 simulator, impact, replay, experiments, about
│       └── components/      # 🧩 charts and UI
├── 📝 docs/findings.md      # 🔬 experiment write-up
├── 🐳 docker-compose.yml
├── 📋 PRD.md                # product requirements
└── 🧭 context.md            # build guide
✅ Testing
bash
cd backend
pytest                       # 🧪 all tests
pytest --cov=impactlab       # 📊 with coverage
ruff check . && mypy src     # 🧹 lint and type checks
🧪 The suite has unit tests, Hypothesis property-based tests for book invariants, and golden-file tests that check a fixed scenario replays to an identical event log.

📊 Benchmarks
Measured on an x86_64 laptop with Python 3.14 using backend/benchmarks/benchmark_engine.py:

⚡ Metric	🏁 Result
Matching engine throughput	96,081 orders/sec 🚀
Latency p50	3.90 µs
Latency p95	12.50 µs
Latency p99	23.30 µs
Static impact walk	238,915 walks/sec (4.19 µs each)
🎯 The PRD target was at least 50,000 orders/sec. Numbers vary by machine, so run the script yourself before comparing.

🔬 Experiment results: docs/findings.md

🚧 Limitations
🧐 Please read before trusting any number.

⚠️ Limitation	Details
🎭 Synthetic data	Profiles use illustrative parameters, not calibration to real NSE/BSE order book data (licensed and expensive).
🧩 Simplified market	No latency model, no hidden or iceberg liquidity, and only simple agents react to your order.
🧾 Charges change	Check the as_of date in charges.yaml and verify rates with NSE, SEBI, and your broker.
🚫 Not advice	It describes simulated costs. It never recommends trades.
⚖️ Regulation	SEBI rules on algo trading and advisory change. Check them before adding live trading or recommendations.
🗺️ Roadmap
 📐 Almgren-Chriss optimal execution
 √ Square-root impact law check
 🚦 Circuit-limit scenarios and pre-open auction
 📑 F&O mode with lot sizes
 🎯 Calibration against licensed data
 🦀 Rust hot path via PyO3
 🤖 Reinforcement learning execution agent
 💬 LLM explainer for results
🤝 Contributing
Contributions are welcome! 💙

🍴 Fork the repo and create a branch: git checkout -b feature/your-change
🧪 Write tests first for engine or impact changes
✅ Make sure pytest, ruff, and mypy pass
📬 Open a pull request describing what changed and why
📏 Ground rules: engine prices are integer paise · all randomness is seeded · the engine stays free of I/O · UI copy never gives buy or sell advice.

📄 License
MIT. See LICENSE.

<div align="center">
⭐ If ImpactLab helped you, give it a star! ⭐

Built for market microstructure research and execution education 📈

</div>

Claude finished the response
