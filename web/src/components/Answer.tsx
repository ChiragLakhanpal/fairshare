import * as Dropdown from "@radix-ui/react-dropdown-menu";
import * as Popover from "@radix-ui/react-popover";
import { useRef, useState } from "react";
import { copy } from "../copy";
import { copyText, downloadCsv, emailDraft, printElement } from "../lib/export";
import { money, pct } from "../lib/format";
import { answerBody, answerHtml, answerText, shownSentences, trustLine } from "../lib/share";
import type { Answer as AnswerT, Call } from "../lib/types";
import { Check, Chart, Close, Copy, Dots, File as FileIcon, Info, Mail } from "./Icons";
import { Table } from "./Table";

const btn = "press rounded-lg border border-line bg-white px-3 py-1.5 text-[13px] font-medium text-ink hover:border-blue hover:text-blue";
const btnOn = "press rounded-lg border border-tint-line bg-tint px-3 py-1.5 text-[13px] font-medium text-navy";
const item = "flex cursor-pointer items-center gap-2.5 rounded-md px-2.5 py-2 text-sm text-ink outline-none data-[highlighted]:bg-surface";

function Breakdown({ call, markets }: { call: Call; markets?: Call }) {
  const s = call.preview[0] as Record<string, number> | undefined;
  if (!s) return null;
  const total = Math.abs(s.delta_revenue) || 1;
  const parts = [["Volume", s.volume_effect], ["Mix", s.mix_effect], ["Share", s.share_effect]] as [string, number][];
  const scale = Math.max(...parts.map(([, v]) => Math.abs(v)), total) || 1;
  const fair = s.fair_share_now_pct - s.fair_share_prior_pct;
  return (
    <div className="mt-3 rounded-[10px] border border-line bg-white px-[18px] py-4">
      <h4 className="mb-2.5 text-sm font-semibold">Here is where the {money(Math.abs(s.delta_revenue), 1)} went.</h4>
      {parts.map(([name, v]) => (
        <div key={name} className="grid grid-cols-[70px_minmax(0,1fr)_72px] items-center gap-3 py-1 text-[13.5px]">
          <span>{name}</span>
          <div className="relative h-3 rounded-sm bg-surface">
            <div className="absolute top-0 h-3 rounded-sm" style={{ left: v < 0 ? `${50 - (Math.abs(v) / scale) * 50}%` : "50%", width: `${(Math.abs(v) / scale) * 50}%`, background: name === "Mix" ? "#9DA6AB" : v < 0 ? "#C30019" : "#0078D2" }} />
          </div>
          <span className="text-right font-semibold" style={{ color: name === "Mix" ? "#627A88" : v < 0 ? "#C30019" : "#0078D2" }}>{v < 0 ? "−" : "+"}{money(Math.abs(v), 1).replace("$", "$")}</span>
        </div>
      ))}
      <p className="mt-2.5 text-[13.5px] text-ink-2">
        Volume, mix and share add up to the full change of {money(Math.abs(s.delta_revenue), 1)}. {Math.abs(fair) < 0.05 ? "Fair share did not move, so AA's own capacity explains none of it." : `Fair share moved ${fair > 0 ? "up" : "down"} ${Math.abs(fair).toFixed(1)} points, worth ${money(s.fair_share_effect)}.`}
      </p>
      {markets && markets.preview.length > 0 && (
        <Table rows={markets.preview.slice(0, 5).map((m) => ({ market: m.market, "AA share, before": pct(m.aa_share_prior_pct as number), "AA share, now": pct(m.aa_share_now_pct as number), "share effect": money(m.share_effect as number) }))} />
      )}
    </div>
  );
}

