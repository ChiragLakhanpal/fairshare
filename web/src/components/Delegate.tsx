// Delegate: the overview of what is waiting, or one agent with its pages. Loads the run behind the open page (or the run
// in progress, or the last one, for the stepper) and polls it every two seconds while it runs; starting a run says so
// and keeps the catalog fresh through onRefresh.
import { useEffect, useState } from "react";
import { copy } from "../copy";
import { api } from "../lib/api";
import { toast } from "../lib/export";
import { nounFor, startedToast } from "../lib/runs";
import { store, useStore } from "../lib/store";
import type { AgentDef, AgentScope, AgentsCatalog, ApiError, Item, PageVersion, Run, Scope } from "../lib/types";
import { AgentView } from "./AgentView";
import { Overview } from "./Overview";

type Props = { catalog: AgentsCatalog | null; catalogError: string | null; scope: Scope; onRefresh: () => void };

export function Delegate({ catalog, catalogError, scope, onRefresh }: Props) {
  const view = useStore((s) => s.delegate);
  const [run, setRun] = useState<Run | null>(null);
  const [runLoading, setRunLoading] = useState(false);
  const [runError, setRunError] = useState<string | null>(null);
  const [starting, setStarting] = useState(false);
  const agent = catalog?.agents.find((a) => a.key === view.agent) ?? null;
  const wanted = view.agent ? view.runId ?? agent?.running?.run_id ?? agent?.last_run?.run_id ?? null : null;

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
        if (r.status !== "running") onRefresh();
      }).catch(() => {});
    }, 2000);
    return () => clearInterval(id);
  }, [runningId, onRefresh]);

  const start = async (a: AgentDef, s: AgentScope) => {
    setStarting(true);
    setRunError(null);
    try {
      const r = await api.runAgent(a.key, s);
      toast(startedToast(r.progress.total || null, nounFor(a.key)[1]), 5000);
      store.setDelegate({ agent: a.key, runId: r.run_id, itemId: null });
      setRun(r);
      onRefresh();
    } catch (e) {
      setRunError((e as ApiError).message ?? copy.errorGeneric);
    } finally {
      setStarting(false);
    }
  };

  const onItemChange = (item: Item) => {
    setRun((cur) => (cur ? { ...cur, items: cur.items.map((i) => (i.item_id === item.item_id ? item : i)) } : cur));
    onRefresh();
  };
  const open = (key: string, v: Pick<PageVersion, "run_id" | "item_id"> | null) => store.setDelegate({ agent: key, runId: v?.run_id ?? null, itemId: v?.item_id ?? null });

  if (!view.agent) return <Overview catalog={catalog} error={catalogError} onOpenAgent={(k) => open(k, null)} onOpenPage={open} />;
  if (catalogError) return <p className="px-10 pt-8 text-red">{catalogError}</p>;
  if (!catalog || !agent) return <p className="px-10 pt-8 text-[13.5px] text-ink-2">{copy.agentsLoading}</p>;
  return (
    <AgentView agent={agent} catalog={catalog} scope={scope} run={run} runLoading={runLoading} runError={runError} itemId={view.itemId} starting={starting}
      onRun={(s) => void start(agent, s)} onOpenVersion={(v) => open(agent.key, v)} onItemChange={onItemChange} />
  );
}
