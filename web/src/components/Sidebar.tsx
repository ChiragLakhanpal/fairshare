import * as Tooltip from "@radix-ui/react-tooltip";
import { copy } from "../copy";
import { groupByRecency } from "../lib/store";
import type { Conversation } from "../lib/types";
import { Chart, ChevronsLeft, ChevronsRight, Clock, File, Pen, Phone, Plus, Trash } from "./Icons";

export type QuickAction = "summary" | "brief" | "call" | "agreement";

type Props = {
  collapsed: boolean; onToggle: () => void; conversations: Conversation[]; activeId: string | null; onSelect: (id: string) => void;
  onRemove: (id: string) => void; onNew: () => void; onAction: (a: QuickAction) => void; email: string | null; inSummary: boolean;
};

const ACTIONS: { key: QuickAction; label: string; Icon: typeof Chart }[] = [
  { key: "summary", label: copy.actionSummary, Icon: Chart },
  { key: "brief", label: copy.actionBrief, Icon: Pen },
  { key: "call", label: copy.actionCall, Icon: Phone },
  { key: "agreement", label: copy.actionAgreement, Icon: File },
];

function Tip({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <Tooltip.Root delayDuration={150}>
      <Tooltip.Trigger asChild>{children}</Tooltip.Trigger>
      <Tooltip.Portal>
        <Tooltip.Content side="right" sideOffset={8} className="rounded-md bg-ink px-2.5 py-1.5 text-[13px] text-white shadow-lg">{label}</Tooltip.Content>
      </Tooltip.Portal>
    </Tooltip.Root>
  );
}

export function Sidebar({ collapsed, onToggle, conversations, activeId, onSelect, onRemove, onNew, onAction, email, inSummary }: Props) {
  const initials = (email ?? "You").split("@")[0].split(/[._-]/).map((s) => s[0]?.toUpperCase() ?? "").join("").slice(0, 2) || "Y";
  if (collapsed) {
    return (
      <Tooltip.Provider>
        <nav aria-label="Sidebar, collapsed" className="flex h-full w-14 shrink-0 flex-col items-center gap-1.5 bg-surface px-2 py-4">
          <img src="/aa-mark.svg" alt={copy.brand} className="h-[30px] w-[30px]" />
          <Tip label={copy.expandSidebar}><button type="button" onClick={onToggle} aria-label={copy.expandSidebar} className="press flex h-10 w-10 items-center justify-center rounded-lg text-ink-2 hover:bg-line-2 hover:text-ink"><ChevronsRight /></button></Tip>
          <Tip label={copy.newChat}><button type="button" onClick={onNew} aria-label={copy.newChat} className="press flex h-10 w-10 items-center justify-center rounded-lg border border-line bg-white text-ink"><Plus /></button></Tip>
          <span className="h-2" />
          {ACTIONS.map(({ key, label, Icon }) => (
            <Tip key={key} label={label}>
              <button type="button" onClick={() => onAction(key)} aria-label={label} className={`press flex h-10 w-10 items-center justify-center rounded-lg ${key === "summary" && inSummary ? "bg-white text-blue shadow-sm" : "text-ink-2 hover:bg-line-2 hover:text-ink"}`}><Icon width={18} height={18} /></button>
            </Tip>
          ))}
          <span className="h-2" />
          <Tip label={copy.recent}><button type="button" onClick={onToggle} aria-label={copy.recent} className={`press flex h-10 w-10 items-center justify-center rounded-lg ${activeId ? "bg-white text-blue shadow-sm" : "text-ink-2 hover:bg-line-2"}`}><Clock width={18} height={18} /></button></Tip>
          <span className="flex-1" />
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
        <button type="button" onClick={onToggle} aria-label={copy.collapseSidebar} className="press rounded p-1 text-ink-2 hover:bg-line-2 hover:text-ink"><ChevronsLeft /></button>
      </div>
      <button type="button" onClick={onNew} className="press flex w-full items-center gap-2 rounded-md border border-line bg-white px-3 py-2 text-sm font-medium text-ink hover:border-blue hover:text-blue"><Plus />{copy.newChat}</button>
      <div className="t-label mx-2.5 mb-1.5 mt-4">{copy.quickActions}</div>
      {ACTIONS.map(({ key, label, Icon }) => (
        <button key={key} type="button" onClick={() => onAction(key)}
          className={`press flex w-full items-center gap-2.5 rounded-md px-2.5 py-[7px] text-left text-sm ${key === "summary" && inSummary ? "bg-white font-semibold text-navy shadow-sm" : "text-ink hover:bg-line-2"}`}>
          <Icon className={key === "summary" && inSummary ? "text-blue" : "text-ink-2"} />{label}
        </button>
      ))}
      {groups.length > 0 && <div className="t-label mx-2.5 mb-1.5 mt-4">{copy.recent}</div>}
      <div className="min-h-0 flex-1 overflow-y-auto">
        {groups.map((g) => (
          <div key={g.label}>
            {groups.length > 1 && <div className="px-2.5 pb-1 pt-2 text-[11px] font-semibold uppercase tracking-wider text-grey">{g.label}</div>}
            {g.items.map((c) => (
              <div key={c.id} className={`group flex items-center rounded-md ${c.id === activeId ? "bg-white font-semibold text-navy shadow-sm" : "text-ink hover:bg-line-2"}`}>
                <button type="button" onClick={() => onSelect(c.id)} className="min-w-0 flex-1 truncate px-2.5 py-[7px] text-left text-sm" title={c.title}>{c.title}</button>
                <button type="button" onClick={() => onRemove(c.id)} aria-label={`Delete the chat "${c.title}"`} className="mr-1 hidden rounded p-1 text-ink-2 hover:text-red group-hover:block"><Trash width={14} height={14} /></button>
              </div>
            ))}
          </div>
        ))}
      </div>
      <div className="mt-2 flex items-center gap-2.5 border-t border-line px-2 pt-3.5">
        <span className="flex h-[30px] w-[30px] shrink-0 items-center justify-center rounded-full bg-tint text-xs font-bold text-navy">{initials}</span>
        <span className="text-[12.5px] leading-snug text-ink-2">{copy.signedIn(email)}</span>
      </div>
    </nav>
  );
}
