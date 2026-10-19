import { motion, useReducedMotion } from "motion/react";
import { useEffect, useRef } from "react";
import { copy } from "../copy";
import { monthLabel } from "../lib/format";
import { relatedSignal, signalFacts } from "../lib/signals";
import type { ApiError, Brief as BriefT, Conversation as ConversationT, SignalAction, Signals, Turn } from "../lib/types";
import { Answer } from "./Answer";
import { Brief } from "./Brief";
import { Info } from "./Icons";
import { SeverityDot } from "./ItemRows";
import { SignalLine } from "./Signals";
import { Steps } from "./Steps";

function ErrorNote({ e }: { e: ApiError }) {
  const text = e.code === "no_model" ? copy.noModel : e.code === "cancelled" ? copy.stopped : e.code === "busy" || e.code === "timeout" || e.code === "reload" ? e.message : `${copy.errorGeneric} (${e.message})`;
  return <div className="flex items-start gap-2 text-[14.5px] text-ink-2"><Info className="mt-[3px] shrink-0" width={15} height={15} /><span>{text}</span></div>;
}

type Props = {
  c: ConversationT; onFollowUp: (q: string) => void; onHow: () => void; onApproved: (index: number, b: BriefT) => void; onTyped: (index: number) => void;
  signals: Signals | null; onAction: (a: SignalAction) => void;
};

export function Conversation({ c, onFollowUp, onHow, onApproved, onTyped, signals, onAction }: Props) {
  const reduced = useReducedMotion();
  const lastUser = useRef<HTMLDivElement>(null);
  const lastUserIndex = c.turns.map((t) => t.role).lastIndexOf("user");
  useEffect(() => {
    // the newest question goes to the top of the view, under the strip, so a long answer reads from its question down
    lastUser.current?.scrollIntoView({ block: "start", behavior: reduced ? "auto" : "smooth" });
  }, [c.id, c.turns.length, reduced]);
  // under an answer about an agency, the one "worth knowing" line about that agency this month; nothing for general or meta
  // answers, and nothing until the answer has finished typing itself out
  const related = (t: Turn, i: number) => {
    if (t.fresh || !signals || !t.answer || t.answer.kind === "general" || t.answer.kind === "meta") return null;
    const question = c.turns[i - 1]?.role === "user" ? c.turns[i - 1].text : "";
    const s = relatedSignal(`${question} ${t.answer.verified_text || t.text}`, signals.signals);
    if (!s) return null;
    return (
      <motion.div initial={reduced ? false : { opacity: 0 }} animate={{ opacity: 1 }} transition={{ duration: 0.25 }} className="no-print mt-3.5 flex items-start gap-2.5 text-[13.5px] leading-[1.5]">
        <SeverityDot s={s.severity} className="mt-[7px]" />
        <SignalLine s={s} facts={signalFacts(signals)} onAction={onAction} lead={copy.signalsRelated(monthLabel(signals.month))} />
      </motion.div>
    );
  };
  return (
    <div className="mx-auto flex w-full max-w-[760px] flex-col gap-6 px-6 pt-6">
      {c.turns.map((t, i) =>
        t.role === "user" ? (
          <div key={i} ref={i === lastUserIndex ? lastUser : undefined} className="max-w-[80%] scroll-mt-20 self-end rounded-[12px_12px_4px_12px] bg-surface px-4 py-2.5 text-[15px]">{t.text}</div>
        ) : (
          <motion.div key={`${i}-${t.pending ? "pending" : "done"}`} initial={reduced ? false : { opacity: 0, y: 6 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.25 }}
            className={`text-[15.5px] leading-[1.6] ${i === c.turns.length - 1 ? "min-h-[calc(100vh-240px)]" : ""}`}>
            {t.pending ? <Steps steps={t.steps ?? []} /> : t.error ? <ErrorNote e={t.error} /> : t.brief ? <Brief brief={t.brief} fresh={!!t.fresh} onTyped={() => onTyped(i)} onApproved={(b) => onApproved(i, b)} /> : t.answer ? <><Answer a={t.answer} fresh={!!t.fresh} onTyped={() => onTyped(i)} onFollowUp={onFollowUp} onHow={onHow} />{related(t, i)}</> : <span>{t.text}</span>}
          </motion.div>
        ),
      )}
    </div>
  );
}
