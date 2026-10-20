# ImpactLab 📈

> Limit Order Book Simulator with Market Impact Analysis (NSE-style).

[![CI](https://github.com/opentrade/impactlab/actions/workflows/ci.yml/badge.svg)](https://github.com/opentrade/impactlab/actions/workflows/ci.yml)

ImpactLab is a web application and research framework that simulates a price-time priority limit order book for Indian equities (NSE-style rules), feeds it synthetic order flow, and lets you measure what it actually costs to execute hypothetical orders: average fill price, slippage, price impact, and total costs including Indian statutory trading charges.

> **Disclaimer**: *Results are produced by a simulation using synthetic data and simplifying assumptions. Not investment advice. Real execution costs will differ.*

---

## Architecture

- **Engine**: Pure Python price-time priority matching engine (integer paise prices, deterministic event log).
- **Impact Calculator**: Static book walks and dynamic execution simulation with Poisson order flow.
- **Backend API**: FastAPI, WebSockets, Pydantic v2, PostgreSQL / SQLite.
- **Frontend**: Next.js 15, TypeScript, Tailwind CSS, Recharts, shadcn-inspired components.

---

## Quick Start

### Backend

```bash
cd backend
python -m venv .venv
# On Windows:
.\.venv\Scripts\activate
# On Unix/macOS:
source .venv/bin/activate

pip install -e ".[dev]"
pytest
uvicorn impactlab.api.main:app --reload --port 8000
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Visit [http://localhost:3000](http://localhost:3000) for the UI and [http://localhost:8000/docs](http://localhost:8000/docs) for the interactive Swagger API documentation.
