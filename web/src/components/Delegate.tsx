// Delegate: the agents, their runs, and the items waiting for a decision. Polls a running run every two seconds.
import { useCallback, useEffect, useState } from "react";
import { copy } from "../copy";
import { api } from "../lib/api";
import { draftCount } from "../lib/runs";
import { store, useStore } from "../lib/store";
import type { AgentDef, AgentScope, AgentsCatalog, ApiError, Item, Run, RunHeader, Scope } from "../lib/types";
import { AgentCard } from "./AgentCard";
import { RunList } from "./RunList";
import { RunView } from "./RunView";

type Props = { catalog: AgentsCatalog | null; catalogError: string | null; scope: Scope; focusKey: string | null; onRefreshCatalog: () => void };

function header(r: Run): RunHeader {
  return { run_id: r.run_id, agent: r.agent, agent_name: r.agent_name, scope: r.scope, status: r.status, created_at: r.created_at, finished_at: r.finished_at, items: r.items.length, needs_approval: draftCount(r.items) };
}

export function Delegate({ catalog, catalogError, scope, focusKey, onRefreshCatalog }: Props) {
  const runId = useStore((s) => s.runId);
  const [runs, setRuns] = useState<RunHeader[]>([]);
  const [runsLoading, setRunsLoading] = useState(true);
  const [run, setRun] = useState<Run | null>(null);
  const [runError, setRunError] = useState<string | null>(null);
  const [starting, setStarting] = useState<string | null>(null);
  const crmLabel = catalog?.crm_label || copy.crmStandIn;

  const loadRuns = useCallback(() => api.runs().then(setRuns).catch(() => {}).finally(() => setRunsLoading(false)), []);
  useEffect(() => {
    void loadRuns();
  }, [loadRuns]);

  useEffect(() => {
    if (!runId) {
      setRun(null);
      return;
    }
    let gone = false;
    setRunError(null);
    api.run(runId).then((r) => !gone && setRun(r)).catch((e: ApiError) => {
      if (!gone) {
        setRun(null);
        setRunError(e.message ?? copy.errorGeneric);
      }
    });
    return () => {
      gone = true;
    };
  }, [runId]);

  const running = run?.status === "running" ? run.run_id : null;
  useEffect(() => {
    if (!running) return;
    const id = setInterval(() => {
      api.run(running).then((r) => {
        setRun(r);
        if (r.status !== "running") {
          void loadRuns();
          onRefreshCatalog();
        }
      }).catch(() => {});
    }, 2000);
    return () => clearInterval(id);
  }, [running, loadRuns, onRefreshCatalog]);

  const start = async (agent: AgentDef, s: AgentScope) => {
    setStarting(agent.key);
    setRunError(null);
    try {
      const r = await api.runAgent(agent.key, s);
      setRun(r);
      store.setRun(r.run_id);
      setRuns((list) => [header(r), ...list.filter((x) => x.run_id !== r.run_id)]);
    } catch (e) {
      setRunError((e as ApiError).message ?? copy.errorGeneric);
    } finally {
      setStarting(null);
    }
  };

  const onItemChange = (item: Item) => {
    setRun((cur) => (cur ? { ...cur, items: cur.items.map((i) => (i.item_id === item.item_id ? item : i)) } : cur));
    if (run) api.run(run.run_id).then((r) => { setRun(r); setRuns((list) => list.map((x) => (x.run_id === r.run_id ? header(r) : x))); }).catch(() => {});
  };

  return (
    <div className="mx-auto w-full max-w-[980px] px-6 pb-16 pt-9">
      <div className="t-label">{copy.modeDelegate}</div>
      <h1 className="t-title mt-2">{copy.delegateTitle}</h1>
      <p className="mt-2 max-w-[640px] text-[15px] leading-[1.55] text-ink-2">{copy.delegateIntro}</p>

      <div className="t-label mt-8">{copy.agentsLabel}</div>
      {catalogError ? <p className="mt-2 text-red">{catalogError}</p> : !catalog ? <p className="mt-2 text-[13.5px] text-ink-2">{copy.agentsLoading}</p> : (
        <div className="mt-3 grid gap-4 md:grid-cols-2">
          {catalog.agents.map((a) => (
            <AgentCard key={a.key} agent={a} managers={catalog.managers} markets={catalog.markets} scope={scope} busy={starting === a.key} focused={focusKey === a.key} onRun={(s) => void start(a, s)} />
          ))}
        </div>
      )}

      <div className="t-label mt-10">{copy.runsLabel}</div>
      <div className="mt-3 grid gap-6 md:grid-cols-[280px_minmax(0,1fr)]">
        <div><RunList runs={runs} selected={runId} onSelect={(id) => store.setRun(id)} loading={runsLoading} /></div>
        <div>
          {runError ? <p className="text-[13.5px] text-red">{runError}</p> : run ? <RunView run={run} crmLabel={crmLabel} onItemChange={onItemChange} /> : runId ? <p className="text-[13.5px] text-ink-2">{copy.runLoading}</p> : null}
        </div>
      </div>
    </div>
  );
}
