/**
 * API client for ImpactLab backend.
 */

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export interface StockProfile {
  name: string;
  description: string;
  reference_price: number;
  reference_price_formatted: string;
  tick_size: number;
  lot_size: number;
  typical_spread_ticks: number;
  target_depth_shares: number;
  limit_arrival_rate: number;
  market_arrival_rate: number;
  cancel_rate: number;
  daily_volatility_pct: number;
}

export interface LevelSchema {
  price: number;
  price_formatted: string;
  qty: number;
  order_count: number;
}

export interface BookResponse {
  session_id: string;
  ts: number;
  best_bid: number | null;
  best_bid_formatted: string;
  best_ask: number | null;
  best_ask_formatted: string;
  spread: number | null;
  spread_formatted: string;
  mid: number | null;
  mid_formatted: string;
  bids: LevelSchema[];
  asks: LevelSchema[];
}

export interface SessionResponse {
  session_id: string;
  profile: string;
  seed: number;
  warmup_seconds: number;
  current_time_us: number;
  best_bid: number | null;
  best_ask: number | null;
  spread: number | null;
  mid: number | null;
  created_at: string;
}

export interface SessionSummary {
  id: string;
  profile: string;
  seed: number;
  status: string;
  created_at: string;
  event_count: number;
}

export interface EventSchema {
  seq: number;
  ts: number;
  kind: "ACCEPTED" | "TRADE" | "CANCELED" | "REJECTED" | "MODIFIED";
  payload: Record<string, unknown>;
}

export interface ReplayVerifyResponse {
  session_id: string;
  event_count: number;
  trade_count: number;
  reconstructed_best_bid: number | null;
  reconstructed_best_ask: number | null;
  reconstructed_best_bid_formatted: string;
  reconstructed_best_ask_formatted: string;
  live_best_bid: number | null;
  live_best_ask: number | null;
  verified_deterministic: boolean;
}

export interface TradeSchema {
  id: number;
  price: number;
  price_formatted: string;
  qty: number;
  taker_order_id: number;
  maker_order_id: number;
  taker_side: "BUY" | "SELL";
  ts: number;
}

export interface OrderSubmitResponse {
  order_id: number;
  status: string;
  filled_qty: number;
  remaining: number;
  trades: TradeSchema[];
}

export interface AdvanceResponse {
  session_id: string;
  advanced_seconds: number;
  events_generated: number;
  current_time_us: number;
  book: BookResponse;
}

export interface LevelFillSchema {
  price: number;
  price_formatted: string;
  qty: number;
  notional: number;
  notional_formatted: string;
}

export interface ChargesSchema {
  product_type: string;
  brokerage: number;
  brokerage_formatted: string;
  stt: number;
  stt_formatted: string;
  exchange_txn_fee: number;
  exchange_txn_fee_formatted: string;
  sebi_fee: number;
  sebi_fee_formatted: string;
  stamp_duty: number;
  stamp_duty_formatted: string;
  gst: number;
  gst_formatted: string;
  total_charges: number;
  total_charges_formatted: string;
  as_of: string;
  source_note: string;
}

export interface ImpactSimulateResponse {
  session_id: string;
  side: "BUY" | "SELL";
  mode: string;
  requested_qty: number;
  filled_qty: number;
  unfilled_qty: number;
  fill_ratio: number;
  total_notional: number;
  total_notional_formatted: string;
  avg_price: number | null;
  avg_price_formatted: string;
  arrival_best: number | null;
  arrival_best_formatted: string;
  arrival_mid: number | null;
  arrival_mid_formatted: string;
  post_mid: number | null;
  post_mid_formatted: string;
  slippage_vs_best: number | null;
  slippage_vs_best_formatted: string;
  slippage_vs_mid: number | null;
  slippage_vs_mid_formatted: string;
  slippage_bps: number | null;
  price_impact_bps: number | null;
  impl_shortfall: number | null;
  impl_shortfall_formatted: string;
  levels_consumed: number;
  level_fills: LevelFillSchema[];
  charges: ChargesSchema;
  all_in_cost: number;
  all_in_cost_formatted: string;
  disclaimer: string;
}

export interface ExperimentSummary {
  experiment_id: string;
  experiment_type: string;
  status: string;
  master_seed: number;
  created_at: string;
}

export interface ExperimentResponse {
  experiment_id: string;
  experiment_type: string;
  status: string;
  master_seed: number;
  runs: number;
  summary: Record<string, unknown>;
  chart_data: Array<Record<string, unknown>>;
}

