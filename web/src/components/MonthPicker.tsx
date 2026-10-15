// One control for the month: a button with the month's name that opens a year and its twelve months.
import * as Popover from "@radix-ui/react-popover";
import { useEffect, useState } from "react";
import { copy } from "../copy";
import { monthLabel } from "../lib/format";
import { ChevronDown, ChevronLeft, ChevronRight } from "./Icons";

const NAMES = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];

export function MonthPicker({ months, value, onChange }: { months: string[]; value: string; onChange: (m: string) => void }) {
  const have = new Set(months);
  const years = [...new Set(months.map((m) => m.slice(0, 4)))].sort();
  const [open, setOpen] = useState(false);
  const [year, setYear] = useState(value.slice(0, 4) || years[years.length - 1] || "");
  useEffect(() => {
    if (open) setYear(value.slice(0, 4) || years[years.length - 1] || "");
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open, value]);
  const minYear = years[0] ?? year;
  const maxYear = years[years.length - 1] ?? year;
  const nav = "flex h-8 w-8 items-center justify-center rounded-lg border border-line bg-white text-ink disabled:border-line-2 disabled:text-grey";
  return (
    <Popover.Root open={open} onOpenChange={setOpen}>
      <Popover.Trigger asChild>
        <button type="button" aria-label={`${copy.monthPicker}: ${monthLabel(value)}`}
          className="inline-flex h-[34px] items-center gap-2 whitespace-nowrap rounded-md border border-line bg-white px-3 text-sm font-medium text-ink hover:border-grey focus:outline-none focus:ring-2 focus:ring-tint-line">
          {monthLabel(value)}<ChevronDown width={14} height={14} className="text-ink-2" />
        </button>
      </Popover.Trigger>
      <Popover.Portal>
        <Popover.Content align="start" sideOffset={6} aria-label={copy.monthPicker} className="z-30 w-[352px] rounded-xl border border-line bg-white p-3.5 shadow-xl">
          <div className="flex items-center justify-between px-1 pb-2.5">
            <button type="button" aria-label={copy.yearBefore} className={nav} disabled={year <= minYear} onClick={() => setYear(String(Number(year) - 1))}><ChevronLeft width={14} height={14} /></button>
            <span className="text-[15px] font-semibold">{year}</span>
            <button type="button" aria-label={copy.yearAfter} className={nav} disabled={year >= maxYear} onClick={() => setYear(String(Number(year) + 1))}><ChevronRight width={14} height={14} /></button>
          </div>
          <div className="grid grid-cols-4 gap-1.5">
            {NAMES.map((n, i) => {
              const ym = `${year}-${String(i + 1).padStart(2, "0")}`;
              const on = ym === value;
              const ok = have.has(ym);
              return (
                <button key={ym} type="button" disabled={!ok} aria-pressed={on} aria-label={`${n} ${year}`} onClick={() => { onChange(ym); setOpen(false); }}
                  className={`press h-10 rounded-lg text-sm font-medium ${on ? "bg-blue font-semibold text-white" : ok ? "text-ink hover:bg-surface" : "text-[#C4CCD2]"}`}>{n}</button>
              );
            })}
          </div>
          <p className="mt-3 px-1 text-[12.5px] leading-[1.45] text-ink-2">{copy.monthHint}</p>
        </Popover.Content>
      </Popover.Portal>
    </Popover.Root>
  );
}
