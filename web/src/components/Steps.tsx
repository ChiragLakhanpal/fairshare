import { copy } from "../copy";
import type { Step } from "../lib/types";
import { Check } from "./Icons";

const LABEL: Record<string, string> = {
  model: "I am writing the answer.",
  warehouse: "I am waking up the warehouse.",
  genie: "I am asking Genie for the numbers.",
  sql: "I am running a query on your data.",
  explain: "I am working out what moved.",
  agreement: "I am reading the agreement.",
  verify: "I am checking every number against the query.",
};

export function Steps({ steps }: { steps: Step[] }) {
  // the latest status is the current step; everything before it is done
  const shown = steps.filter((s, i) => i === steps.length - 1 || s.phase !== "model");
  return (
    <div>
      <div className="flex flex-col gap-3">
        {shown.map((s, i) => {
          const current = i === shown.length - 1;
          return (
            <div key={i} className="flex items-start gap-2.5 text-[15px] leading-[1.45]">
              {current ? (
                <span className="mt-0.5 flex h-5 w-5 shrink-0 items-center justify-center rounded-full border-2 border-blue"><span className="h-2 w-2 animate-pulse rounded-full bg-blue" /></span>
              ) : (
                <span className="mt-0.5 flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-tint text-navy"><Check width={11} height={11} strokeWidth={3} /></span>
              )}
              <span className={current ? "" : "text-ink-2"}>{s.text || LABEL[s.phase] || s.phase}{s.genie && current ? <> <a href={s.genie.url} target="_blank" rel="noreferrer" className="text-[13px]">Open in Genie</a></> : null}</span>
            </div>
          );
        })}
      </div>
      <p className="mt-3 text-[13.5px] text-ink-2">{copy.waitHint}</p>
    </div>
  );
}
