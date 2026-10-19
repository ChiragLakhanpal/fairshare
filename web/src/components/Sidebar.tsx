import * as Tooltip from "@radix-ui/react-tooltip";
import { AnimatePresence, motion, useReducedMotion } from "motion/react";
import { copy } from "../copy";
import { SPRING } from "../lib/motion";
import { sidebarLine } from "../lib/runs";
import { groupByRecency, type Mode } from "../lib/store";
import type { AgentDef, Conversation } from "../lib/types";
import { Agents, Chart, ChatIcon, ChevronsLeft, ChevronsRight, Clock, File, Inbox as InboxIcon, Pen, Phone, Plus, Trash } from "./Icons";

export type QuickAction = "summary" | "brief" | "call" | "agreement";

type Props = {
  collapsed: boolean; onToggle: () => void; conversations: Conversation[]; activeId: string | null; onSelect: (id: string) => void;
  onRemove: (id: string) => void; onNew: () => void; onAction: (a: QuickAction) => void; email: string | null; inSummary: boolean;
  mode: Mode; onMode: (m: Mode) => void; agents: AgentDef[]; view: string | null; onOverview: () => void; onAgent: (key: string) => void;
};

const ACTIONS: { key: QuickAction; label: string; Icon: typeof Chart }[] = [
  { key: "summary", label: copy.actionSummary, Icon: Chart },
  { key: "brief", label: copy.actionBrief, Icon: Pen },
  { key: "call", label: copy.actionCall, Icon: Phone },
  { key: "agreement", label: copy.actionAgreement, Icon: File },
];
const MODES: { key: Mode; label: string; Icon: typeof Chart }[] = [
  { key: "ask", label: copy.modeAsk, Icon: ChatIcon },
  { key: "delegate", label: copy.modeDelegate, Icon: Agents },
];

function Tip({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <Tooltip.Root delayDuration={150}>
      <Tooltip.Trigger asChild>{children}</Tooltip.Trigger>
      <Tooltip.Portal>
        <Tooltip.Content side="right" sideOffset={8} className="menu rounded-md bg-ink px-2.5 py-1.5 text-[13px] text-white shadow-lg">{label}</Tooltip.Content>
      </Tooltip.Portal>
    </Tooltip.Root>
  );
}

function Dot({ tone }: { tone: "running" | "waiting" | "quiet" | "none" | "failed" }) {
  const look = tone === "running" ? "animate-pulse bg-blue" : tone === "waiting" ? "bg-blue" : tone === "failed" ? "bg-red" : "bg-line";
  return <span aria-hidden="true" className={`mt-2 h-2 w-2 shrink-0 rounded-full ${look}`} />;
}

/** The white pill behind the chosen mode slides to the other button instead of jumping. */
function Pill({ id, reduced }: { id: string; reduced: boolean | null }) {
  return <motion.span layoutId={id} aria-hidden="true" className="absolute inset-0 -z-10 rounded-md bg-white shadow-sm" transition={reduced ? { duration: 0 } : SPRING} />;
}

/** The part of the sidebar that belongs to one mode crossfades when the mode changes. */
function Pane({ k, children }: { k: string; children: React.ReactNode }) {
  return (
    <AnimatePresence mode="wait" initial={false}>
      <motion.div key={k} initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} transition={{ duration: 0.14 }} className="flex min-h-0 flex-1 flex-col gap-1">
        {children}
      </motion.div>
    </AnimatePresence>
  );
}

