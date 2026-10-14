import * as Dialog from "@radix-ui/react-dialog";
import { copy } from "../copy";
import type { Me } from "../lib/types";
import { ChevronRight, Close, External } from "./Icons";

const PATH = [
  ["Your data", "Agency sales, seats, goals and agreements"],
  ["Metric view", "Each KPI is defined once"],
  ["Genie", "Turns the question into SQL"],
  ["Agent and checker", "Writes the answer, then matches every number"],
  ["This app", "Shows the answer, the query and what was removed"],
];

export function HowItWorks({ open, onOpenChange, me }: { open: boolean; onOpenChange: (o: boolean) => void; me: Me | null }) {
  const links = me?.links ?? {};
  return (
    <Dialog.Root open={open} onOpenChange={onOpenChange}>
      <Dialog.Portal>
        <Dialog.Overlay className="fixed inset-0 z-40 bg-ink/30" />
        <Dialog.Content className="fixed left-1/2 top-1/2 z-50 flex max-h-[90vh] w-[min(720px,94vw)] -translate-x-1/2 -translate-y-1/2 flex-col gap-5 overflow-y-auto rounded-xl bg-white px-7 pb-6 pt-6 shadow-2xl">
          <div className="flex items-baseline justify-between gap-4">
            <Dialog.Title className="text-xl font-semibold tracking-tight">{copy.howTitle}</Dialog.Title>
            <Dialog.Close aria-label={copy.closeWindow} className="text-ink-2 hover:text-ink"><Close width={20} height={20} /></Dialog.Close>
          </div>
          <Dialog.Description className="text-[15.5px] leading-[1.6]">{copy.howBody}</Dialog.Description>
          <div>
            <div className="t-label">{copy.howPath}</div>
            <div className="mt-2.5 flex items-stretch gap-1.5">
              {PATH.map(([t, d], i) => (
                <div key={t} className="contents">
                  <div className="flex-1 rounded-lg border border-line bg-surface px-2 py-2.5 text-center text-[12.5px] leading-[1.35]"><b className="block text-ink">{t}</b>{d}</div>
                  {i < PATH.length - 1 && <span className="flex items-center text-grey"><ChevronRight width={14} height={14} /></span>}
                </div>
              ))}
            </div>
          </div>
          <div>
            <div className="t-label">{copy.howScores}</div>
            <div className="mt-2">
              {copy.howScoreRows.map(([k, v]) => (
                <div key={k} className="flex justify-between gap-4 border-t hairline py-2 text-sm last:border-b"><span>{k}</span><b className="whitespace-nowrap">{v}</b></div>
              ))}
            </div>
            <p className="mt-2.5 text-[13px] text-ink-2">{copy.howNote}</p>
          </div>
          <div className="flex flex-wrap gap-x-5 gap-y-2 text-sm font-medium">
            {links.genie && <a href={links.genie} target="_blank" rel="noreferrer" className="inline-flex items-center gap-1.5">The Genie space<External width={14} height={14} /></a>}
            {links.dashboard && <a href={links.dashboard} target="_blank" rel="noreferrer" className="inline-flex items-center gap-1.5">The sales dashboard<External width={14} height={14} /></a>}
            {links.traces && <a href={links.traces} target="_blank" rel="noreferrer" className="inline-flex items-center gap-1.5">Traces in MLflow<External width={14} height={14} /></a>}
            {links.repo && <a href={links.repo} target="_blank" rel="noreferrer" className="inline-flex items-center gap-1.5">The code<External width={14} height={14} /></a>}
          </div>
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  );
}
