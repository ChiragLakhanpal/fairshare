import { copy } from "../copy";
import { monthLabel } from "../lib/format";
import type { Me, Scope } from "../lib/types";
import { External } from "./Icons";
import { MonthPicker } from "./MonthPicker";
import { Select } from "./Select";

export function TopBar({ me, scope, onScope }: { me: Me | null; scope: Scope; onScope: (s: Scope) => void }) {
  const regions = me?.regions ?? ["All", "Central", "East", "West"];
  const months = me?.months ?? (scope.month ? [scope.month] : []);
  return (
    <div className="flex h-14 items-center justify-between gap-4 px-7">
      <div className="flex gap-2">
        <Select label="Region" value={scope.region} options={regions.map((r) => ({ value: r, label: r === "All" ? "All regions" : `${r} region` }))} onChange={(r) => onScope({ ...scope, region: r })} />
        {scope.month && <MonthPicker months={months} value={scope.month} onChange={(m) => onScope({ ...scope, month: m })} />}
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
