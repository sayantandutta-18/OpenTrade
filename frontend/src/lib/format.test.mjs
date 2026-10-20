import test from "node:test";
import assert from "node:assert";
import { formatRupees, formatLakhCrore, formatShares, formatBps, formatPrice } from "./format.ts";

test("formatRupees handles standard paise amounts", () => {
  // 10000 paise = Rs 100.00
  const formatted = formatRupees(10000);
  assert.ok(formatted.includes("100.00"));
});

test("formatLakhCrore formats Crores and Lakhs correctly", () => {
  // 1 Crore = 10,000,000 Rupees = 1,000,000,000 paise
  const cr = formatLakhCrore(1_000_000_000);
  assert.strictEqual(cr, "₹1.00 Cr");

  // 2.5 Lakh = 250,000 Rupees = 25,000,000 paise
  const lk = formatLakhCrore(25_000_000);
  assert.strictEqual(lk, "₹2.50 L");
});

test("formatShares formats integer with commas", () => {
  assert.strictEqual(formatShares(50000), "50,000");
  assert.strictEqual(formatShares(0), "0");
});

test("formatBps formats basis points", () => {
  assert.strictEqual(formatBps(10.5), "10.50 bps");
  assert.strictEqual(formatBps(null), "0.00 bps");
});

test("formatPrice formats price with rupee prefix", () => {
  assert.strictEqual(formatPrice(10000), "₹100.00");
  assert.strictEqual(formatPrice(null), "-");
});
