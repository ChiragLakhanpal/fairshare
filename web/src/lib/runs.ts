// Words and states for agents, runs and items: the sidebar line, the stepper's states, the progress line, the approval
// line, scope names, decided lines. Pure functions, tested in runs.test.ts.
import { copy, minutesWord, numberWord } from "../copy";
import { monthLabel } from "./format";
import type { AgentDef, AgentScope, AgentStep, Item, ItemAction, Page, PageVersion, Progress, RunStatus } from "./types";

export function statusLabel(s: RunStatus): string {
  return ({ running: "Running", needs_approval: "Needs approval", approved: "Approved", rejected: "Rejected", failed: "Failed", superseded: "Replaced by a newer run" } as Record<string, string>)[s] ?? s;
}

export function draftCount(items: Pick<Item, "status">[]): number {
  return items.filter((i) => i.status === "draft").length;
}

/** What an agent produces, singular and plural: pages, alerts, briefs, notes. */
export function nounFor(key: string): [string, string] {
  return copy.nouns[key] ?? ["item", "items"];
}

export function scopeLabel(scope: AgentScope): string {
  if (scope.manager) return scope.month ? `${scope.manager}, ${monthLabel(scope.month)}` : scope.manager;
  if (scope.region) {
    const region = scope.region === "All" ? "all regions" : `the ${scope.region} region`;
    return scope.month ? `${region}, ${monthLabel(scope.month)}` : region;
  }
  return scope.market ?? "";
}

export function whenLabel(iso: string | null | undefined): string {
  if (!iso) return "";
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso;
  const day = d.toLocaleDateString("en-US", { month: "long", day: "numeric" });
  const time = d.toLocaleTimeString("en-US", { hour: "numeric", minute: "2-digit" });
  return `${day} at ${time}`;
}

export function dayLabel(iso: string | null | undefined): string {
  if (!iso) return "";
  const d = new Date(iso);
  return Number.isNaN(d.getTime()) ? iso : d.toLocaleDateString("en-US", { month: "long", day: "numeric" });
}

export function decidedLine(item: Pick<Item, "status" | "decided_by" | "decided_at">): string {
  if (item.status === "superseded") return copy.replacedPlain;
  const verb = item.status === "approved" ? "Approved" : "Rejected";
  const by = item.decided_by ? ` by ${item.decided_by}` : "";
  const when = item.decided_at ? ` on ${whenLabel(item.decided_at)}` : "";
  return `${verb}${by}${when}.`;
}

/** The short status at the right of a page row: waiting, or the decision and its day. */
export function pageLine(p: Pick<Page, "status" | "decided_at">): string {
  if (p.status === "draft") return copy.pageWaiting;
  if (p.status === "superseded") return copy.replacedPlain;
  return copy.rowDecided(p.status === "approved" ? "Approved" : "Rejected", dayLabel(p.decided_at));
}

/** "October 15 at 8:57 PM, for SEA-DEN": when a version was written and for what. */
export function versionLabel(v: Pick<PageVersion, "created_at" | "scope">): string {
  return `${whenLabel(v.created_at)}, for ${scopeLabel(v.scope)}`;
}

export function waitingLine(n: number): string {
  return copy.waitingLine(n);
}

export type StatusTone = "running" | "waiting" | "quiet" | "none" | "failed";

/** The one line under an agent's name in the sidebar. */
export function sidebarLine(a: Pick<AgentDef, "key" | "running" | "waiting" | "last_run">): { text: string; tone: StatusTone } {
  const [noun, nouns] = nounFor(a.key);
  if (a.running) {
    const p = a.running.progress;
    return { text: copy.sidebarRunning(Math.min(p.done + 1, Math.max(p.total, 1)), p.total, noun), tone: "running" };
  }
  if (a.waiting > 0) return { text: copy.sidebarWaiting(a.waiting, noun, nouns), tone: "waiting" };
  if (!a.last_run) return { text: copy.sidebarNotRun, tone: "none" };
  if (a.last_run.status === "failed") return { text: copy.sidebarFailed, tone: "failed" };
  return { text: copy.sidebarQuiet, tone: "quiet" };
}

