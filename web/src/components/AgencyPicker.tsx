import * as Dialog from "@radix-ui/react-dialog";
import { useEffect, useState } from "react";
import { copy } from "../copy";
import { api } from "../lib/api";
import type { Agency } from "../lib/types";
import { Close } from "./Icons";

export function AgencyPicker({ open, onOpenChange, onPick, title }: { open: boolean; onOpenChange: (o: boolean) => void; onPick: (a: Agency) => void; title: string }) {
  const [list, setList] = useState<Agency[]>([]);
  const [q, setQ] = useState("");
  useEffect(() => {
    if (open && list.length === 0) api.agencies().then(setList).catch(() => setList([]));
  }, [open, list.length]);
  const shown = list.filter((a) => a.agency_name.toLowerCase().includes(q.toLowerCase()) || a.region.toLowerCase().includes(q.toLowerCase()) || a.account_manager.toLowerCase().includes(q.toLowerCase()));
  return (
    <Dialog.Root open={open} onOpenChange={onOpenChange}>
      <Dialog.Portal>
        <Dialog.Overlay className="overlay fixed inset-0 z-40 bg-ink/30" />
        <Dialog.Content className="dialog fixed left-1/2 top-1/2 z-50 flex max-h-[80vh] w-[min(520px,94vw)] -translate-x-1/2 -translate-y-1/2 flex-col rounded-xl bg-white shadow-2xl">
          <div className="flex items-baseline justify-between gap-4 px-6 pt-5">
            <div><Dialog.Title className="text-lg font-semibold">{title}</Dialog.Title><Dialog.Description className="mt-0.5 text-[13.5px] text-ink-2">{copy.pickAgencyHint}</Dialog.Description></div>
            <Dialog.Close aria-label={copy.closeWindow} className="text-ink-2 hover:text-ink"><Close width={20} height={20} /></Dialog.Close>
          </div>
          <div className="px-6 pt-4"><input autoFocus value={q} onChange={(e) => setQ(e.target.value)} placeholder="Type a name, a region or an account manager." className="w-full rounded-lg border border-line px-3 py-2 text-[15px] focus:outline-none focus:ring-2 focus:ring-tint-line" aria-label="Search agencies" /></div>
          <div className="mt-3 overflow-y-auto px-3 pb-4">
            {shown.map((a) => (
              <button key={a.agency_id} type="button" onClick={() => onPick(a)} className="press flex w-full items-baseline justify-between gap-3 rounded-md px-3 py-2 text-left transition-colors hover:bg-surface">
                <span className="font-medium text-ink">{a.agency_name}</span><span className="text-[13px] text-ink-2">{a.region}, {a.account_manager}</span>
              </button>
            ))}
            {list.length > 0 && shown.length === 0 && <p className="px-3 py-2 text-[13.5px] text-ink-2">No agency matches that.</p>}
          </div>
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  );
}
