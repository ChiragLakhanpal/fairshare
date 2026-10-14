import * as Dialog from "@radix-ui/react-dialog";
import { useEffect, useState } from "react";
import { copy } from "../copy";
import { api } from "../lib/api";
import type { Definitions } from "../lib/types";
import { Check, Close } from "./Icons";

const PLAIN: Record<string, string> = {
  aa_revenue: "AA revenue is the ticketed revenue sold on AA by the agency, in US dollars, for the markets and months you picked.",
  aa_share: "AA share is AA revenue divided by everything the agency sold on the same markets and months, across all carriers. It is a ratio computed at the grain of the question, never an average of other shares.",
  fair_share: "Fair share is AA's share of the scheduled seats on a market, weighted by what the agency sold there. It is the share an agency would sell if it had no carrier preference.",
  share_gap_pts: "Share gap in points is AA share minus fair share. Above zero, the agency sells more AA than the schedule alone would predict.",
  share_gap_usd: "Share gap in dollars is AA revenue minus the revenue AA would have if the agency sold exactly fair share.",
  yoy_revenue_pct: "The change from last year compares AA revenue this month with the same calendar month a year earlier.",
  pace_pct: "Pace is year-to-date AA revenue divided by the year-to-date share of the annual goal, with the goal spread evenly over twelve months. 100 means on pace.",
};

export function DefinitionWindow({ kpi, onClose }: { kpi: string | null; onClose: () => void }) {
  const [defs, setDefs] = useState<Definitions | null>(null);
  const [formula, setFormula] = useState(false);
  useEffect(() => {
    if (kpi && !defs) api.definitions().then(setDefs).catch(() => setDefs(null));
  }, [kpi, defs]);
  const d = defs?.kpis.find((k) => k.kpi === kpi);
  const parity = defs?.parity;
  const when = parity ? new Date(parity.run_at).toLocaleDateString("en-US", { month: "long", day: "numeric" }) : "";
  return (
    <Dialog.Root open={!!kpi} onOpenChange={(o) => !o && onClose()}>
      <Dialog.Portal>
        <Dialog.Overlay className="fixed inset-0 z-40 bg-ink/20" />
        <Dialog.Content className="fixed left-1/2 top-1/2 z-50 w-[min(440px,94vw)] -translate-x-1/2 -translate-y-1/2 rounded-[10px] border border-line bg-white px-5 py-4 text-[13.5px] leading-[1.5] shadow-2xl">
          <div className="flex items-baseline justify-between gap-3">
            <Dialog.Title className="text-[15px] font-semibold text-ink">{d?.display_name ?? kpi}</Dialog.Title>
            <Dialog.Close aria-label={copy.closeWindow} className="text-ink-2 hover:text-ink"><Close /></Dialog.Close>
          </div>
          <Dialog.Description className="mt-1.5 text-ink">{PLAIN[kpi ?? ""] ?? d?.definition_en ?? ""}</Dialog.Description>
          {parity && (
            <p className="mt-2 flex items-start gap-1.5 text-[12.5px] text-ink-2"><Check className="mt-[3px] shrink-0 text-blue" width={13} height={13} strokeWidth={2.5} /><span>{parity.drift === 0 ? copy.defCheck(when, parity.rows) : copy.defCheckDrift(when, parity.drift)}</span></p>
          )}
          {d && (
            <>
              <div className="mt-2.5 flex gap-3.5 text-[13px]"><button type="button" className="text-blue hover:underline" onClick={() => setFormula((f) => !f)}>{formula ? "Hide the formula" : copy.showFormula}</button></div>
              {formula && <pre className="sql mt-2.5">{d.metric_view_expr || d.twin_sql}</pre>}
              {formula && d.definition_en && <p className="mt-2 text-[12.5px] text-ink-2"><b>The exact wording:</b> {d.definition_en}</p>}
            </>
          )}
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  );
}
