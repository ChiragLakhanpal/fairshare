export function money(x: number | null | undefined, decimals?: number): string {
  if (x === null || x === undefined || Number.isNaN(x)) return "n/a";
  const sign = x < 0 ? "−" : "";
  const v = Math.abs(x);
  if (v >= 1e6) return `${sign}$${(v / 1e6).toFixed(decimals ?? 2)}M`;
  if (v >= 1e3) return `${sign}$${Math.round(v / 1e3)}K`;
  return `${sign}$${Math.round(v).toLocaleString("en-US")}`;
}
/** The breakdown's line on fair share under a why answer, from explain_change's summary row. A month whose seats repeat last year's
 * (seats_projected, until the DOT publishes it) has no seat comparison, so it gets no dollar figure. Fair share can also move with the
 * agency's mix of routes while each route's seat share stays put, so the move and what the seat shares alone are worth are said apart. */
export type FairShareRow = { seats_projected?: unknown; fair_share_now_pct: number; fair_share_prior_pct: number; fair_share_effect?: number | null };
export function fairShareLine(s: FairShareRow): string {
  if (s.seats_projected) return "This month's seats repeat the same month last year until the DOT publishes them, so there is no seat comparison.";
  const fair = s.fair_share_now_pct - s.fair_share_prior_pct;
  if (Math.abs(fair) < 0.05) return "Fair share did not move, so AA's own capacity explains none of it.";
  return `Fair share moved ${fair > 0 ? "up" : "down"} ${Math.abs(fair).toFixed(1)} points. Changes in AA's seat shares alone are worth ${money(s.fair_share_effect)}.`;
}
export function pct(x: number | null | undefined, digits = 1): string {
  if (x === null || x === undefined || Number.isNaN(x)) return "n/a";
  return `${x.toFixed(digits)}%`;
}
export function signed(x: number | null | undefined, digits = 1, unit = "%"): string {
  if (x === null || x === undefined || Number.isNaN(x)) return "n/a";
  return `${x < 0 ? "−" : "+"}${Math.abs(x).toFixed(digits)}${unit}`;
}
export function pts(x: number | null | undefined): string {
  if (x === null || x === undefined || Number.isNaN(x)) return "n/a";
  return `${x < 0 ? "−" : ""}${Math.abs(x).toFixed(1)} pts`;
}
const MONTHS = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"];
export function monthName(ym: string): string {
  const m = Number(ym.slice(5, 7));
  return MONTHS[m - 1] ?? ym;
}
export function monthLabel(ym: string): string {
  return `${monthName(ym)} ${ym.slice(0, 4)}`;
}
export function upDown(x: number | null | undefined, digits = 1): string {
  if (x === null || x === undefined || Number.isNaN(x)) return "no comparison";
  if (x === 0) return "unchanged";
  return `${x > 0 ? "up" : "down"} ${Math.abs(x).toFixed(digits)}%`;
}
export function todayLabel(d = new Date()): string {
  return d.toLocaleDateString("en-US", { weekday: "long", month: "long", day: "numeric", year: "numeric" });
}
export function greeting(name?: string | null, d = new Date()): string {
  const h = d.getHours();
  return `Good ${h < 12 ? "morning" : h < 18 ? "afternoon" : "evening"}${name ? `, ${name}` : ""}.`;
}
