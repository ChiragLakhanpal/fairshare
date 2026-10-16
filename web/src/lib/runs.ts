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

/** The title a checked number shows on hover: the fact it matched and the query that returned it. */
export function numberTitle(n: { source: string | null; fact: string | null }): string {
  if (!n.source && !n.fact) return "";
  return [n.fact ? `Matched ${n.fact}` : "", n.source ? `from ${n.source}` : ""].filter(Boolean).join(" ");
}

export { minutesWord, numberWord };
