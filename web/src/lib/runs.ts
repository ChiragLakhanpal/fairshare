// Words for agent runs and their items: status labels, the progress line, scope names, decided lines. Pure functions.
import { copy } from "../copy";
import { monthLabel } from "./format";
import type { AgentScope, Item, Run, RunStatus } from "./types";

export function statusLabel(s: RunStatus): string {
  return copy.runStatus[s] ?? s;
}

export function draftCount(items: Item[]): number {
  return items.filter((i) => i.status === "draft").length;
}

export function progressText(run: Pick<Run, "status" | "progress" | "items">): string {
  if (run.status === "running") return run.progress.text || (run.progress.total ? copy.written(run.progress.done, run.progress.total) : copy.starting);
  if (run.status === "needs_approval") return copy.waiting(draftCount(run.items), run.items.length);
  if (run.status === "failed") return copy.runFailed;
  return copy.decidedAll;
}

export function scopeLabel(scope: AgentScope): string {
  if (scope.manager) return scope.month ? `${scope.manager}, ${monthLabel(scope.month)}` : scope.manager;
  if (scope.region) {
    const region = scope.region === "All" ? "All regions" : `${scope.region} region`;
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

export function decidedLine(item: Item): string {
  const verb = item.status === "approved" ? "Approved" : "Rejected";
  const by = item.decided_by ? ` by ${item.decided_by}` : "";
  const when = item.decided_at ? ` on ${whenLabel(item.decided_at)}` : "";
  return `${verb}${by}${when}.`;
}
