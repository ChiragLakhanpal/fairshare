// What an agent does, in order: the explanation when idle, the live progress while it runs.
import { copy } from "../copy";
import type { StepState } from "../lib/runs";
import type { AgentStep } from "../lib/types";
import { Check } from "./Icons";

type Props = { steps: AgentStep[]; states: StepState[]; line: string | null; fraction: number; note: string };

export function Stepper({ steps, states, line, fraction, note }: Props) {
  return (
    <div className="rounded-xl border border-line bg-white px-6 pb-4 pt-5">
      <div className="t-label mb-4">{copy.stepsLabel}</div>
      <ol className="flex items-start" aria-label={copy.stepsLabel}>
        {steps.map((s, i) => {
          const st = states[i] ?? "idle";
          return (
            <li key={s.key} className="contents">
              <div className={`flex w-[118px] shrink-0 flex-col items-center gap-2 text-center leading-[1.3] ${st === "idle" ? "text-grey" : "text-ink"}`} aria-current={st === "current" ? "step" : undefined}>
                <span className={`flex h-7 w-7 items-center justify-center rounded-full border-2 text-[12px] font-semibold ${st === "done" ? "border-blue bg-blue text-white" : st === "current" ? "border-blue bg-white" : "border-line bg-white text-ink-2"}`}>
                  {st === "done" ? <Check width={12} height={12} strokeWidth={3} /> : st === "current" ? <span className="h-2.5 w-2.5 animate-pulse rounded-full bg-blue" /> : i + 1}
                </span>
                <span className="text-[13px] font-semibold">{s.title}</span>
                <span className={`-mt-1 text-[12px] ${st === "idle" ? "text-grey" : "text-ink-2"}`}>{s.sub}</span>
              </div>
              {i < steps.length - 1 && <div className={`mt-[13px] h-0.5 min-w-3 flex-1 ${st === "done" ? "bg-blue" : "bg-line-2"}`} aria-hidden="true" />}
            </li>
          );
        })}
      </ol>
      {line ? (
        <div className="mt-4 flex items-center gap-3.5">
          <div className="h-1.5 flex-1 overflow-hidden rounded-full bg-line-2"><div className="h-1.5 rounded-full bg-blue transition-[width] duration-500" style={{ width: `${Math.round(fraction * 100)}%` }} /></div>
          <span className="whitespace-nowrap text-[13px] text-ink" role="status">{line}</span>
        </div>
      ) : (
        <p className="mt-3.5 text-[13px] text-ink-2">{note}</p>
      )}
    </div>
  );
}
