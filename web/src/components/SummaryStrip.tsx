import { copy } from "../copy";
import { monthLabel } from "../lib/format";
import type { Summary } from "../lib/types";
import { stripParts } from "./Summary";
import { ChevronDown } from "./Icons";

export function SummaryStrip({ summary, expanded, onToggle }: { summary: Summary | null; expanded: boolean; onToggle: () => void }) {
  if (!summary) return null;
  const p = stripParts(summary);
  return (
    <div className="sticky top-0 z-10">
      <button type="button" onClick={onToggle} aria-expanded={expanded} className="translucent flex w-full items-center gap-3 px-7 py-2.5 text-left text-[13.5px] text-ink shadow-[0_1px_0_rgba(54,73,90,0.08)] hover:bg-white/95">
        <span className="flex-1">
          {monthLabel(summary.month)}: <b>{p.revenue}</b> in AA revenue, {p.yoy}. AA share is <b>{p.share}</b> against a fair share of <b>{p.fair}</b>, a gap of <b style={p.gapNeg ? { color: "#C30019" } : undefined}>{p.gap}</b>. Pace is <b>{p.pace}</b> of goal.
        </span>
        <span className="inline-flex shrink-0 items-center gap-1.5 font-medium text-blue">{expanded ? copy.hideSummary : copy.showSummary}<ChevronDown width={14} height={14} style={{ transform: expanded ? "rotate(180deg)" : undefined, transition: "transform 200ms" }} /></span>
      </button>
      <div className="edge-fade" />
    </div>
  );
}
