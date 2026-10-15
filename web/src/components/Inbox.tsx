// The landing for Delegate: what is waiting for a decision, grouped by the run that wrote it.
import { copy } from "../copy";
import { scopeLabel, whenLabel } from "../lib/runs";
import type { Inbox as InboxT, InboxGroup, InboxItem } from "../lib/types";
import { ItemRow } from "./ItemRows";

export function Inbox({ inbox, loading, onOpen }: { inbox: InboxT | null; loading: boolean; onOpen: (g: InboxGroup, i: InboxItem) => void }) {
  const waiting = inbox?.waiting ?? 0;
  const groups = (inbox?.groups ?? []).filter((g) => g.items.length > 0);
  return (
    <div className="mx-auto w-full max-w-[960px] px-10 pb-16 pt-8">
      <h1 className="t-title">{copy.inboxTitle}</h1>
      <p className="mt-1.5 text-[14px] text-ink-2">{loading && !inbox ? copy.inboxLoading : copy.inboxLine(waiting)}</p>
      {!loading && inbox && groups.length === 0 && <p className="mt-7 text-[15px] text-ink">{copy.inboxEmpty}</p>}
      {groups.map((g) => (
        <section key={g.run_id} className="mt-8" aria-label={g.agent_name}>
          <div className="t-label px-2 pb-1.5">{`${g.agent_name}, ${scopeLabel(g.scope)}, ${whenLabel(g.created_at)}`}</div>
          {g.items.map((i, k) => (
            <ItemRow key={i.item_id} title={i.title} summary={i.summary} severity={i.severity} kind={i.kind} last={k === g.items.length - 1} onOpen={() => onOpen(g, i)} />
          ))}
        </section>
      ))}
    </div>
  );
}