export function Answer({ a, onFollowUp, onHow }: { a: AnswerT; onFollowUp: (q: string) => void; onHow: () => void }) {
  const ref = useRef<HTMLDivElement>(null);
  const explain = a.calls.find((c) => c.tool === "explain_change" && c.preview.length);
  const explainMarkets = a.calls.filter((c) => c.tool === "explain_change").at(1);
  const [open, setOpen] = useState<null | "numbers" | "query" | "breakdown">(explain ? "breakdown" : null);
  const toggle = (k: "numbers" | "query" | "breakdown") => setOpen(open === k ? null : k);
  const shown = shownSentences(a);
  const nums = shown.reduce((n, s) => n + (s.numbers?.length ?? 0), 0);
  const withSql = a.calls.filter((c) => c.sql);
  const withRows = a.calls.filter((c) => c.preview.length);
  const genie = a.calls.find((c) => c.genie)?.genie;
  const refusal = a.kind === "refusal" || a.kind === "general" || a.kind === "meta";
  const nothingToShow = shown.length === 0 && a.removed.length > 0;
  return (
    <div ref={ref} className="print-section">
      <div className="text-[15.5px] leading-[1.6]">{answerBody(a)}</div>
      {a.cached && <p className="mt-2 text-[13px] text-ink-2">{copy.cached(a.cached.recorded)}</p>}
      <div className="mt-2.5 flex items-start gap-1.5 text-[13.5px] leading-[1.45] text-ink-2">
        {refusal ? <Info className="mt-[3px] shrink-0" width={15} height={15} /> : <Check className="mt-[3px] shrink-0 text-blue" width={15} height={15} strokeWidth={2.5} />}
        <span>
          {trustLine(a)}{" "}
          <Popover.Root>
            <Popover.Trigger asChild><button type="button" className="border-b border-dotted border-grey text-ink-2 hover:text-ink">{copy.howChecked}</button></Popover.Trigger>
            <Popover.Portal>
              <Popover.Content side="bottom" align="start" sideOffset={8} className="z-30 w-[420px] max-w-[92vw] rounded-[10px] border border-line bg-white px-4 py-3.5 text-[13.5px] leading-[1.5] shadow-xl">
                <div className="flex items-baseline justify-between gap-3"><span className="text-[15px] font-semibold">How this answer was checked</span><Popover.Close aria-label="Close" className="text-ink-2 hover:text-ink"><Close /></Popover.Close></div>
                <p className="mt-1.5 text-ink">The agent can only state numbers it received from a query. Before you saw this answer, a checker compared each of its {nums} numbers with the query results, at the same rounding. If a sentence had carried a number no query returned, the checker would have removed it and told you.</p>
                <p className="mt-2 text-[12.5px] text-ink-2">{copy.howScoresLine} <button type="button" className="text-blue hover:underline" onClick={onHow}>See how this app gets an answer.</button></p>
                <div className="mt-2.5 flex gap-3.5 text-[13px]">{a.trace_url && <a href={a.trace_url} target="_blank" rel="noreferrer">{copy.openTrace}</a>}{genie && <a href={genie.url} target="_blank" rel="noreferrer">{copy.openGenie}</a>}</div>
              </Popover.Content>
            </Popover.Portal>
          </Popover.Root>
        </span>
      </div>
      {a.could_not_verify.map((c, i) => (
        <div key={i} className="mt-1 flex items-start gap-1.5 text-[13.5px] leading-[1.45] text-ink-2"><Info className="mt-[3px] shrink-0" width={15} height={15} /><span>{c.replace(/^Could not verify:?\s*/i, "I could not verify ").replace(/^I could not verify ([a-z])/, (m, ch) => `I could not verify ${ch}`)}</span></div>
      ))}
      {a.removed.length > 0 && (
        <div className="mt-2.5 rounded-lg border border-[#F0C7CC] bg-red-tint px-3 py-2.5 text-[13.5px] leading-[1.5]">
          <strong className="text-red">{copy.removedSome(a.removed.length)}</strong>{" "}
          <span className="text-ink-2">{a.removed.map((r) => `It said "${r.sentence}" and ${r.reason}.`).join(" ")}</span>
        </div>
      )}
      <div className="no-print mt-3 flex flex-wrap items-center gap-2">
        {explain && <button type="button" className={open === "breakdown" ? btnOn : btn} onClick={() => toggle("breakdown")}>{open === "breakdown" ? copy.hideBreakdown : copy.showBreakdown}</button>}
        {withRows.length > 0 && !explain && <button type="button" className={open === "numbers" ? btnOn : btn} onClick={() => toggle("numbers")}>{open === "numbers" ? copy.hideNumbers : copy.showNumbers}</button>}
        {withSql.length > 0 && <button type="button" className={open === "query" ? btnOn : btn} onClick={() => toggle("query")}>{open === "query" ? copy.hideQuery : copy.showQuery}</button>}
        {genie && <a href={genie.url} target="_blank" rel="noreferrer" className={btn}>{copy.openGenie}</a>}
        <Dropdown.Root>
          <Dropdown.Trigger asChild><button type="button" aria-label={copy.more} className="press rounded-lg px-2 py-1.5 text-ink-2 hover:bg-surface hover:text-ink"><Dots /></button></Dropdown.Trigger>
          <Dropdown.Portal>
            <Dropdown.Content align="start" sideOffset={6} className="z-20 min-w-[230px] rounded-lg border border-line bg-white p-1.5 shadow-xl">
              <Dropdown.Item className={item} onSelect={() => void copyText(answerText(a), answerHtml(a))}><Copy className="text-ink-2" />{copy.copyAnswer}</Dropdown.Item>
              <Dropdown.Item className={item} onSelect={() => emailDraft(a.question, `${answerBody(a)}\n\n${trustLine(a)}`)}><Mail className="text-ink-2" />{copy.emailAnswer}</Dropdown.Item>
              <Dropdown.Item className={item} onSelect={() => printElement(ref.current)}><FileIcon className="text-ink-2" />{copy.pdfAnswer}</Dropdown.Item>
              {withRows.length > 0 && <Dropdown.Item className={item} onSelect={() => downloadCsv("fairshare-answer", withRows[0].preview)}><Chart className="text-ink-2" />{copy.csv}</Dropdown.Item>}
            </Dropdown.Content>
          </Dropdown.Portal>
        </Dropdown.Root>
      </div>
      {open === "breakdown" && explain && <Breakdown call={explain} markets={explainMarkets} />}
      {open === "numbers" && (
        <div className="mt-3 rounded-[10px] border border-line bg-white px-[18px] py-4">
          {withRows.map((c) => (
            <div key={c.i} className="mb-3 last:mb-0">
              <div className="text-[13px] font-semibold text-ink-2">{c.tool === "ask_metrics" ? "Genie" : c.tool === "run_sql" ? "The query" : c.tool} returned {c.rows ?? c.preview.length} {c.rows === 1 ? "row" : "rows"}.</div>
              <Table rows={c.preview} />
            </div>
          ))}
        </div>
      )}
      {open === "query" && (
        <div className="mt-3 rounded-[10px] border border-line bg-white px-[18px] py-4">
          {withSql.map((c) => (
            <div key={c.i} className="mb-3 last:mb-0">
              <div className="mb-2 flex flex-wrap items-baseline justify-between gap-3">
                <h4 className="text-sm font-semibold">{c.tool === "ask_metrics" ? `Genie wrote this query against the sales metrics view${c.ms ? ` and answered in ${Math.round(c.ms / 1000)} seconds` : ""}.` : c.tool === "run_sql" ? "The agent ran this query." : `${c.tool} used ${c.sql}.`}</h4>
                {c.genie && <a href={c.genie.url} target="_blank" rel="noreferrer" className="text-[13px]">{copy.openGenie}</a>}
              </div>
              {c.tool !== "explain_change" && <pre className="sql">{c.sql}</pre>}
              {c.preview.length > 0 && <Table rows={c.preview} />}
            </div>
          ))}
        </div>
      )}
      {a.follow_ups.length > 0 && (
        <div className="no-print mt-3.5 flex flex-wrap gap-2">
          {a.follow_ups.map((f) => <button key={f} type="button" onClick={() => onFollowUp(f)} className="press rounded-lg border border-line bg-white px-3 py-[7px] text-left text-[13.5px] font-medium text-ink hover:border-blue hover:text-blue">{f}</button>)}
        </div>
      )}
    </div>
  );
}
