/** Money is an integer number of paise: 149900 means INR 1,499.00 */
export function formatINR(paise: number | null | undefined): string {
  return new Intl.NumberFormat("en-IN", { style: "currency", currency: "INR" }).format((paise ?? 0) / 100);
}

/** "1,499.50" or "1499.5" -> 149950. Returns NaN for bad input. */
export function rupeesToPaise(value: string): number {
  const clean = value.replace(/[,\s₹]/g, "");
  if (!/^\d+(\.\d{0,2})?$/.test(clean)) return Number.NaN;
  const [whole, frac = ""] = clean.split(".");
  return Number(whole) * 100 + Number((frac + "00").slice(0, 2));
}

export function formatDate(iso: string | null | undefined, withTime = false): string {
  if (!iso) return "—";
  const d = new Date(iso);
  return d.toLocaleString("en-IN", withTime
    ? { day: "2-digit", month: "short", hour: "2-digit", minute: "2-digit" }
    : { day: "2-digit", month: "short", year: "numeric" });
}
