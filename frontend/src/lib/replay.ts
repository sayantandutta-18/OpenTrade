/**
 * Replay engine for stepping through event logs and reconstructing order book states.
 */

import { formatINR } from "./format";
import { TradeSchema } from "./api";

export interface ReplayLevel {
  price: number;
  price_formatted: string;
  qty: number;
  order_count: number;
}

export type ReplayTrade = TradeSchema;

export interface ReplayFrame {
  step: number;
  event: {
    seq: number;
    ts: number;
    kind: string;
    payload: Record<string, unknown>;
  };
  best_bid: number | null;
  best_bid_formatted: string;
  best_ask: number | null;
  best_ask_formatted: string;
  spread: number | null;
  spread_formatted: string;
  mid: number | null;
  mid_formatted: string;
  bids: ReplayLevel[];
  asks: ReplayLevel[];
  trades: ReplayTrade[];
}

interface RestingOrder {
  id: number;
  side: "BUY" | "SELL";
  price: number;
  qty: number;
}

/**
 * Pre-computes sequential snapshots from a raw list of engine events.
 */
export function buildReplayFrames(
  events: Array<{ seq: number; ts: number; kind: string; payload: Record<string, unknown> }>,
  depthLimit = 10
): ReplayFrame[] {
  const frames: ReplayFrame[] = [];

  // Price -> orderId -> qty
  const bidLevels = new Map<number, Map<number, number>>();
  const askLevels = new Map<number, Map<number, number>>();
  const restingOrders = new Map<number, RestingOrder>();
  const tradeHistory: ReplayTrade[] = [];
  let tradeSeq = 1;

  for (let i = 0; i < events.length; i++) {
    const ev = events[i];
    const p = ev.payload;

    if (ev.kind === "ACCEPTED") {
      const oid = Number(p.order_id);
      const side = String(p.side) as "BUY" | "SELL";
      const type = String(p.type);
      const price = p.price !== undefined && p.price !== null ? Number(p.price) : null;
      const qty = Number(p.qty);

      // Resting limit order
      if (type === "LIMIT" && price !== null && qty > 0) {
        restingOrders.set(oid, { id: oid, side, price, qty });
        const levelMap = side === "BUY" ? bidLevels : askLevels;
        if (!levelMap.has(price)) {
          levelMap.set(price, new Map());
        }
        levelMap.get(price)!.set(oid, qty);
      }
    } else if (ev.kind === "TRADE") {
      const makerOid = Number(p.maker_order_id);
      const takerOid = Number(p.taker_order_id);
      const price = Number(p.price);
      const qty = Number(p.qty);
      const takerSide = (String(p.taker_side) as "BUY" | "SELL") || "BUY";

      tradeHistory.unshift({
        id: Number(p.trade_id || tradeSeq++),
        price,
        price_formatted: formatINR(price),
        qty,
        taker_side: takerSide,
        ts: ev.ts,
        maker_order_id: makerOid || 0,
        taker_order_id: takerOid || 0,
      });

      // Deduct quantity from maker resting order
      const makerOrder = restingOrders.get(makerOid);
      if (makerOrder) {
        makerOrder.qty -= qty;
        const levelMap = makerOrder.side === "BUY" ? bidLevels : askLevels;
        const priceMap = levelMap.get(makerOrder.price);
        if (priceMap) {
          if (makerOrder.qty <= 0) {
            priceMap.delete(makerOid);
            restingOrders.delete(makerOid);
            if (priceMap.size === 0) {
              levelMap.delete(makerOrder.price);
            }
          } else {
            priceMap.set(makerOid, makerOrder.qty);
          }
        }
      }
    } else if (ev.kind === "CANCELED") {
      const oid = Number(p.order_id);
      const order = restingOrders.get(oid);
      if (order) {
        const levelMap = order.side === "BUY" ? bidLevels : askLevels;
        const priceMap = levelMap.get(order.price);
        if (priceMap) {
          priceMap.delete(oid);
          if (priceMap.size === 0) {
            levelMap.delete(order.price);
          }
        }
        restingOrders.delete(oid);
      }
    } else if (ev.kind === "MODIFIED") {
      const oid = Number(p.order_id);
      const order = restingOrders.get(oid);
      if (order) {
        const oldPrice = order.price;
        const newQty = p.new_qty !== undefined ? Number(p.new_qty) : order.qty;
        const newPrice = p.new_price !== undefined ? Number(p.new_price) : order.price;

        const levelMap = order.side === "BUY" ? bidLevels : askLevels;
        const oldPriceMap = levelMap.get(oldPrice);
        if (oldPriceMap) {
          oldPriceMap.delete(oid);
          if (oldPriceMap.size === 0) {
            levelMap.delete(oldPrice);
          }
        }

        order.qty = newQty;
        order.price = newPrice;
        if (!levelMap.has(newPrice)) {
          levelMap.set(newPrice, new Map());
        }
        levelMap.get(newPrice)!.set(oid, newQty);
      }
    }

    // Extract sorted bids (descending) and asks (ascending)
    const sortedBidPrices = Array.from(bidLevels.keys()).sort((a, b) => b - a);
    const sortedAskPrices = Array.from(askLevels.keys()).sort((a, b) => a - b);

    const bestBid = sortedBidPrices.length > 0 ? sortedBidPrices[0] : null;
    const bestAsk = sortedAskPrices.length > 0 ? sortedAskPrices[0] : null;
    const spread = bestBid !== null && bestAsk !== null ? bestAsk - bestBid : null;
    const mid = bestBid !== null && bestAsk !== null ? (bestBid + bestAsk) / 2 : null;

    const bids: ReplayLevel[] = sortedBidPrices.slice(0, depthLimit).map((price) => {
      const orders = bidLevels.get(price)!;
      let totalQty = 0;
      for (const q of orders.values()) totalQty += q;
      return {
        price,
        price_formatted: formatINR(price),
        qty: totalQty,
        order_count: orders.size,
      };
    });

    const asks: ReplayLevel[] = sortedAskPrices.slice(0, depthLimit).map((price) => {
      const orders = askLevels.get(price)!;
      let totalQty = 0;
      for (const q of orders.values()) totalQty += q;
      return {
        price,
        price_formatted: formatINR(price),
        qty: totalQty,
        order_count: orders.size,
      };
    });

    frames.push({
      step: i,
      event: ev,
      best_bid: bestBid,
      best_bid_formatted: formatINR(bestBid),
      best_ask: bestAsk,
      best_ask_formatted: formatINR(bestAsk),
      spread,
      spread_formatted: formatINR(spread),
      mid,
      mid_formatted: formatINR(mid),
      bids,
      asks,
      trades: [...tradeHistory.slice(0, 50)],
    });
  }

  return frames;
}
