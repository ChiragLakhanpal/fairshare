import { useEffect, useState } from "react";
import { copy } from "../copy";
import { api } from "../lib/api";
import type { Brief as BriefT } from "../lib/types";
import { Brief } from "./Brief";

export function BriefPage({ runId }: { runId: string }) {
  const [brief, setBrief] = useState<BriefT | null>(null);
  const [error, setError] = useState<string | null>(null);
  useEffect(() => {
    api.getBrief(runId).then(setBrief).catch((e) => setError(e.message ?? "No brief with that id."));
  }, [runId]);
  return (
    <div className="mx-auto max-w-[760px] px-6 py-10">
      <div className="mb-8 flex items-center gap-2.5">
        <span className="flex h-[30px] w-[30px] items-center justify-center rounded border border-dashed border-grey text-[9px] text-ink-2" aria-label="Logo placeholder">logo</span>
        <span className="leading-tight"><span className="block text-sm font-semibold text-navy">{copy.brand}</span><span className="block text-xs text-ink-2">{copy.product}</span></span>
        <a href="/" className="ml-auto text-[13.5px]">Open the app</a>
      </div>
      {error ? <p className="text-ink-2">{error}</p> : brief ? <Brief brief={brief} onApproved={setBrief} /> : <p className="text-ink-2">Loading the brief.</p>}
    </div>
  );
}
