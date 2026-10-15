// The progress list while an answer is in flight: what each step is doing (from the tool's arguments), how long it took,
// and which hint to show as the wait grows. Pure functions; Steps.tsx renders them.
import { copy } from "../copy";
import { monthLabel } from "./format";
import type { Step } from "./types";

const str = (v: unknown) => (typeof v === "string" ? v : "");

/** The workings of a step: the question Genie was asked, the first line of the query, the agency and month, the agency and topic. */
export function stepDetail(s: Step): string | null {
  const a = s.args ?? {};
  if (s.phase === "genie" && str(a.question)) return `"${a.question}"`;
  if (s.phase === "sql" && str(a.sql)) {
    const lines = str(a.sql).split("\n").map((l) => l.trim()).filter(Boolean);
    const first = lines[0] ?? "";
    const cut = first.length > 90 ? first.slice(0, 89).trimEnd() : first;
    return cut !== first || lines.length > 1 ? `${cut} …` : first;
  }
  if (s.phase === "explain" && str(a.agency)) return str(a.month) ? `${a.agency}, ${monthLabel(str(a.month))}` : str(a.agency);
  if (s.phase === "agreement" && str(a.agency)) return str(a.topic) ? `${a.agency}: ${a.topic}` : str(a.agency);
  return null;
}

const secs = (n: number) => (n < 1 ? "under a second" : `${n} s`);
/** A finished step in the past tense, with its time. */
export function doneLabel(s: Step, seconds: number): string {
  if (s.phase === "warehouse") return seconds < 2 ? copy.warehouseAwake : copy.stepDone.warehouse(secs(seconds));
  const f = copy.stepDone[s.phase];
  return f ? f(secs(seconds)) : s.text || s.phase;
}

/** Silent for ten seconds, then the usual hint, the warehouse note on a long Genie wait, and a way out at ninety seconds. */
export function hintFor(phase: string, elapsedS: number): string | null {
  if (elapsedS < 10) return null;
  if (elapsedS >= 90) return copy.waitLong;
  if (elapsedS >= 45 && (phase === "genie" || phase === "warehouse")) return copy.waitGenie;
  return copy.waitHint;
}

/** The steps to show: every tool step plus the latest status, each timed from its arrival to the next event (or to now). */
export function visibleSteps(steps: Step[], now: number): { step: Step; current: boolean; seconds: number }[] {
  return steps
    .map((step, i) => {
      const current = i === steps.length - 1;
      const end = current ? now : (steps[i + 1].at ?? now);
      return { step, current, seconds: Math.max(0, Math.floor((end - (step.at ?? end)) / 1000)) };
    })
    .filter((t) => t.current || t.step.phase !== "model");
}