export function Sidebar({ collapsed, onToggle, conversations, activeId, onSelect, onRemove, onNew, onAction, email, inSummary, mode, onMode, agents, view, onOverview, onAgent }: Props) {
  const reduced = useReducedMotion();
  const initials = (email ?? "You").split("@")[0].split(/[._-]/).map((s) => s[0]?.toUpperCase() ?? "").join("").slice(0, 2) || "Y";
  const anyRunning = agents.some((a) => a.running);
  if (collapsed) {
    return (
      <Tooltip.Provider>
        <nav aria-label="Sidebar, collapsed" className="flex h-full w-14 shrink-0 flex-col items-center gap-1.5 bg-surface px-2 py-4">
          <img src="/aa-mark.svg" alt={copy.brand} className="h-[30px] w-[30px]" />
          <Tip label={copy.expandSidebar}><button type="button" onClick={onToggle} aria-label={copy.expandSidebar} className="press flex h-10 w-10 items-center justify-center rounded-lg text-ink-2 transition-colors hover:bg-line-2 hover:text-ink"><ChevronsRight /></button></Tip>
          <div role="group" aria-label={copy.modeSwitch} className="flex flex-col gap-0.5 rounded-lg bg-line-2 p-0.5">
            {MODES.map(({ key, label, Icon }) => (
              <Tip key={key} label={label}>
                <button type="button" aria-pressed={mode === key} aria-label={label} onClick={() => onMode(key)} className={`press relative z-10 flex h-9 w-9 items-center justify-center rounded-md transition-colors ${mode === key ? "text-navy" : "text-ink-2 hover:text-ink"}`}>
                  {mode === key && <Pill id="mode-pill-rail" reduced={reduced} />}
                  <Icon width={17} height={17} />
                  {key === "delegate" && anyRunning && <span aria-hidden="true" className="absolute right-1 top-1 h-2 w-2 animate-pulse rounded-full bg-blue" />}
                </button>
              </Tip>
            ))}
          </div>
          <Pane k={mode}>
            {mode === "ask" ? (
              <div className="flex flex-col items-center gap-1.5">
                <Tip label={copy.newChat}><button type="button" onClick={onNew} aria-label={copy.newChat} className="press flex h-10 w-10 items-center justify-center rounded-lg border border-line bg-white text-ink transition-colors hover:border-blue hover:text-blue"><Plus /></button></Tip>
                <span className="h-2" />
                {ACTIONS.map(({ key, label, Icon }) => (
                  <Tip key={key} label={label}>
                    <button type="button" onClick={() => onAction(key)} aria-label={label} className={`press flex h-10 w-10 items-center justify-center rounded-lg transition-colors ${key === "summary" && inSummary ? "bg-white text-blue shadow-sm" : "text-ink-2 hover:bg-line-2 hover:text-ink"}`}><Icon width={18} height={18} /></button>
                  </Tip>
                ))}
                <span className="h-2" />
                <Tip label={copy.recent}><button type="button" onClick={onToggle} aria-label={copy.recent} className={`press flex h-10 w-10 items-center justify-center rounded-lg transition-colors ${activeId ? "bg-white text-blue shadow-sm" : "text-ink-2 hover:bg-line-2"}`}><Clock width={18} height={18} /></button></Tip>
              </div>
            ) : (
              <div className="flex flex-col items-center gap-1.5">
                <span className="h-2" />
                <Tip label={copy.overviewTitle}><button type="button" onClick={onOverview} aria-label={copy.overviewTitle} className={`press flex h-10 w-10 items-center justify-center rounded-lg transition-colors ${view === null ? "bg-white text-blue shadow-sm" : "text-ink-2 hover:bg-line-2 hover:text-ink"}`}><InboxIcon width={18} height={18} /></button></Tip>
                {agents.map((a) => {
                  const s = sidebarLine(a);
                  return (
                    <Tip key={a.key} label={`${a.name}: ${s.text}`}>
                      <button type="button" onClick={() => onAgent(a.key)} aria-label={`${a.name}: ${s.text}`} className={`press relative flex h-10 w-10 items-center justify-center rounded-lg transition-colors ${view === a.key ? "bg-white text-blue shadow-sm" : "text-ink-2 hover:bg-line-2 hover:text-ink"}`}>
                        <Agents width={18} height={18} />
                        {(s.tone === "running" || s.tone === "waiting") && <span aria-hidden="true" className={`absolute right-1.5 top-1.5 h-2 w-2 rounded-full bg-blue ${s.tone === "running" ? "animate-pulse" : ""}`} />}
                      </button>
                    </Tip>
                  );
                })}
              </div>
            )}
          </Pane>
          <Tip label={copy.signedIn(email)}><span className="flex h-[30px] w-[30px] items-center justify-center rounded-full bg-tint text-xs font-bold text-navy" aria-label={copy.signedIn(email)}>{initials}</span></Tip>
        </nav>
      </Tooltip.Provider>
    );
  }
  const groups = groupByRecency(conversations);
  return (
    <nav aria-label="Sidebar" className="flex h-full w-64 shrink-0 flex-col gap-1 bg-surface px-3 pb-4 pt-[18px]">
      <div className="flex items-start gap-2 px-2 pb-3.5">
        <span className="min-w-0 flex-1">
          <img src="/aa-logo.svg" alt={copy.brand} className="h-auto w-[170px]" />
          <span className="mt-1 block text-[13px] font-semibold tracking-tight text-navy">{copy.product}</span>
        </span>
        <button type="button" onClick={onToggle} aria-label={copy.collapseSidebar} className="press rounded p-1 text-ink-2 transition-colors hover:bg-line-2 hover:text-ink"><ChevronsLeft /></button>
      </div>
      <div role="group" aria-label={copy.modeSwitch} className="mb-2 grid grid-cols-2 rounded-lg bg-line-2 p-0.5">
        {MODES.map(({ key, label, Icon }) => (
          <button key={key} type="button" aria-pressed={mode === key} onClick={() => onMode(key)} className={`press relative z-10 inline-flex items-center justify-center gap-1.5 rounded-md py-1.5 text-sm font-semibold transition-colors ${mode === key ? "text-navy" : "text-ink-2 hover:text-ink"}`}>
            {mode === key && <Pill id="mode-pill" reduced={reduced} />}
            <Icon width={15} height={15} />{label}
            {key === "delegate" && anyRunning && mode !== "delegate" && <span aria-hidden="true" className="absolute right-2 top-1/2 h-2 w-2 -translate-y-1/2 animate-pulse rounded-full bg-blue" />}
          </button>
        ))}
      </div>
      <Pane k={mode}>
        {mode === "delegate" ? (
          <>
            <button type="button" onClick={onOverview} aria-current={view === null ? "page" : undefined}
              className={`press flex w-full items-center gap-2.5 rounded-md px-2.5 py-[7px] text-left text-sm transition-colors ${view === null ? "bg-white font-semibold text-navy shadow-sm" : "font-medium text-ink hover:bg-line-2"}`}>
              <InboxIcon className={view === null ? "text-blue" : "text-ink-2"} />{copy.overviewTitle}
            </button>
            <div className="t-label mx-2.5 mb-1.5 mt-4">{copy.agentsLabel}</div>
            {agents.map((a) => {
              const s = sidebarLine(a);
              return (
                <button key={a.key} type="button" onClick={() => onAgent(a.key)} aria-current={view === a.key ? "page" : undefined}
                  className={`press flex w-full items-start gap-2.5 rounded-lg px-2.5 py-2 text-left transition-colors ${view === a.key ? "bg-white shadow-sm" : "hover:bg-line-2"}`}>
                  <Dot tone={s.tone} />
                  <span className="min-w-0">
                    <span className={`block text-sm ${view === a.key ? "font-semibold text-navy" : "font-medium text-ink"}`}>{a.name}</span>
                    <span className={`block text-[12.5px] ${s.tone === "running" ? "text-blue" : "text-ink-2"}`}>{s.text}</span>
                  </span>
                </button>
              );
            })}
            <div className="min-h-0 flex-1" />
          </>
        ) : (
          <>
            <button type="button" onClick={onNew} className="press flex w-full items-center gap-2 rounded-md border border-line bg-white px-3 py-2 text-sm font-medium text-ink transition-colors hover:border-blue hover:text-blue"><Plus />{copy.newChat}</button>
            <div className="t-label mx-2.5 mb-1.5 mt-4">{copy.quickActions}</div>
            {ACTIONS.map(({ key, label, Icon }) => (
              <button key={key} type="button" onClick={() => onAction(key)}
                className={`press flex w-full items-center gap-2.5 rounded-md px-2.5 py-[7px] text-left text-sm transition-colors ${key === "summary" && inSummary ? "bg-white font-semibold text-navy shadow-sm" : "text-ink hover:bg-line-2"}`}>
                <Icon className={`transition-colors ${key === "summary" && inSummary ? "text-blue" : "text-ink-2"}`} />{label}
              </button>
            ))}
            {groups.length > 0 && <div className="t-label mx-2.5 mb-1.5 mt-4">{copy.recent}</div>}
            <div className="min-h-0 flex-1 overflow-y-auto">
              {groups.map((g) => (
                <div key={g.label}>
                  {groups.length > 1 && <div className="px-2.5 pb-1 pt-2 text-[11px] font-semibold uppercase tracking-wider text-grey">{g.label}</div>}
                  {g.items.map((c) => (
                    <div key={c.id} className={`group flex items-center rounded-md transition-colors ${c.id === activeId ? "bg-white font-semibold text-navy shadow-sm" : "text-ink hover:bg-line-2"}`}>
                      <button type="button" onClick={() => onSelect(c.id)} className="min-w-0 flex-1 truncate px-2.5 py-[7px] text-left text-sm" title={c.title}>{c.title}</button>
                      <button type="button" onClick={() => onRemove(c.id)} aria-label={`Delete the chat "${c.title}"`} className="mr-1 hidden rounded p-1 text-ink-2 hover:text-red group-hover:block"><Trash width={14} height={14} /></button>
                    </div>
                  ))}
                </div>
              ))}
            </div>
          </>
        )}
      </Pane>
      <div className="mt-2 flex items-center gap-2.5 border-t border-line px-2 pt-3.5">
        <span className="flex h-[30px] w-[30px] shrink-0 items-center justify-center rounded-full bg-tint text-xs font-bold text-navy">{initials}</span>
        <span className="text-[12.5px] leading-snug text-ink-2">{copy.signedIn(email)}</span>
      </div>
    </nav>
  );
}