export type StepState = "idle" | "current" | "done";

/** The stepper is the explanation when idle and the progress when a run exists: facts light every step before Draft,
 * draft lights Draft, check lights Check, a finished run waits on Approve, a decided run is all done. */
export function stepStates(steps: AgentStep[], run: { status: RunStatus; progress: Progress } | null): StepState[] {
  const n = steps.length;
  const at = (key: string, fallback: number) => {
    const i = steps.findIndex((s) => s.key === key);
    return i >= 0 ? i : fallback;
  };
  const draft = at("draft", Math.max(n - 3, 0));
  const check = at("check", Math.max(n - 2, 0));
  const approve = at("approve", Math.max(n - 1, 0));
  if (!run) return steps.map(() => "idle");
  if (run.status === "running") {
    const phase = run.progress.phase;
    if (phase === "draft") return steps.map((_, i) => (i < draft ? "done" : i === draft ? "current" : "idle"));
    if (phase === "check") return steps.map((_, i) => (i < check ? "done" : i === check ? "current" : "idle"));
    if (phase === "done") return steps.map((_, i) => (i < approve ? "done" : "idle"));
    return steps.map((_, i) => (i < draft ? "current" : "idle"));
  }
  if (run.status === "failed") return steps.map(() => "idle");
  if (run.status === "needs_approval") return steps.map((_, i) => (i < approve ? "done" : "current"));
  return steps.map(() => "done");
}

/** "Page 2 of 4: BlueSky Corporate Travel" while a run is going; null when there is nothing to count yet. */
export function progressLine(p: Progress, noun: string): string | null {
  if (!p.total) return null;
  return copy.pageOf(noun, Math.min(p.done + 1, p.total), p.total, p.item);
}

/** How far along the run is, for the thin bar: finished items plus a share of the one in progress. */
export function barFraction(p: Progress): number {
  if (!p.total) return 0;
  const within = p.phase === "facts" ? 0.15 : p.phase === "draft" ? 0.5 : p.phase === "check" ? 0.85 : 0;
  return Math.min(1, (p.done + within) / p.total);
}

export function approvalLine(a: ItemAction): string {
  if (a.type === "email") return copy.approveLineEmail(a.crm?.activity_type ?? null);
  if (a.type === "crm") return copy.approveLineCrm;
  return copy.approveLineNone;
}

export function startedToast(total: number | null, nouns: string): string {
  return copy.startedToast(total, nouns);
}

export type ProsePart = string | { raw: string; source: string | null; fact: string | null };

/** A sentence split around its checked numbers, in order, so each number can carry an underline and a title. */
export function proseParts(text: string, numbers: { raw: string; source: string | null; fact: string | null }[]): ProsePart[] {
  const out: ProsePart[] = [];
  let cursor = 0;
  for (const n of numbers) {
    const at = n.raw ? text.indexOf(n.raw, cursor) : -1;
    if (at < 0) continue;
    if (at > cursor) out.push(text.slice(cursor, at));
    out.push({ raw: n.raw, source: n.source, fact: n.fact });
    cursor = at + n.raw.length;
  }
  if (cursor < text.length) out.push(text.slice(cursor));
  return out;
}

