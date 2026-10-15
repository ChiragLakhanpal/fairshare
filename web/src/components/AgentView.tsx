// One agent: what it does, the scope and Run now, the stepper that becomes the progress, and the outputs of the selected
// run. With a page open, the outputs move to a narrow list beside the document.
import { useEffect, useState } from "react";
import { copy } from "../copy";
import { monthLabel } from "../lib/format";
import { barFraction, draftCount, nounFor, progressLine, scopeLabel, stepStates, whenLabel } from "../lib/runs";
import type { AgentDef, AgentScope, AgentsCatalog, Item, Run, RunHeader, Scope } from "../lib/types";
import { Document } from "./Document";
import { ChevronDown, ChevronLeft, Play } from "./Icons";
import { ItemRow, QueuedRow, WritingRow } from "./ItemRows";
import { Stepper } from "./Stepper";

const sel = "h-9 appearance-none rounded-md border border-line bg-white pl-3 pr-8 text-sm font-medium text-ink hover:border-grey focus:outline-none focus:ring-2 focus:ring-tint-line disabled:bg-surface disabled:text-grey";

type Props = {
  agent: AgentDef; catalog: AgentsCatalog; scope: Scope; runs: RunHeader[]; run: Run | null; runLoading: boolean; runError: string | null;
  itemId: string | null; starting: boolean;
  onRun: (s: AgentScope) => void; onSelectRun: (id: string) => void; onOpenItem: (id: string | null) => void; onItemChange: (i: Item) => void;
};

export function AgentView({ agent, catalog, scope, runs, run, runLoading, runError, itemId, starting, onRun, onSelectRun, onOpenItem, onItemChange }: Props) {
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
  const selected = run && itemId ? run.items.find((i) => i.item_id === itemId) ?? null : null;

  if (run && selected) {
    const waiting = draftCount(run.items);
    return (
      <div className="flex min-h-[calc(100vh-56px)] flex-col">
        <div className="flex h-12 shrink-0 items-center gap-2 border-y hairline px-7 text-[14px]">
          <button type="button" onClick={() => onOpenItem(null)} className="press inline-flex items-center gap-1 font-medium text-blue hover:underline"><ChevronLeft width={14} height={14} />{agent.name}</button>
          <span className="text-grey">/</span>
          <span className="text-ink-2">{copy.runOf(whenLabel(run.created_at), scopeLabel(run.scope))}</span>
        </div>
        <div className="flex min-h-0 flex-1">
          <div className="w-[340px] shrink-0 self-start border-r hairline px-3 py-4" aria-label={copy.listCount(run.items.length, nouns, waiting)}>
            <div className="t-label px-3.5 pb-2">{copy.listCount(run.items.length, nouns, waiting)}</div>
            <div className="flex flex-col gap-1">
              {run.items.map((i) => <ItemRow key={i.item_id} compact title={i.title} summary={i.summary || i.subtitle} severity={i.severity} kind={i.kind} selected={i.item_id === itemId} onOpen={() => onOpenItem(i.item_id)} />)}
            </div>
          </div>
          <Document runId={run.run_id} item={selected} onChange={onItemChange} />
        </div>
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
        <div className="flex items-baseline justify-between gap-4 pb-2">
          <div className="text-[15px] font-semibold">
            {copy.listCount(run?.items.length ?? 0, nouns, run ? draftCount(run.items) : 0).split(",")[0]}{" "}
            {run && <span className="font-normal text-ink-2">{copy.fromRun(whenLabel(run.created_at), scopeLabel(run.scope))}</span>}
          </div>
          {runs.length > 1 && (
            <label className="relative text-[13.5px]">
              <span className="sr-only">{copy.pastRuns}</span>
              <select aria-label={copy.pastRuns} className="h-8 appearance-none rounded-md border border-line bg-white pl-2.5 pr-7 text-[13px] font-medium text-ink" value={run?.run_id ?? ""} onChange={(e) => onSelectRun(e.target.value)}>
                {runs.map((r) => <option key={r.run_id} value={r.run_id}>{whenLabel(r.created_at)}, {scopeLabel(r.scope)}</option>)}
              </select>
              <ChevronDown className="pointer-events-none absolute right-2 top-1/2 -translate-y-1/2 text-ink-2" width={13} height={13} />
            </label>
          )}
        </div>
        {runError && <p className="text-[13.5px] text-red">{runError}</p>}
        {!run && !runError && (runLoading ? <p className="text-[13.5px] text-ink-2">{copy.runLoading}</p> : <p className="text-[14px] text-ink-2">{copy.noRunsForAgent}</p>)}
        {run && run.status === "failed" && run.error && <div className="mb-3 rounded-lg border border-[#F0C7CC] bg-red-tint px-3 py-2.5 text-[13.5px] leading-[1.5]">{copy.runFailedLine(run.error)}</div>}
        {run && (
          <div>
            {run.items.map((i, k) => <ItemRow key={i.item_id} title={i.title} summary={i.summary || i.subtitle} severity={i.severity} kind={i.kind} last={!running && k === run.items.length - 1} onOpen={() => onOpenItem(i.item_id)} />)}
            {running && live && live.progress.total > live.progress.done && <WritingRow title={live.progress.item ?? copy.nextUp(noun)} />}
            {running && Array.from({ length: queued }).map((_, k) => <QueuedRow key={k} label={copy.nextUp(noun)} last={k === queued - 1} />)}
            {!running && run.items.length === 0 && run.status !== "failed" && <p className="text-[14px] text-ink-2">{copy.runEmpty}</p>}
          </div>
        )}
      </div>
    </div>
  );
}
