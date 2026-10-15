import { copy } from "../copy";
import { scopeLabel, statusLabel, whenLabel } from "../lib/runs";
import type { RunHeader, RunStatus } from "../lib/types";

export function StatusPill({ status }: { status: RunStatus }) {
  const look = status === "running" ? "border-tint-line bg-tint text-navy" : status === "needs_approval" ? "border-tint-line bg-white text-blue" : status === "failed" ? "border-[#F0C7CC] bg-red-tint text-red" : "border-line bg-surface text-ink-2";
  return (
    <span className={`inline-flex shrink-0 items-center gap-1.5 rounded-full border px-2 py-0.5 text-[11.5px] font-semibold ${look}`}>
      {status === "running" && <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-blue" />}
      {statusLabel(status)}
    </span>
  );
}

export function RunList({ runs, selected, onSelect, loading }: { runs: RunHeader[]; selected: string | null; onSelect: (id: string) => void; loading: boolean }) {
  if (loading && runs.length === 0) return <p className="text-[13.5px] text-ink-2">{copy.runsLoading}</p>;
  if (runs.length === 0) return <p className="text-[13.5px] text-ink-2">{copy.noRuns}</p>;
  return (
    <ul className="flex flex-col gap-1" aria-label={copy.runsLabel}>
      {runs.map((r) => (
        <li key={r.run_id}>
          <button type="button" aria-current={selected === r.run_id ? "true" : undefined} onClick={() => onSelect(r.run_id)}
            className={`press w-full rounded-lg px-3 py-2.5 text-left ${selected === r.run_id ? "bg-white shadow-sm ring-1 ring-line" : "hover:bg-surface"}`}>
            <div className="flex items-center justify-between gap-2"><span className="truncate text-[14px] font-semibold text-ink">{r.agent_name}</span><StatusPill status={r.status} /></div>
            <div className="mt-0.5 text-[13px] text-ink-2">{scopeLabel(r.scope)}</div>
            <div className="mt-0.5 text-[12.5px] text-grey">{whenLabel(r.created_at)}.{r.needs_approval > 0 ? ` ${copy.waiting(r.needs_approval, r.items)}` : ""}</div>
          </button>
        </li>
      ))}
    </ul>
  );
}
