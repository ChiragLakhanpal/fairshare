// A KPI word: hover for one line, click for the small definition window (filled in by Definitions in a later batch).
import * as Tooltip from "@radix-ui/react-tooltip";
import type { ReactNode } from "react";

const ONE_LINE: Record<string, string> = {
  aa_share: "AA share is AA revenue divided by everything the agency sold on the same markets, across all carriers.",
  fair_share: "Fair share is AA's share of the scheduled seats on a market, weighted by what the agency sold there.",
  share_gap_pts: "Share gap is AA share minus fair share, in points.",
  share_gap_usd: "Share gap in dollars is AA revenue minus what AA would have at exactly fair share.",
  pace_pct: "Pace is year-to-date revenue against the year-to-date share of the annual goal. 100 means on pace.",
  yoy_revenue_pct: "The change from the same month a year earlier.",
};

export function Term({ kpi, children, onOpen }: { kpi: string; children: ReactNode; onOpen?: (kpi: string) => void }) {
  return (
    <Tooltip.Provider delayDuration={200}>
      <Tooltip.Root>
        <Tooltip.Trigger asChild>
          <button type="button" className="term inline cursor-help bg-transparent p-0 text-inherit" onClick={() => (onOpen ? onOpen(kpi) : window.dispatchEvent(new CustomEvent("fairshare:kpi", { detail: kpi })))}>{children}</button>
        </Tooltip.Trigger>
        <Tooltip.Portal>
          <Tooltip.Content side="bottom" align="start" sideOffset={6} className="z-30 max-w-[300px] rounded-md bg-ink px-3 py-2 text-[13px] leading-snug text-white shadow-lg">
            {ONE_LINE[kpi] ?? kpi} Click the word for the full definition and how it is checked.
          </Tooltip.Content>
        </Tooltip.Portal>
      </Tooltip.Root>
    </Tooltip.Provider>
  );
}
