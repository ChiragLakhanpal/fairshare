import { useEffect, useRef, useState } from "react";
import { copy } from "../copy";
import { monthLabel } from "../lib/format";
import { statusLabel, whenLabel } from "../lib/runs";
import type { AgentDef, AgentScope, Scope } from "../lib/types";
import { ChevronDown, Play } from "./Icons";

const sel = "appearance-none rounded-md border border-line bg-white py-1.5 pl-3 pr-8 text-sm font-medium text-ink hover:border-grey focus:outline-none focus:ring-2 focus:ring-tint-line";

type Props = { agent: AgentDef; managers: string[]; markets: { market_id: number; market: string }[]; scope: Scope; busy: boolean; focused: boolean; onRun: (s: AgentScope) => void };

export function AgentCard({ agent, managers, markets, scope, busy, focused, onRun }: Props) {
  const ref = useRef<HTMLDivElement>(null);
  const [manager, setManager] = useState(managers[0] ?? "");
  const [market, setMarket] = useState(markets[0]?.market ?? "");
  useEffect(() => {
    if (!manager && managers[0]) setManager(managers[0]);
    if (!market && markets[0]) setMarket(markets[0].market);
  }, [managers, markets, manager, market]);
  useEffect(() => {
    if (focused) ref.current?.scrollIntoView({ block: "center", behavior: "smooth" });
  }, [focused]);
  const regionLabel = `${scope.region === "All" ? "all regions" : `the ${scope.region} region`}, ${monthLabel(scope.month)}`;
  const run = () => onRun(agent.scope_kind === "manager" ? { manager, month: scope.month } : agent.scope_kind === "market" ? { market } : { region: scope.region, month: scope.month });
  const ready = agent.scope_kind === "manager" ? !!manager && !!scope.month : agent.scope_kind === "market" ? !!market : !!scope.month;
  return (
    <div ref={ref} className={`rounded-xl border bg-white p-5 ${focused ? "border-blue ring-2 ring-tint-line" : "border-line"}`}>
      <h3 className="text-[16px] font-semibold text-ink">{agent.name}</h3>
      <p className="mt-1 text-[14px] leading-[1.5] text-ink">{agent.summary}</p>
      <dl className="mt-3 grid grid-cols-[auto_minmax(0,1fr)] gap-x-3 gap-y-1 text-[13px] leading-[1.45]">
        <dt className="text-ink-2">{copy.reads}</dt><dd>{agent.reads.join(", ")}</dd>
        <dt className="text-ink-2">{copy.writes}</dt><dd>{agent.writes.join(", ")}</dd>
        <dt className="text-ink-2">{copy.approver}</dt><dd>{agent.approver}</dd>
      </dl>
      <div className="mt-4 flex flex-wrap items-center gap-2.5">
        {agent.scope_kind === "manager" && (
          <label className="relative">
            <span className="sr-only">{copy.pickManager}</span>
            <select aria-label={`${copy.pickManager} for ${agent.name}`} className={sel} value={manager} onChange={(e) => setManager(e.target.value)}>
              {managers.map((m) => <option key={m} value={m}>{m}</option>)}
            </select>
            <ChevronDown className="pointer-events-none absolute right-2.5 top-1/2 -translate-y-1/2 text-ink-2" width={14} height={14} />
          </label>
        )}
        {agent.scope_kind === "market" && (
          <label className="relative">
            <span className="sr-only">{copy.pickMarket}</span>
            <select aria-label={`${copy.pickMarket} for ${agent.name}`} className={sel} value={market} onChange={(e) => setMarket(e.target.value)}>
              {markets.map((m) => <option key={m.market_id} value={m.market}>{m.market}</option>)}
            </select>
            <ChevronDown className="pointer-events-none absolute right-2.5 top-1/2 -translate-y-1/2 text-ink-2" width={14} height={14} />
          </label>
        )}
        {agent.scope_kind === "region" && <span className="text-[13px] text-ink-2">{copy.scopeFromFilters(regionLabel)}</span>}
        <button type="button" onClick={run} disabled={busy || !ready} aria-label={`${copy.runNow}: ${agent.name}`}
          className="press ml-auto inline-flex items-center gap-1.5 rounded-lg bg-blue px-3.5 py-2 text-sm font-semibold text-white hover:bg-navy disabled:opacity-60">
          <Play width={11} height={11} />{busy ? copy.runStarting : copy.runNow}
        </button>
      </div>
      <p className="mt-3 text-[12.5px] text-ink-2">{agent.last_run ? copy.lastRun(whenLabel(agent.last_run.created_at), statusLabel(agent.last_run.status)) : copy.noRunYet}</p>
    </div>
  );
}
