// A checked number in the prose: the same hover as a KPI word (one plain sentence: what it is and where it came from),
// and a click shows the rows it came from, or the source it quotes. A span, not a button: a button is an unbreakable box,
// so the period after it would wrap onto its own line.
import * as Tooltip from "@radix-ui/react-tooltip";
import { numberHint, type HintFact } from "../lib/runs";

type N = { raw: string; source: string | null; fact: string | null };

export function Num({ n, facts, onOpen }: { n: N; facts: HintFact[]; onOpen?: (source: string) => void }) {
  const hint = numberHint(n, facts);
  if (!hint) return <span>{n.raw}</span>;
  return (
    <Tooltip.Root delayDuration={150}>
      <Tooltip.Trigger asChild>
        <span role="button" tabIndex={0} className="num" onClick={() => n.source && onOpen?.(n.source)}
          onKeyDown={(e) => { if ((e.key === "Enter" || e.key === " ") && n.source) { e.preventDefault(); onOpen?.(n.source); } }}>{n.raw}</span>
      </Tooltip.Trigger>
      <Tooltip.Portal>
        <Tooltip.Content side="bottom" align="start" sideOffset={6} className="z-30 max-w-[320px] rounded-md bg-ink px-3 py-2 text-[13px] leading-snug text-white shadow-lg">{hint}</Tooltip.Content>
      </Tooltip.Portal>
    </Tooltip.Root>
  );
}
