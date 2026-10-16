// One agent: what it does, the scope and Run now, the stepper that becomes the progress, and its pages: the ones waiting
// for a decision first, then the decided ones. With a page open, the pages move to a narrow list beside the document.
import { useEffect, useState } from "react";
import { copy } from "../copy";
import { api } from "../lib/api";
import { toast } from "../lib/export";
import { monthLabel } from "../lib/format";
import { barFraction, nounFor, pageLine, progressLine, stepStates } from "../lib/runs";
import type { AgentDef, AgentScope, AgentsCatalog, Item, Page, PageVersion, Run, Scope } from "../lib/types";
import { Document } from "./Document";
import { ChevronLeft, Play } from "./Icons";
import { ItemRow, QueuedRow, WritingRow } from "./ItemRows";
import { Select } from "./Select";
import { Stepper } from "./Stepper";

type Props = {
  agent: AgentDef; catalog: AgentsCatalog; scope: Scope; run: Run | null; runLoading: boolean; runError: string | null;
  itemId: string | null; starting: boolean;
  onRun: (s: AgentScope) => void; onOpenVersion: (v: Pick<PageVersion, "run_id" | "item_id"> | null) => void; onItemChange: (i: Item | null) => void;
};

export function AgentView({ agent, catalog, scope, run, runLoading, runError, itemId, starting, onRun, onOpenVersion, onItemChange }: Props) {
  const [noun, nouns] = nounFor(agent.key);
  const [manager, setManager] = useState(catalog.managers[0] ?? "");
  const [market, setMarket] = useState(catalog.markets[0]?.market ?? "");
  useEffect(() => {
    if (!manager && catalog.managers[0]) setManager(catalog.managers[0]);
    if (!market && catalog.markets[0]) setMarket(catalog.markets[0].market);
  }, [catalog, manager, market]);

  const live = run ?? (agent.running ? { status: "running" as const, progress: agent.running.progress } : null);
  const states = stepStates(agent.steps, live);
  const running = live?.status === "running";
  const line = running && live ? progressLine(live.progress, noun) : null;
  const regionLabel = `${scope.region === "All" ? "all regions" : `the ${scope.region} region`}, ${monthLabel(scope.month)}`;
  const start = () => onRun(agent.scope_kind === "manager" ? { manager, month: scope.month } : agent.scope_kind === "market" ? { market } : { region: scope.region, month: scope.month });
  const ready = agent.scope_kind === "manager" ? !!manager && !!scope.month : agent.scope_kind === "market" ? !!market : !!scope.month;
  const pages = agent.pages;
  const count = copy.pagesCount(pages.length, noun, nouns, agent.waiting);
  const selected = run && itemId ? run.items.find((i) => i.item_id === itemId) ?? null : null;
  const page = itemId ? pages.find((p) => p.versions.some((v) => v.item_id === itemId)) ?? null : null;

  // Several pages at once: the waiting ones carry a checkbox; a bar below the list approves or rejects the picked ones, one call per run.
  const waitingPages = pages.filter((p) => p.status === "draft");
  const [picked, setPicked] = useState<string[]>([]);
  const [deciding, setDeciding] = useState(false);
  useEffect(() => setPicked([]), [agent.key]);
  const pickedPages = waitingPages.filter((p) => picked.includes(p.item_id));
  const pick = (p: Page, on: boolean) => setPicked((cur) => (on ? [...cur.filter((id) => id !== p.item_id), p.item_id] : cur.filter((id) => id !== p.item_id)));
  const decideAll = async (approve: boolean) => {
    setDeciding(true);
    const byRun = new Map<string, string[]>();
    for (const p of pickedPages) byRun.set(p.run_id, [...(byRun.get(p.run_id) ?? []), p.item_id]);
    let done = 0;
    let failed = false;
    for (const [runId, ids] of byRun) {
      try {
        done += (await api.decideItems(runId, ids, approve)).length;
      } catch {
        failed = true;
      }
    }
    toast(failed ? copy.bulkFailed : copy.bulkDone(approve ? "Approved" : "Rejected", done, noun, nouns), 4000);
    setPicked([]);
    setDeciding(false);
    onItemChange(null);
  };

  if (run && selected) {
    return (
      <div className="flex h-[calc(100vh-56px)] min-h-0">
        <aside className="w-[300px] shrink-0 overflow-y-auto border-r hairline bg-surface/50 px-3 py-4" aria-label={count}>
          <button type="button" onClick={() => onOpenVersion(null)} className="press mb-3 inline-flex items-center gap-1 px-3.5 text-[14px] font-medium text-blue hover:underline"><ChevronLeft width={14} height={14} />{agent.name}</button>
          <div className="t-label px-3.5 pb-2">{count}</div>
          <div className="flex flex-col gap-1">
            {pages.map((p) => <ItemRow key={p.item_id} compact title={p.title} summary={p.summary || p.subtitle} severity={p.severity} right={p.status === "draft" ? "" : pageLine(p)} selected={p === page} onOpen={() => onOpenVersion(p)} />)}
          </div>
        </aside>
        <Document runId={run.run_id} item={selected} versions={page?.versions ?? []} onOpenVersion={onOpenVersion} onChange={onItemChange} />
      </div>
    );
  }

  const queued = running && live ? Math.max(0, live.progress.total - live.progress.done - 1) : 0;
  const detail = copy.detailsLine(agent.reads.join(", "), agent.writes.join(", "));
  return (
    <div className="mx-auto w-full max-w-[1040px] px-10 pb-16 pt-8">
      <div className="t-label">{copy.modeDelegate}</div>
      <h1 className="t-title mt-2">{agent.name}</h1>
      <p className="mt-2 max-w-[720px] text-[15px] leading-[1.55]">{agent.one_liner} {agent.cadence}</p>

      <div className="mt-5 flex flex-wrap items-center gap-3">
        {agent.scope_kind !== "region" && <span className="text-[14px] text-ink-2">{copy.forLabel}</span>}
        {agent.scope_kind === "manager" && <Select label={copy.pickManager} value={manager} options={catalog.managers.map((m) => ({ value: m, label: m }))} onChange={setManager} disabled={running || starting} />}
        {agent.scope_kind === "market" && <Select label={copy.pickMarket} value={market} options={catalog.markets.map((m) => ({ value: m.market, label: m.market }))} onChange={setMarket} disabled={running || starting} />}
        <button type="button" onClick={start} disabled={running || starting || !ready}
          className={`press inline-flex h-[34px] items-center gap-2 rounded-md px-4 text-[14px] font-semibold text-white ${running || starting ? "bg-grey" : "bg-blue hover:bg-navy"} disabled:cursor-default`}>
          {running ? copy.running : starting ? copy.runStarting : <><Play width={11} height={11} />{copy.runNow}</>}
        </button>
        <span className="text-[13px] text-ink-2">{agent.scope_kind === "region" ? copy.scopeFromFilters(regionLabel) : copy.timeHint(live?.progress.total || null, nouns)}</span>
      </div>

      <div className="mt-7">
        <Stepper steps={agent.steps} states={states} line={line} fraction={live ? barFraction(live.progress) : 0} note={detail} />
      </div>

      <div className="mt-8">
        <div className="flex items-center justify-between gap-4 pb-2">
          <div className="text-[15px] font-semibold">{count}</div>
          {waitingPages.length > 1 && (
            <label className="flex cursor-pointer items-center gap-2 text-[13px] text-ink-2">
              <input type="checkbox" className="h-4 w-4 cursor-pointer accent-[var(--color-blue)]" checked={pickedPages.length === waitingPages.length} onChange={(e) => setPicked(e.target.checked ? waitingPages.map((p) => p.item_id) : [])} />
              {copy.selectAllWaiting}
            </label>
          )}
        </div>
        {runError && <p className="text-[13.5px] text-red">{runError}</p>}
        {run && run.status === "failed" && run.error && <div className="mb-3 rounded-lg border border-[#F0C7CC] bg-red-tint px-3 py-2.5 text-[13.5px] leading-[1.5]">{copy.runFailedLine(run.error)}</div>}
        <div>
          {running && live && live.progress.total > live.progress.done && <WritingRow title={live.progress.item ?? copy.nextUp(noun)} />}
          {running && Array.from({ length: queued }).map((_, k) => <QueuedRow key={k} label={copy.nextUp(noun)} last={k === queued - 1 && pages.length === 0} />)}
          {pages.map((p, k) => (
            <ItemRow key={p.item_id} title={p.title} summary={p.summary || p.subtitle} severity={p.severity} right={pageLine(p)} last={k === pages.length - 1} onOpen={() => onOpenVersion(p)}
              checked={picked.includes(p.item_id)} onCheck={p.status === "draft" && waitingPages.length > 1 ? (on) => pick(p, on) : undefined} />
          ))}
          {!running && pages.length === 0 && !runError && (
            runLoading ? <p className="text-[13.5px] text-ink-2">{copy.runLoading}</p>
              : <p className="text-[14px] text-ink-2">{agent.last_run && agent.last_run.status !== "failed" ? copy.lastRunEmpty : copy.noRunsForAgent}</p>
          )}
        </div>
        {pickedPages.length > 0 && (
          <div className="sticky bottom-0 mt-2 border-t hairline bg-white/95 py-3 backdrop-blur" role="region" aria-label={copy.selectedCount(pickedPages.length, noun, nouns)}>
            <div className="flex flex-wrap items-center gap-2.5">
              <span className="text-[14px] font-semibold">{copy.selectedCount(pickedPages.length, noun, nouns)}</span>
              <button type="button" onClick={() => void decideAll(true)} disabled={deciding} className="press rounded-lg bg-blue px-4 py-2 text-[14px] font-semibold text-white hover:bg-navy disabled:opacity-60">{copy.approveSelected}</button>
              <button type="button" onClick={() => void decideAll(false)} disabled={deciding} className="press rounded-lg border border-line bg-white px-3.5 py-2 text-[14px] font-semibold text-ink hover:border-blue hover:text-blue">{copy.rejectSelected}</button>
              <button type="button" onClick={() => setPicked([])} disabled={deciding} className="press text-[14px] font-medium text-blue hover:underline">{copy.clearSelection}</button>
              <span className="text-[13px] text-ink-2">{copy.bulkHint}</span>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
