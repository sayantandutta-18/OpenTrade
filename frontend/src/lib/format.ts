/**
 * Indian currency formatting utilities (Rupees, Lakhs, Crores)
 * Prices and notionals received from backend are in integer paise (1 Rupee = 100 paise).
 */

export function formatRupees(paise: number | null | undefined): string {
  if (paise === null || paise === undefined || isNaN(paise)) {
    return "₹0.00";
  }
  const rupees = paise / 100;
  return new Intl.NumberFormat("en-IN", {
    style: "currency",
    currency: "INR",
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(rupees);
}

export const formatINR = formatRupees;

export function formatLakhCrore(paise: number | null | undefined): string {
  if (paise === null || paise === undefined || isNaN(paise)) {
    return "₹0.00";
  }
  const rupees = paise / 100;
  const absRupees = Math.abs(rupees);
  const sign = rupees < 0 ? "-" : "";

  if (absRupees >= 10_000_000) {
    const crores = absRupees / 10_000_000;
    return `${sign}₹${crores.toFixed(2)} Cr`;
  }
  if (absRupees >= 100_000) {
    const lakhs = absRupees / 100_000;
    return `${sign}₹${lakhs.toFixed(2)} L`;
  }
  return formatRupees(paise);
}

export function formatShares(qty: number | null | undefined): string {
  if (qty === null || qty === undefined || isNaN(qty)) {
    return "0";
  }
  return new Intl.NumberFormat("en-IN").format(Math.round(qty));
}

export function formatBps(bps: number | null | undefined): string {
  if (bps === null || bps === undefined || isNaN(bps)) {
    return "0.00 bps";
  }
  return `${bps.toFixed(2)} bps`;
}

export function formatPrice(paise: number | null | undefined): string {
  if (paise === null || paise === undefined || isNaN(paise)) {
    return "-";
  }
  const rupees = paise / 100;
  return `₹${rupees.toFixed(2)}`;
}