// ponytail: the columns the four agents and the Ask tools return today; anything new falls through to the word splitter
const COLUMN_WORDS: Record<string, string> = {
  aa_revenue: "AA revenue", aa_revenue_prior: "AA revenue a year earlier", aa_revenue_prior_year: "AA revenue a year earlier", aa_pax: "AA passengers",
  aa_seat_share_pct: "AA's share of seats", aa_seats_now: "AA seats now", aa_seats_prior_year: "AA seats a year earlier",
  aa_share: "AA share", aa_share_pct: "AA share", aa_share_now_pct: "AA share", aa_share_prior_pct: "AA share a year earlier",
  agencies: "the number of agencies", amount_usd: "the deal amount", delta_revenue: "the change in revenue", fair_revenue: "revenue at exactly fair share",
  fair_share: "fair share", fair_share_pct: "fair share", fair_share_now_pct: "fair share", fair_share_prior_pct: "fair share a year earlier",
  fair_share_chg_pts: "the change in fair share", fair_share_effect: "the fair share effect",
  market_revenue: "market revenue, all carriers", market_revenue_now: "market revenue, all carriers", mix_effect: "the mix effect", months_in: "the months into the year", n: "the count",
  revenue_goal_usd: "the annual revenue goal", revenue_now: "revenue now", revenue_prior: "revenue a year earlier",
  revenue_vs_prior_year_pct: "the change from a year earlier", revenue_yoy_pct: "the change from a year earlier", yoy_pct: "the change from a year earlier", yoy_revenue_pct: "the change from a year earlier",
  seats_change_pct: "the change in seats", section_number: "the clause number", share_chg_pts: "the change in AA share", share_effect: "the share effect",
  share_gap_pts: "the share gap in points", share_gap_usd: "the share gap in dollars", volume_effect: "the volume effect",
  ytd_revenue: "year-to-date revenue", ytd_goal: "the year-to-date goal", pace_pct: "pace to the annual goal",
  value: "the clause's value", threshold: "the clause's line", distance: "the distance to the line", dollars: "the dollars at stake", days_since_touch: "the days since the last touch",
};
const WORD: Record<string, string> = { aa: "AA", yoy: "year over year", ytd: "year to date", chg: "change", pct: "percent", usd: "dollars", prior: "a year earlier" };

/** A column name in plain words: "aa_revenue" is "AA revenue", "odd_thing_usd" is "odd thing in dollars". */
export function columnWords(col: string): string {
  const key = col.toLowerCase();
  if (COLUMN_WORDS[key]) return COLUMN_WORDS[key];
  const m = /^(.*)_(pct|pts|usd)$/.exec(key);
  const base = m ? m[1] : key;
  const unit = m ? { pct: " in percent", pts: " in points", usd: " in dollars" }[m[2]] : "";
  return base.split("_").map((w) => WORD[w] ?? w).join(" ") + unit;
}

export type HintFact = { name: string; label: string; source: string | null; rows: Record<string, unknown>[] };
const CONTEXT_COLS = ["agency_name", "agency", "market", "section", "opp_name", "contact_name", "quarter", "qtr", "month", "clause_type"];

function rowContext(row: Record<string, unknown> | undefined): string {
  if (!row) return "";
  for (const c of CONTEXT_COLS) {
    const v = row[c];
    if (v !== undefined && v !== null && String(v).trim()) return c === "section" ? `clause ${v}` : String(v);
  }
  const first = Object.values(row).find((v) => typeof v === "string" && v.trim() && v.length <= 40);
  return first ? String(first) : "";
}

/** What a checked number is and where it came from, in one plain sentence for the hover: the column in words, the row it
 * sits on, the query's label and the table it read. A number quoted from a public page says which source. */
export function numberHint(n: { raw: string; source: string | null; fact: string | null }, facts: HintFact[]): string {
  if (!n.source) return "";
  if (n.source.startsWith("web:")) return copy.numFromSource(n.raw, /source \[(\d+)\]/.exec(n.fact ?? "")?.[1] ?? "");
  const fact = facts.find((f) => f.name === n.source);
  const eq = (n.fact ?? "").indexOf("=");
  const col = eq > 0 ? (n.fact as string).slice(0, eq) : "";
  const value = eq > 0 ? Number((n.fact as string).slice(eq + 1)) : NaN;
  const row = fact && col ? fact.rows.find((r) => Number(r[col]) === value) : undefined;
  return copy.numHint(n.raw, col ? columnWords(col) : "a number", rowContext(row), fact?.label ?? n.source, fact?.source ?? null);
}

export { minutesWord, numberWord };