async function handleResponse<T>(res: Response): Promise<T> {
  if (!res.ok) {
    let errMsg = `Request failed: ${res.status} ${res.statusText}`;
    try {
      const errJson = await res.json();
      if (errJson?.error?.message) {
        errMsg = errJson.error.message;
      }
    } catch {
      // ignore
    }
    throw new Error(errMsg);
  }
  return res.json() as Promise<T>;
}

export const api = {
  async getProfiles(): Promise<StockProfile[]> {
    const res = await fetch(`${API_BASE}/api/v1/profiles`);
    return handleResponse<StockProfile[]>(res);
  },

  async createSession(
    profile = "mid_cap",
    seed = 1,
    warmupSeconds = 30.0
  ): Promise<SessionResponse> {
    const res = await fetch(`${API_BASE}/api/v1/sessions`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        profile,
        seed,
        warmup_seconds: warmupSeconds,
      }),
    });
    return handleResponse<SessionResponse>(res);
  },

  async getSession(sessionId: string): Promise<SessionResponse> {
    const res = await fetch(`${API_BASE}/api/v1/sessions/${sessionId}`);
    return handleResponse<SessionResponse>(res);
  },

  async getBook(sessionId: string, depth = 10): Promise<BookResponse> {
    const res = await fetch(
      `${API_BASE}/api/v1/sessions/${sessionId}/book?depth=${depth}`
    );
    return handleResponse<BookResponse>(res);
  },

  async submitOrder(
    sessionId: string,
    order: {
      side: "BUY" | "SELL";
      type: string;
      qty: number;
      price?: number;
      owner?: string;
    }
  ): Promise<OrderSubmitResponse> {
    const res = await fetch(`${API_BASE}/api/v1/sessions/${sessionId}/orders`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(order),
    });
    return handleResponse<OrderSubmitResponse>(res);
  },

  async cancelOrder(sessionId: string, orderId: number): Promise<{ status: string }> {
    const res = await fetch(
      `${API_BASE}/api/v1/sessions/${sessionId}/orders/${orderId}`,
      {
        method: "DELETE",
      }
    );
    return handleResponse<{ status: string }>(res);
  },

  async advanceTime(sessionId: string, seconds = 1.0): Promise<AdvanceResponse> {
    const res = await fetch(`${API_BASE}/api/v1/sessions/${sessionId}/advance`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ seconds }),
    });
    return handleResponse<AdvanceResponse>(res);
  },

  async simulateImpact(params: {
    session_id: string;
    side: "BUY" | "SELL";
    size: { mode: "shares" | "rupees"; value: number };
    mode?: "static" | "dynamic";
    product_type?: string;
    strategy?: { name: string; duration_seconds?: number; num_slices?: number };
  }): Promise<ImpactSimulateResponse> {
    const res = await fetch(`${API_BASE}/api/v1/impact/simulate`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        mode: "static",
        product_type: "equity_delivery",
        strategy: { name: "market" },
        ...params,
      }),
    });
    return handleResponse<ImpactSimulateResponse>(res);
  },

  async createExperiment(params: {
    type: string;
    params: Record<string, unknown>;
    seed?: number;
    runs?: number;
  }): Promise<ExperimentResponse> {
    const res = await fetch(`${API_BASE}/api/v1/experiments`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        seed: 42,
        runs: 50,
        ...params,
      }),
    });
    return handleResponse<ExperimentResponse>(res);
  },

  async getExperiment(experimentId: string): Promise<ExperimentResponse> {
    const res = await fetch(`${API_BASE}/api/v1/experiments/${experimentId}`);
    return handleResponse<ExperimentResponse>(res);
  },

  async listExperiments(limit = 20): Promise<ExperimentSummary[]> {
    const res = await fetch(`${API_BASE}/api/v1/experiments?limit=${limit}`);
    return handleResponse<ExperimentSummary[]>(res);
  },

  async listSessions(limit = 50): Promise<SessionSummary[]> {
    const res = await fetch(`${API_BASE}/api/v1/sessions?limit=${limit}`);
    return handleResponse<SessionSummary[]>(res);
  },

  async replayVerify(sessionId: string): Promise<ReplayVerifyResponse> {
    const res = await fetch(
      `${API_BASE}/api/v1/sessions/${sessionId}/replay_verify`
    );
    return handleResponse<ReplayVerifyResponse>(res);
  },

  async getEvents(sessionId: string, fromSeq = 1): Promise<EventSchema[]> {
    const res = await fetch(
      `${API_BASE}/api/v1/sessions/${sessionId}/events?from_seq=${fromSeq}`
    );
    return handleResponse<EventSchema[]>(res);
  },
};
