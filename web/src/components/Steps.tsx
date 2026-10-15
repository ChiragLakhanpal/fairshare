import { AnimatePresence, motion, useReducedMotion } from "motion/react";
import { useEffect, useState } from "react";
import { copy } from "../copy";
import { doneLabel, hintFor, stepDetail, visibleSteps } from "../lib/steps";
import type { Step } from "../lib/types";
import { Check } from "./Icons";

export function Steps({ steps }: { steps: Step[] }) {
  const reduced = useReducedMotion();
  const [now, setNow] = useState(() => Date.now());
  useEffect(() => {
    const id = setInterval(() => setNow(Date.now()), 1000);
    return () => clearInterval(id);
  }, []);
  const shown = visibleSteps(steps, now);
  const rows = shown.length ? shown : [{ step: { phase: "send", text: copy.sending, t_ms: 0 } as Step, current: true, seconds: 0 }];
  const elapsed = steps[0]?.at ? Math.floor((now - steps[0].at) / 1000) : 0;
  const hint = hintFor(rows[rows.length - 1].step.phase, elapsed);
  return (
    <div>
      <div className="flex flex-col gap-3">
        <AnimatePresence initial={false}>
          {rows.map(({ step: s, current, seconds }, i) => {
            const detail = stepDetail(s);
            return (
              <motion.div key={`${i}-${s.phase}`} initial={reduced ? false : { opacity: 0, y: 4 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.2 }} className="flex items-start gap-2.5 text-[15px] leading-[1.45]">
                {current ? (
                  <span className="mt-0.5 flex h-5 w-5 shrink-0 items-center justify-center rounded-full border-2 border-blue"><span className="h-2 w-2 animate-pulse rounded-full bg-blue" /></span>
                ) : (
                  <span className="mt-0.5 flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-tint text-navy"><Check width={11} height={11} strokeWidth={3} /></span>
                )}
                <span className={`min-w-0 flex-1 ${current ? "" : "text-ink-2"}`}>
                  <span>{current ? s.text || s.phase : doneLabel(s, seconds)}</span>
                  {current && seconds >= 2 && <span className="ml-2 text-[13px] tabular-nums text-ink-2">{seconds} s</span>}
                  {s.genie && current ? <> <a href={s.genie.url} target="_blank" rel="noreferrer" className="text-[13px]">{copy.openGenie}</a></> : null}
                  {detail && <span className={`mt-0.5 block truncate text-[13px] text-ink-2 ${s.phase === "sql" ? "font-mono" : ""}`} title={detail}>{detail}</span>}
                </span>
              </motion.div>
            );
          })}
        </AnimatePresence>
      </div>
      {hint && <p className="mt-3 text-[13.5px] text-ink-2">{hint}</p>}
    </div>
  );
}
