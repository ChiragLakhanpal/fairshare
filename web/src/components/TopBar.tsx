import { copy } from "../copy";
import { monthLabel } from "../lib/format";
import type { Me, Scope } from "../lib/types";
import { ChevronDown, External } from "./Icons";

export function TopBar({ me, scope, onScope }: { me: Me | null; scope: Scope; onScope: (s: Scope) => void }) {
  const regions = me?.regions ?? ["All", "Central", "East", "West"];
  const months = me?.months ?? [scope.month];
  const sel = "appearance-none rounded-md border border-line bg-white py-1.5 pl-3 pr-8 text-sm font-medium text-ink hover:border-grey focus:outline-none focus:ring-2 focus:ring-tint-line";
  return (
    <div className="flex h-14 items-center justify-between gap-4 px-7">
      <div className="flex gap-2">
        <label className="relative">
          <span className="sr-only">Region</span>
          <select className={sel} value={scope.region} onChange={(e) => onScope({ ...scope, region: e.target.value })}>
            {regions.map((r) => <option key={r} value={r}>{r === "All" ? "All regions" : `${r} region`}</option>)}
          </select>
          <ChevronDown className="pointer-events-none absolute right-2.5 top-1/2 -translate-y-1/2 text-ink-2" width={14} height={14} />
        </label>
        <label className="relative">
          <span className="sr-only">Month</span>
          <select className={sel} value={scope.month} onChange={(e) => onScope({ ...scope, month: e.target.value })}>
            {months.map((m) => <option key={m} value={m}>{monthLabel(m)}</option>)}
          </select>
          <ChevronDown className="pointer-events-none absolute right-2.5 top-1/2 -translate-y-1/2 text-ink-2" width={14} height={14} />
        </label>
      </div>
      <div className="flex items-center gap-5">
        {me && <span className="hidden text-[13px] text-ink-2 md:inline">{copy.dataThrough(monthLabel(me.data_through))}</span>}
        {me?.links.dashboard && (
          <a href={me.links.dashboard} target="_blank" rel="noreferrer" className="inline-flex items-center gap-1.5 text-[13.5px] font-medium">{copy.openDashboard}<External width={14} height={14} /></a>
        )}
      </div>
    </div>
  );
}
