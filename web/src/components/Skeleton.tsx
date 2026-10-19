// Loading shown as shape, not as a sentence: shimmering bars in the layout the content will take, so nothing jumps when
// it lands. One primitive, a few arrangements, and on the two first-paint screens the Flight Symbol gliding in once along
// the takeoff diagonal.
import { motion, useReducedMotion } from "motion/react";
import { EASE_OUT } from "../lib/motion";

export function Bar({ w = "100%", h = 12, className = "" }: { w?: number | string; h?: number; className?: string }) {
  return <span aria-hidden="true" className={`shimmer block rounded ${className}`} style={{ width: w, height: h }} />;
}

/** The Flight Symbol arriving: in from the lower left along the takeoff line, once, while the page loads under it. */
export function Approach() {
  const reduced = useReducedMotion();
  return (
    <motion.img src="/aa-mark.svg" alt="" aria-hidden="true" className="h-[22px] w-[22px]" initial={reduced ? false : { opacity: 0, x: -28, y: 18 }}
      animate={{ opacity: 1, x: 0, y: 0 }} transition={{ duration: 0.7, ease: EASE_OUT }} />
  );
}

/** A few lines of text that are not here yet. */
export function Lines({ n = 3, label }: { n?: number; label: string }) {
  const widths = ["100%", "92%", "76%", "88%", "64%"];
  return (
    <div aria-busy="true" aria-label={label} role="status" className="flex flex-col gap-2.5">
      {Array.from({ length: n }).map((_, i) => <Bar key={i} w={widths[i % widths.length]} h={11} />)}
    </div>
  );
}

/** Rows in the shape of a page list: a dot, a name, a line, a status. */
export function Rows({ n = 3, label }: { n?: number; label: string }) {
  return (
    <div aria-busy="true" aria-label={label} role="status">
      {Array.from({ length: n }).map((_, i) => (
        <div key={i} className={`grid grid-cols-[10px_230px_minmax(0,1fr)_auto] items-center gap-3.5 border-t hairline px-2 py-[15px] ${i === n - 1 ? "border-b" : ""}`}>
          <span aria-hidden="true" className="h-2 w-2 rounded-full bg-line-2" />
          <Bar w={i % 2 ? 150 : 190} h={12} />
          <Bar w={i % 2 ? "70%" : "85%"} h={11} />
          <Bar w={72} h={10} />
        </div>
      ))}
    </div>
  );
}

/** Rows in the shape of a table: one wide cell and four marks. */
export function TableRows({ n = 8, label }: { n?: number; label: string }) {
  return (
    <div aria-busy="true" aria-label={label} role="status">
      {Array.from({ length: n }).map((_, i) => (
        <div key={i} className="grid grid-cols-[1fr_repeat(4,5.5rem)] items-center gap-x-2 border-b hairline py-2.5">
          <Bar w={`${55 + ((i * 17) % 35)}%`} h={11} />
          {[0, 1, 2, 3].map((k) => <span key={k} className="flex justify-center"><Bar w={14} h={14} className="!rounded-full" /></span>)}
        </div>
      ))}
    </div>
  );
}

/** The month's summary before it arrives: the greeting line, the headline, the five numbers, the movers. */
export function SummarySkeleton() {
  return (
    <div aria-busy="true" aria-label="Loading the month." role="status">
      <div className="flex items-center gap-3"><Approach /><Bar w={256} h={12} /></div>
      <Bar w={520} h={28} className="mt-4 max-w-full" />
      <div className="mt-9 grid grid-cols-2 gap-x-5 gap-y-7 sm:grid-cols-3 md:grid-cols-5">
        {[0, 1, 2, 3, 4].map((i) => (
          <div key={i}><Bar w={96} h={36} /><Bar w={80} h={12} className="mt-2.5" /><Bar w={112} h={12} className="mt-1.5" /></div>
        ))}
      </div>
      <Bar w={288} h={16} className="mt-10" />
      {[0, 1, 2].map((i) => <Bar key={i} h={16} className="mt-4" />)}
    </div>
  );
}

/** The Delegate overview before the agents arrive: the title, the line, two agents with their rows. */
export function OverviewSkeleton() {
  return (
    <div aria-busy="true" aria-label="Loading the agents." role="status" className="mx-auto w-full max-w-[960px] px-10 pb-16 pt-8">
      <div className="flex items-center gap-3"><Approach /><Bar w={64} h={12} /></div>
      <Bar w={180} h={28} className="mt-3" />
      <Bar w={300} h={14} className="mt-3" />
      {[0, 1].map((i) => (
        <div key={i} className="mt-9">
          <Bar w={i ? 160 : 210} h={16} />
          <Bar w={i ? 320 : 380} h={12} className="mb-3 mt-2" />
          <Rows n={i ? 2 : 3} label="" />
        </div>
      ))}
    </div>
  );
}
