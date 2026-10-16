// The Delegate home: one line and a strip of chips for what waits across the agents, then each agent with the pages
// waiting under it. Running an agent happens on its own page.
import { copy } from "../copy";
import { pageLine, sidebarLine, waitingLine } from "../lib/runs";
import type { AgentDef, AgentsCatalog, Page } from "../lib/types";
import { ChevronRight } from "./Icons";
import { ItemRow } from "./ItemRows";

type Props = { catalog: AgentsCatalog | null; error: string | null; onOpenAgent: (key: string) => void; onOpenPage: (agent: string, p: Page) => void };

export function Overview({ catalog, error, onOpenAgent, onOpenPage }: Props) {
  const agents = catalog?.agents ?? [];
  const waiting = agents.reduce((n, a) => n + a.waiting, 0);
  const busy = agents.filter((a) => a.waiting > 0 || a.running);
  return (
    <div className="mx-auto w-full max-w-[960px] px-10 pb-16 pt-8">
      <div className="t-label">{copy.modeDelegate}</div>
      <h1 className="t-title mt-2">{copy.overviewTitle}</h1>
      {error && <p className="mt-2 text-[14px] text-red">{error}</p>}
      {!catalog && !error && <p className="mt-2 text-[14px] text-ink-2">{copy.agentsLoading}</p>}
      {catalog && (
        <>
          <p className="mt-2 text-[15px]">{waitingLine(waiting)}</p>
          {busy.length > 0 && (
            <div className="mt-3 flex flex-wrap gap-2" aria-label={copy.overviewTitle}>
              {busy.map((a) => {
                const s = sidebarLine(a);
                return (
                  <button key={a.key} type="button" onClick={() => onOpenAgent(a.key)}
                    className={`press inline-flex h-8 items-center gap-2 rounded-full border px-3 text-[13px] font-medium ${s.tone === "running" ? "border-tint-line bg-tint text-navy" : "border-line bg-white text-ink hover:border-blue hover:text-blue"}`}>
                    <span aria-hidden="true" className={`h-2 w-2 rounded-full bg-blue ${s.tone === "running" ? "animate-pulse" : ""}`} />{a.name}<span className="font-normal text-ink-2">{s.text}</span>
                  </button>
                );
              })}
            </div>
          )}
          {agents.map((a) => <AgentSection key={a.key} agent={a} onOpen={() => onOpenAgent(a.key)} onOpenPage={(p) => onOpenPage(a.key, p)} />)}
        </>
      )}
    </div>
  );
}

function AgentSection({ agent, onOpen, onOpenPage }: { agent: AgentDef; onOpen: () => void; onOpenPage: (p: Page) => void }) {
  const s = sidebarLine(agent);
  const waiting = agent.pages.filter((p) => p.status === "draft");
  return (
    <section className="mt-9" aria-label={agent.name}>
      <div className="flex items-baseline justify-between gap-4">
        <button type="button" onClick={onOpen} className="press inline-flex items-center gap-1 text-[16px] font-semibold text-ink hover:text-blue">{agent.name}<ChevronRight className="text-grey" /></button>
        <span className={`text-[13px] ${s.tone === "running" ? "text-blue" : "text-ink-2"}`}>{s.text}</span>
      </div>
      <p className="mt-1 pb-2.5 text-[14px] text-ink-2">{agent.one_liner}</p>
      {waiting.map((p, k) => <ItemRow key={p.item_id} title={p.title} summary={p.summary || p.subtitle} severity={p.severity} right={pageLine(p)} last={k === waiting.length - 1} onOpen={() => onOpenPage(p)} />)}
    </section>
  );
}
