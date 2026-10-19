import * as Dialog from "@radix-ui/react-dialog";
import { useEffect, useState } from "react";
import { copy } from "../copy";
import { api } from "../lib/api";
import type { Evals, Me } from "../lib/types";
import { Check, ChevronRight, Close, External } from "./Icons";
import { TableRows } from "./Skeleton";

const PATH = [
  ["Your data", "Agency sales, seats, goals and agreements"],
  ["Metric view", "Each KPI is defined once"],
  ["Genie", "Turns the question into SQL"],
  ["Agent and checker", "Writes the answer, then matches every number"],
  ["This app", "Shows the answer, the query and what was removed"],
];

const longDate = (iso: string) => new Date(iso).toLocaleDateString("en-US", { month: "long", day: "numeric", year: "numeric" });
const ofN = (k: number | null, n: number | null) => (k === null || n === null ? "n/a" : `${k} of ${n}`);
const share = (x: number | null) => (x === null ? "n/a" : `${Math.round(x * 100)}%`);

/** One pass/fail mark. A string verdict (GOOD, CORRECT, BAD, WRONG) or a boolean; anything in between is a hollow dot; null is not run. */
function Mark({ v, title }: { v: boolean | string | null; title?: string }) {
  if (v === null || v === undefined) return <span className="inline-block w-4" aria-label="not run" />;
  const ok = v === true || v === "GOOD" || v === "CORRECT";
  const bad = v === false || v === "BAD" || v === "WRONG";
  return (
    <span title={title} aria-label={ok ? "pass" : bad ? "fail" : String(v).toLowerCase()} className="inline-flex items-center justify-center">
      {ok ? <Check width={15} height={15} className="text-blue" /> : bad ? <Close width={15} height={15} className="text-red" /> : <span className="inline-block h-2.5 w-2.5 rounded-full border border-grey" />}
    </span>
  );
}

export function HowItWorks({ open, onOpenChange, me }: { open: boolean; onOpenChange: (o: boolean) => void; me: Me | null }) {
  const links = me?.links ?? {};
  const [evals, setEvals] = useState<Evals | null | undefined>(undefined); // undefined: not loaded yet; null: not available here
  useEffect(() => {
    if (open && evals === undefined) api.evals().then(setEvals, () => setEvals(null));
  }, [open, evals]);
  const n = evals?.questions.length ?? null;
  const stamps = evals ? [evals.genie.run_at, evals.space.run_at, evals.harness.run_at].filter((d): d is string => !!d).sort() : [];
  const first = stamps[0] ? longDate(stamps[0]) : "";
  const last = stamps[stamps.length - 1] ? longDate(stamps[stamps.length - 1]) : "";
  const dates = !first ? "" : first === last ? `on ${first}` : `between ${first.replace(/, \d{4}$/, "")} and ${last}`;
  const repo = links.repo?.replace(/\/$/, "");
  const external = [
    links.genie && [copy.howLinks.genie, links.genie],
    repo && [copy.howLinks.questions, `${repo}/blob/main/evals/benchmark.yaml`],
    repo && [copy.howLinks.runs, `${repo}/blob/main/evals/results/README.md`],
    links.traces && [copy.howLinks.traces, links.traces],
    links.job && [copy.howLinks.job, links.job],
    links.dashboard && [copy.howLinks.dashboard, links.dashboard],
    repo && [copy.howLinks.repo, repo],
  ].filter((x): x is [string, string] => Array.isArray(x));
  return (
    <Dialog.Root open={open} onOpenChange={onOpenChange}>
      <Dialog.Portal>
        <Dialog.Overlay className="overlay fixed inset-0 z-40 bg-ink/30" />
        <Dialog.Content className="dialog fixed left-1/2 top-1/2 z-50 flex max-h-[90vh] w-[min(760px,94vw)] -translate-x-1/2 -translate-y-1/2 flex-col gap-5 overflow-y-auto rounded-xl bg-white px-7 pb-6 pt-6 shadow-2xl">
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
            {evals === undefined && <div className="mt-3"><TableRows n={8} label={copy.howLoading} /></div>}
            {evals === null && <p className="mt-2 text-[13px] text-ink-2">{copy.howUnavailable}</p>}
            {evals && (
              <>
                <p className="mt-2 text-[14px] leading-[1.55]">
                  {copy.howSummary(ofN(evals.genie.rate === null || n === null ? null : Math.round(evals.genie.rate * n), n), ofN(evals.space.correct, evals.space.n), share(evals.harness.backed), share(evals.harness.correct))}
                </p>
                <div className="mt-3 grid grid-cols-[1fr_repeat(4,5.5rem)] items-center gap-x-2 border-b hairline pb-1.5">
                  <span className="t-label">{n} questions</span>
                  {copy.howColumns.map(([k, help]) => <span key={k} title={help} className="t-label cursor-help text-center">{k}</span>)}
                </div>
                {evals.questions.map((q) => (
                  <div key={q.id} className="grid grid-cols-[1fr_repeat(4,5.5rem)] items-center gap-x-2 border-b hairline py-1.5 text-[13px] leading-[1.4]">
                    <span>{q.question}{q.hard && <span className="ml-1.5 text-[11px] uppercase tracking-wide text-grey">{copy.howHard}</span>}</span>
                    <span className="text-center"><Mark v={q.genie} /></span>
                    <span className="text-center"><Mark v={q.space} title={q.space_reasons.join(", ") || undefined} /></span>
                    <span className="text-center"><Mark v={q.backed} /></span>
                    <span className="text-center"><Mark v={q.judge} title={q.judge ?? undefined} /></span>
                  </div>
                ))}
                <p className="mt-2.5 text-[13px] text-ink-2">{copy.howNote(dates)}</p>
              </>
            )}
          </div>
          {external.length > 0 && (
            <div className="flex flex-wrap gap-x-5 gap-y-2 text-sm font-medium">
              {external.map(([label, href]) => (
                <a key={href} href={href} target="_blank" rel="noreferrer" className="inline-flex items-center gap-1.5">{label}<External width={14} height={14} /></a>
              ))}
            </div>
          )}
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  );
}
