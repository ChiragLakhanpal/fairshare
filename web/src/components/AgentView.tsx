// One agent: what it does, the scope and Run now, the stepper that becomes the progress, and its pages: the ones waiting
// for a decision first, then the decided ones. With a page open, the pages move to a narrow list beside the document.
import { useEffect, useState } from "react";
import { copy } from "../copy";
import { monthLabel } from "../lib/format";
import { barFraction, nounFor, pageLine, progressLine, stepStates } from "../lib/runs";
import type { AgentDef, AgentScope, AgentsCatalog, Item, PageVersion, Run, Scope } from "../lib/types";
import { Document } from "./Document";
import { ChevronDown, ChevronLeft, Play } from "./Icons";
import { ItemRow, QueuedRow, WritingRow } from "./ItemRows";
import { Stepper } from "./Stepper";

const sel = "h-9 appearance-none rounded-md border border-line bg-white pl-3 pr-8 text-sm font-medium text-ink hover:border-grey focus:outline-none focus:ring-2 focus:ring-tint-line disabled:bg-surface disabled:text-grey";

type Props = {
  agent: AgentDef; catalog: AgentsCatalog; scope: Scope; run: Run | null; runLoading: boolean; runError: string | null;
  itemId: string | null; starting: boolean;
  onRun: (s: AgentScope) => void; onOpenVersion: (v: Pick<PageVersion, "run_id" | "item_id"> | null) => void; onItemChange: (i: Item) => void;
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

  if (run && selected) {
    return (
      <div className="flex min-h-[calc(100vh-56px)]">
        <aside className="w-[300px] shrink-0 self-stretch border-r hairline bg-surface/50 px-3 py-4" aria-label={count}>
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
        {agent.scope_kind !== "region" && <label htmlFor="agent-scope" className="text-[14px] text-ink-2">{copy.forLabel}</label>}
        {agent.scope_kind === "manager" && (
          <span className="relative">
            <select id="agent-scope" aria-label={copy.pickManager} className={sel} value={manager} disabled={running || starting} onChange={(e) => setManager(e.target.value)}>
              {catalog.managers.map((m) => <option key={m} value={m}>{m}</option>)}
            </select>
            <ChevronDown className="pointer-events-none absolute right-2.5 top-1/2 -translate-y-1/2 text-ink-2" width={14} height={14} />
          </span>
        )}
        {agent.scope_kind === "market" && (
          <span className="relative">
            <select id="agent-scope" aria-label={copy.pickMarket} className={sel} value={market} disabled={running || starting} onChange={(e) => setMarket(e.target.value)}>
              {catalog.markets.map((m) => <option key={m.market_id} value={m.market}>{m.market}</option>)}
            </select>
            <ChevronDown className="pointer-events-none absolute right-2.5 top-1/2 -translate-y-1/2 text-ink-2" width={14} height={14} />
          </span>
        )}
        <button type="button" onClick={start} disabled={running || starting || !ready}
          className={`press inline-flex h-9 items-center gap-2 rounded-lg px-4 text-[14px] font-semibold text-white ${running || starting ? "bg-grey" : "bg-blue hover:bg-navy"} disabled:cursor-default`}>
          {running ? copy.running : starting ? copy.runStarting : <><Play width={11} height={11} />{copy.runNow}</>}
        </button>
        <span className="text-[13px] text-ink-2">{agent.scope_kind === "region" ? copy.scopeFromFilters(regionLabel) : copy.timeHint(live?.progress.total || null, nouns)}</span>
      </div>

      <div className="mt-7">
        <Stepper steps={agent.steps} states={states} line={line} fraction={live ? barFraction(live.progress) : 0} note={detail} />
      </div>

      <div className="mt-8">
        <div className="pb-2 text-[15px] font-semibold">{count}</div>
        {runError && <p className="text-[13.5px] text-red">{runError}</p>}
        {run && run.status === "failed" && run.error && <div className="mb-3 rounded-lg border border-[#F0C7CC] bg-red-tint px-3 py-2.5 text-[13.5px] leading-[1.5]">{copy.runFailedLine(run.error)}</div>}
        <div>
          {running && live && live.progress.total > live.progress.done && <WritingRow title={live.progress.item ?? copy.nextUp(noun)} />}
          {running && Array.from({ length: queued }).map((_, k) => <QueuedRow key={k} label={copy.nextUp(noun)} last={k === queued - 1 && pages.length === 0} />)}
          {pages.map((p, k) => <ItemRow key={p.item_id} title={p.title} summary={p.summary || p.subtitle} severity={p.severity} right={pageLine(p)} last={k === pages.length - 1} onOpen={() => onOpenVersion(p)} />)}
          {!running && pages.length === 0 && !runError && (
            runLoading ? <p className="text-[13.5px] text-ink-2">{copy.runLoading}</p>
              : <p className="text-[14px] text-ink-2">{agent.last_run && agent.last_run.status !== "failed" ? copy.lastRunEmpty : copy.noRunsForAgent}</p>
          )}
        </div>
      </div>
    </div>
  );
}
