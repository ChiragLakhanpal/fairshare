// The home page's "Worth knowing" lines on the browser side: the suggestion chips they raise, the one line related to an
// answer, and the facts their numbers point at. Pure functions, tested in signals.test.ts.
import type { HintFact } from "./runs";
import type { Signal, Signals } from "./types";

/** The suggestion chips: the questions this month's signals raise, then the standing ones, three in all. */
export function chipsFrom(signals: Signal[] | null | undefined, fallback: string[], max = 3): string[] {
  const out: string[] = [];
  for (const q of [...(signals ?? []).map((s) => s.chip), ...fallback]) {
    if (q && !out.includes(q)) out.push(q);
    if (out.length === max) break;
  }
  return out;
}

const escapeRe = (s: string) => s.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");

/** The first signal about an agency the text names, by its full name or its first word, as whole words. */
export function relatedSignal(text: string, signals: Signal[]): Signal | null {
  const t = text.toLowerCase();
  return (
    signals.find((s) => {
      if (!s.agency) return false;
      const full = s.agency.toLowerCase();
      const first = full.split(/\s+/)[0];
      return new RegExp(`\\b${escapeRe(full)}\\b`).test(t) || new RegExp(`\\b${escapeRe(first)}\\b`).test(t);
    }) ?? null
  );
}

/** The calls behind the lines, named the way the checker names a number's source (tool and position). */
export function signalFacts(s: Signals): HintFact[] {
  return s.calls.map((c, k) => ({ name: `${c.tool}#${k + 1}`, label: String(c.args.block ?? c.tool), source: (c.args.table as string | undefined) ?? null, rows: c.preview }));
}
