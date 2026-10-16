// The rows pages show up as: a severity dot, the name, one plain line, the status, a chevron. The whole row opens the
// page. A compact form sits beside an open page; writing and queued rows show a run in progress.
import { copy } from "../copy";
import type { Severity } from "../lib/types";
import { ChevronRight } from "./Icons";

type Dot = Severity | "running" | "queued";

export function SeverityDot({ s, className = "" }: { s: Dot; className?: string }) {
  const label = s === "running" ? copy.writing : s === "queued" ? copy.queued : copy.severity[s ?? "ok"] ?? "";
  const look = s === "risk" ? "bg-red" : s === "watch" ? "bg-ink-2" : s === "running" ? "animate-pulse bg-blue" : s === "queued" ? "border-2 border-line bg-white" : "border-2 border-grey bg-white";
  return <span role="img" aria-label={label} className={`box-border inline-block h-2 w-2 shrink-0 rounded-full ${look} ${className}`} />;
}

export function SeverityChip({ s }: { s: Severity }) {
  const look = s === "risk" ? "bg-red-tint text-red" : s === "watch" ? "border border-line bg-surface text-ink" : "bg-tint text-navy";
  return <span className={`inline-flex h-[22px] shrink-0 items-center rounded-full px-2.5 text-[12px] font-semibold ${look}`}>{copy.severity[s ?? "ok"]}</span>;
}

type RowProps = { title: string; summary: string; severity: Severity; right: string; onOpen: () => void; selected?: boolean; compact?: boolean; last?: boolean };

export function ItemRow({ title, summary, severity, right, onOpen, selected, compact, last }: RowProps) {
  if (compact) {
    return (
      <button type="button" onClick={onOpen} aria-current={selected ? "true" : undefined} aria-label={title}
        className={`press block w-full rounded-[10px] px-3.5 py-2.5 text-left ${selected ? "bg-white shadow-sm" : "hover:bg-white/70"}`}>
        <span className="flex items-center gap-2"><SeverityDot s={severity} /><span className="min-w-0 flex-1 truncate font-semibold text-ink">{title}</span><span className="shrink-0 text-[12px] text-ink-2">{right}</span></span>
        <span className="mt-0.5 block pl-4 text-[13px] leading-[1.4] text-ink-2">{summary}</span>
      </button>
    );
  }
  return (
    <button type="button" onClick={onOpen} aria-label={title}
      className={`press grid w-full grid-cols-[10px_230px_minmax(0,1fr)_auto_16px] items-center gap-3.5 border-t hairline px-2 py-3 text-left text-[15px] text-ink hover:bg-surface/60 ${last ? "border-b" : ""}`}>
      <SeverityDot s={severity} />
      <span className="font-medium">{title}</span>
      <span className="leading-[1.45]">{summary}</span>
      <span className="whitespace-nowrap text-[12.5px] text-ink-2">{right}</span>
      <ChevronRight className="text-grey" />
    </button>
  );
}

export function WritingRow({ title }: { title: string }) {
  return (
    <div className="grid grid-cols-[10px_230px_minmax(0,1fr)_auto_16px] items-center gap-3.5 border-t hairline px-2 py-3 text-[15px] text-ink" aria-label={`${title}: ${copy.writing}`}>
      <SeverityDot s="running" />
      <span className="font-medium">{title}</span>
      <span className="flex flex-col gap-1.5 py-1" aria-hidden="true"><span className="h-2.5 w-3/4 rounded bg-line-2" /><span className="h-2.5 w-1/2 rounded bg-line-2" /></span>
      <span className="whitespace-nowrap text-[12.5px] text-blue">{copy.writing}</span>
      <span />
    </div>
  );
}

export function QueuedRow({ label, last }: { label: string; last?: boolean }) {
  return (
    <div className={`grid grid-cols-[10px_230px_minmax(0,1fr)_auto_16px] items-center gap-3.5 border-t hairline px-2 py-3 text-[15px] text-grey ${last ? "border-b" : ""}`}>
      <SeverityDot s="queued" />
      <span className="font-medium">{label}</span>
      <span>{copy.queued}</span>
      <span />
      <span />
    </div>
  );
}
