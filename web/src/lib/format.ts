export function money(x: number | null | undefined, decimals?: number): string {
  if (x === null || x === undefined || Number.isNaN(x)) return "n/a";
  const sign = x < 0 ? "−" : "";
  const v = Math.abs(x);
  if (v >= 1e6) return `${sign}$${(v / 1e6).toFixed(decimals ?? 2)}M`;
  if (v >= 1e3) return `${sign}$${Math.round(v / 1e3)}K`;
  return `${sign}$${Math.round(v).toLocaleString("en-US")}`;
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
