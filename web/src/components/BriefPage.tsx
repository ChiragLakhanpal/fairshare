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
      <div className="mb-8 flex items-end gap-3">
        <img src="/aa-logo.svg" alt={copy.brand} className="h-auto w-[170px]" />
        <span className="text-[13px] font-semibold tracking-tight text-navy">{copy.product}</span>
        <a href="/" className="ml-auto text-[13.5px]">Open the app</a>
      </div>
      {error ? <p className="text-ink-2">{error}</p> : brief ? <Brief brief={brief} onApproved={setBrief} /> : <p className="text-ink-2">Loading the brief.</p>}
    </div>
  );
}
