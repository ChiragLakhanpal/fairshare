import { copy } from "../copy";
import { progressText, scopeLabel, whenLabel } from "../lib/runs";
import type { Item, Run } from "../lib/types";
import { ItemView } from "./ItemView";
import { StatusPill } from "./RunList";

export function RunView({ run, crmLabel, onItemChange }: { run: Run; crmLabel: string; onItemChange: (i: Item) => void }) {
  return (
    <div aria-label={`${run.agent_name}, ${scopeLabel(run.scope)}`}>
      <div className="flex items-start justify-between gap-4">
        <div>
          <h3 className="text-[17px] font-semibold text-ink">{run.agent_name}</h3>
          <p className="text-[13.5px] text-ink-2">{scopeLabel(run.scope)}</p>
        </div>
        <StatusPill status={run.status} />
      </div>
      <p className="mt-1.5 text-[13.5px] text-ink-2" role="status">{progressText(run)}{run.requested_by ? ` ${copy.requestedBy(run.requested_by, whenLabel(run.created_at))}` : ""}</p>
      {run.status === "failed" && run.error && (
        <div className="mt-2.5 rounded-lg border border-[#F0C7CC] bg-red-tint px-3 py-2.5 text-[13.5px] leading-[1.5] text-ink">{copy.runError(run.error)}</div>
      )}
      {run.items.length === 0 && run.status === "running" && <p className="mt-4 text-[14px] text-ink-2">{copy.noItemsYet}</p>}
      <div className="mt-4 flex flex-col gap-4">
        {run.items.map((i) => <ItemView key={i.item_id} runId={run.run_id} item={i} crmLabel={crmLabel} onChange={onItemChange} />)}
      </div>
    </div>
  );
}
