// One "worth knowing" line: the sentence with its checked numbers (hover says what and where from, a click opens the rows
// under it) and one action. Used as the rows of the home page block and as the related line under an Ask answer.
import { useState } from "react";
import { proseParts, type HintFact } from "../lib/runs";
import type { Signal, SignalAction } from "../lib/types";
import { Num } from "./Num";
import { Table } from "./Table";

export function SignalLine({ s, facts, onAction, lead }: { s: Signal; facts: HintFact[]; onAction: (a: SignalAction) => void; lead?: string }) {
  const [open, setOpen] = useState<string | null>(null);
  const fact = open ? facts.find((f) => f.name === open) : undefined;
  return (
    <div className="min-w-0">
      <span>
        {lead && <span className="text-ink-2">{lead} </span>}
        {proseParts(s.sentence.text, s.sentence.numbers ?? []).map((p, j) => (typeof p === "string" ? <span key={j}>{p}</span> : <Num key={j} n={p} facts={facts} onOpen={(src) => setOpen(open === src ? null : src)} />))}
      </span>{" "}
      <button type="button" className="no-print whitespace-nowrap text-blue hover:underline" onClick={() => onAction(s.action)}>{s.action.label}</button>
      {fact && (
        <div className="mt-2.5 rounded-[10px] border border-line bg-white px-4 py-3">
          <div className="text-[13px] font-semibold text-ink-2">{fact.label}: {fact.rows.length} {fact.rows.length === 1 ? "row" : "rows"}{fact.source ? `, read from ${fact.source}` : ""}.</div>
          <Table rows={fact.rows} />
        </div>
      )}
    </div>
  );
}
