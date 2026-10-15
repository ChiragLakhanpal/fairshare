// Delegate: the inbox of what is waiting, or one agent with its runs. Loads the selected run and polls it every two
// seconds while it runs; starting a run says so and keeps the sidebar informed through onRefresh.
import { useCallback, useEffect, useMemo, useState } from "react";
import { copy } from "../copy";
import { api } from "../lib/api";
import { toast } from "../lib/export";
import { draftCount, nounFor, startedToast } from "../lib/runs";
import { store, useStore } from "../lib/store";
import type { AgentDef, AgentScope, AgentsCatalog, ApiError, Inbox as InboxT, Item, Run, RunHeader, Scope } from "../lib/types";
import { AgentView } from "./AgentView";
import { Inbox } from "./Inbox";

type Props = { catalog: AgentsCatalog | null; catalogError: string | null; inbox: InboxT | null; inboxLoading: boolean; scope: Scope; onRefresh: () => void };

function header(r: Run): RunHeader {
  return { run_id: r.run_id, agent: r.agent, agent_name: r.agent_name, scope: r.scope, status: r.status, created_at: r.created_at, finished_at: r.finished_at, items: r.items.length, needs_approval: draftCount(r.items) };
}

export function Delegate({ catalog, catalogError, inbox, inboxLoading, scope, onRefresh }: Props) {
  const view = useStore((s) => s.delegate);
  const [runs, setRuns] = useState<RunHeader[]>([]);
  const [run, setRun] = useState<Run | null>(null);
  const [runLoading, setRunLoading] = useState(false);
  const [runError, setRunError] = useState<string | null>(null);
  const [starting, setStarting] = useState(false);
  const agent = catalog?.agents.find((a) => a.key === view.agent) ?? null;

  const loadRuns = useCallback(() => api.runs(50).then(setRuns).catch(() => {}), []);
  useEffect(() => {
    void loadRuns();
  }, [loadRuns]);

  const agentRuns = useMemo(() => runs.filter((r) => r.agent === view.agent), [runs, view.agent]);
  const wanted = view.agent ? view.runId ?? agent?.running?.run_id ?? agentRuns[0]?.run_id ?? agent?.last_run?.run_id ?? null : null;

  useEffect(() => {
    if (!wanted) {
      setRun(null);
      return;
    }
    let gone = false;
    setRunLoading(true);
    setRunError(null);
    api.run(wanted).then((r) => !gone && setRun(r)).catch((e: ApiError) => {
      if (!gone) {
        setRun(null);
        setRunError(e.message ?? copy.errorGeneric);
      }
    }).finally(() => !gone && setRunLoading(false));
    return () => {
      gone = true;
    };
  }, [wanted]);

  const runningId = run?.status === "running" ? run.run_id : null;
  useEffect(() => {
    if (!runningId) return;
    const id = setInterval(() => {
      api.run(runningId).then((r) => {
        setRun(r);
        if (r.status !== "running") {
          void loadRuns();
          onRefresh();
        }
      }).catch(() => {});
    }, 2000);
    return () => clearInterval(id);
  }, [runningId, loadRuns, onRefresh]);

  const start = async (a: AgentDef, s: AgentScope) => {
    setStarting(true);
    setRunError(null);
    try {
      const r = await api.runAgent(a.key, s);
      toast(startedToast(r.progress.total || null, nounFor(a.key)[1]), 5000);
      store.setDelegate({ agent: a.key, runId: r.run_id, itemId: null });
      setRun(r);
      setRuns((list) => [header(r), ...list.filter((x) => x.run_id !== r.run_id)]);
      onRefresh();
    } catch (e) {
      setRunError((e as ApiError).message ?? copy.errorGeneric);
    } finally {
      setStarting(false);
    }
  };

  const onItemChange = (item: Item) => {
    setRun((cur) => (cur ? { ...cur, items: cur.items.map((i) => (i.item_id === item.item_id ? item : i)) } : cur));
    if (run) api.run(run.run_id).then((r) => { setRun(r); setRuns((list) => list.map((x) => (x.run_id === r.run_id ? header(r) : x))); }).catch(() => {});
    onRefresh();
  };

  if (!view.agent) {
    return <Inbox inbox={inbox} loading={inboxLoading} onOpen={(g, i) => store.setDelegate({ agent: g.agent, runId: g.run_id, itemId: i.item_id })} />;
  }
  if (catalogError) return <p className="px-10 pt-8 text-red">{catalogError}</p>;
  if (!catalog || !agent) return <p className="px-10 pt-8 text-[13.5px] text-ink-2">{copy.agentsLoading}</p>;
  return (
    <AgentView agent={agent} catalog={catalog} scope={scope} runs={agentRuns} run={run} runLoading={runLoading} runError={runError} itemId={view.itemId} starting={starting}
      onRun={(s) => void start(agent, s)} onSelectRun={(id) => store.setDelegate({ runId: id, itemId: null })} onOpenItem={(id) => store.setDelegate({ itemId: id })} onItemChange={onItemChange} />
  );
}
