// The small moments after an action: a check that draws itself when something was approved, and a copy button that
// says "Copied" in place for a moment (the toast still shows).
import { motion, useReducedMotion } from "motion/react";
import { useEffect, useRef, useState } from "react";
import { copy } from "../copy";
import { copyText } from "../lib/export";
import { EASE_OUT } from "../lib/motion";
import { Check, Copy } from "./Icons";

export function DrawnCheck({ size = 15, className = "" }: { size?: number; className?: string }) {
  const reduced = useReducedMotion();
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2.5} strokeLinecap="round" strokeLinejoin="round" aria-hidden="true" className={`shrink-0 ${className}`}>
      <motion.path d="M5 13l4 4L19 7" initial={reduced ? false : { pathLength: 0, opacity: 0 }} animate={{ pathLength: 1, opacity: 1 }} transition={{ duration: 0.35, ease: EASE_OUT }} />
    </svg>
  );
}

export function useCopied(ms = 1500): [boolean, () => void] {
  const [on, setOn] = useState(false);
  const timer = useRef<number | undefined>(undefined);
  useEffect(() => () => window.clearTimeout(timer.current), []);
  const mark = () => {
    setOn(true);
    window.clearTimeout(timer.current);
    timer.current = window.setTimeout(() => setOn(false), ms);
  };
  return [on, mark];
}

export function CopyLink({ text, label = copy.copyQuery, className = "" }: { text: string; label?: string; className?: string }) {
  const [done, mark] = useCopied();
  return (
    <button type="button" aria-live="polite" onClick={() => { void copyText(text); mark(); }}
      className={`press inline-flex items-center gap-1.5 text-[13px] font-medium text-blue hover:underline ${className}`}>
      {done ? <Check width={14} height={14} strokeWidth={2.5} /> : <Copy width={14} height={14} />}
      {done ? copy.copied.replace(/\.$/, "") : label}
    </button>
  );
}
