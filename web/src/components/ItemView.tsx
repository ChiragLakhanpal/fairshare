import { useState } from "react";
import { copy } from "../copy";
import { api } from "../lib/api";
import { emailDraft } from "../lib/export";
import { decidedLine } from "../lib/runs";
import type { ApiError, Item } from "../lib/types";
import { Check, External } from "./Icons";
import { Table } from "./Table";

const btn = "press rounded-lg border border-line bg-white px-3 py-1.5 text-[13px] font-medium text-ink hover:border-blue hover:text-blue";
const btnOn = "press rounded-lg border border-tint-line bg-tint px-3 py-1.5 text-[13px] font-medium text-navy";

function Severity({ s }: { s: Item["severity"] }) {
  if (!s) return null;
  const look = s === "risk" ? "border-[#F0C7CC] bg-red-tint text-red" : s === "watch" ? "border-line bg-surface text-ink-2" : "border-tint-line bg-tint text-navy";
  return <span className={`shrink-0 rounded-full border px-2 py-0.5 text-[11px] font-semibold uppercase tracking-wide ${look}`}>{copy.severity[s]}</span>;
}

export function ItemView({ runId, item, crmLabel, onChange }: { runId: string; item: Item; crmLabel: string; onChange: (i: Item) => void }) {
  const [open, setOpen] = useState<null | "numbers" | "query">(null);
  const [editing, setEditing] = useState(false);
  const [text, setText] = useState(item.verified_text);
  const [busy, setBusy] = useState(false);
  const [problem, setProblem] = useState<string | null>(null);
  const [note, setNote] = useState<string | null>(null);
  const draft = item.status === "draft";
  const shown = item.sentences.filter((s) => s.status !== "flagged");
  const withRows = item.facts.filter((f) => f.rows.length);
  const withSql = item.facts.filter((f) => f.sql);
  const toggle = (k: "numbers" | "query") => setOpen(open === k ? null : k);

  const approve = async () => {
    setBusy(true);
    setProblem(null);
    try {
      const edited = editing && text.trim() !== item.verified_text.trim();
      const updated = await api.approveItem(runId, item.item_id, edited ? text : undefined);
      setEditing(false);
      setText(updated.verified_text);
      onChange(updated);
      if (updated.action.type === "email") {
        emailDraft(updated.action.subject, updated.action.body);
        setNote(copy.approvedEmail);
      } else setNote(updated.action.type === "crm" ? copy.approvedCrm(crmLabel) : copy.approvedPlain);
    } catch (e) {
      const err = e as ApiError & { removed?: { sentence: string; reason: string }[] };
      const removed = err.removed?.map((r) => `"${r.sentence}" (${r.reason})`).join("; ");
      setProblem(err.code === "unverified" ? `${err.message} ${removed ?? ""}`.trim() : `${copy.errorGeneric} (${err.message ?? ""})`.trim());
    } finally {
      setBusy(false);
    }
  };
  const reject = async () => {
    setBusy(true);
    setProblem(null);
    try {
      const updated = await api.rejectItem(runId, item.item_id);
      setEditing(false);
      onChange(updated);
      setNote(copy.rejectedItem);
    } catch (e) {
      setProblem(`${copy.errorGeneric} (${(e as ApiError).message ?? ""})`.trim());
    } finally {
      setBusy(false);
    }
  };

  return (
    <article className="rounded-xl border border-line bg-white px-5 py-4" aria-label={item.title}>
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <h4 className="text-[15.5px] font-semibold text-ink">{item.title}</h4>
          {item.subtitle && <p className="mt-0.5 text-[13.5px] text-ink-2">{item.subtitle}</p>}
        </div>
        <Severity s={item.severity} />
      </div>

      {editing ? (
        <textarea value={text} onChange={(e) => setText(e.target.value)} rows={8} aria-label={`Edit ${item.title}`} className="mt-3 w-full rounded-lg border border-line p-3 text-[14.5px] leading-[1.5] text-ink focus:outline-none focus:ring-2 focus:ring-tint-line" />
      ) : (
        <div className="mt-3">
          {shown.length === 0 && item.verified_text && <p className="text-[14.5px] leading-[1.5]">{item.verified_text}</p>}
          {shown.length === 0 && !item.verified_text && item.removed.length > 0 && <p className="text-[14.5px] leading-[1.5] text-ink-2">{copy.allRemoved}</p>}
          {shown.map((s, i) => (
            <div key={i} className="grid grid-cols-[20px_minmax(0,1fr)] gap-2.5 py-[4px] text-[14.5px] leading-[1.5]">
              {s.status === "verified" ? <span className="mt-1 flex h-4 w-4 items-center justify-center rounded-full bg-tint text-navy"><Check width={10} height={10} strokeWidth={3} /></span> : <span />}
              <span className={s.status === "note" ? "text-ink-2" : ""}>{s.text}</span>
            </div>
          ))}
        </div>
      )}
      {item.removed.length > 0 && (
        <div className="mt-2.5 rounded-lg border border-[#F0C7CC] bg-red-tint px-3 py-2.5 text-[13.5px] leading-[1.5]">
          <strong className="text-red">{copy.itemRemoved(item.removed.length)}</strong>{" "}
          <span className="text-ink-2">{item.removed.map((r) => `It said "${r.sentence}" and ${r.reason}.`).join(" ")}</span>
        </div>
      )}

      {item.sources.length > 0 && (
        <div className="mt-3">
          <div className="t-label">{copy.sourcesTitle}</div>
          <ol className="mt-1.5 flex flex-col gap-1.5 text-[13.5px] leading-[1.5]">
            {item.sources.map((s, i) => (
              <li key={s.url} className="grid grid-cols-[28px_minmax(0,1fr)] gap-1">
                <span className="text-ink-2">[{i + 1}]</span>
                <span>
                  <a href={s.url} target="_blank" rel="noreferrer" className="inline-flex items-center gap-1 font-medium">{s.title}<External width={12} height={12} /></a>
                  {s.published && <span className="text-ink-2"> ({s.published})</span>}
                  {s.snippet && <span className="block text-ink-2">"{s.snippet}"</span>}
                </span>
              </li>
            ))}
          </ol>
        </div>
      )}

      <div className="no-print mt-3.5 flex flex-wrap items-center gap-2">
        {draft && <button type="button" onClick={() => void approve()} disabled={busy} className="press rounded-lg bg-blue px-3.5 py-1.5 text-[13px] font-semibold text-white hover:bg-navy disabled:opacity-60">{copy.approveItem}</button>}
        {draft && <button type="button" onClick={() => setEditing((e) => !e)} disabled={busy} className={btn}>{editing ? copy.doneEditing : copy.editItem}</button>}
        {draft && <button type="button" onClick={() => void reject()} disabled={busy} className={btn}>{copy.rejectItem}</button>}
        {withRows.length > 0 && <button type="button" className={open === "numbers" ? btnOn : btn} onClick={() => toggle("numbers")}>{open === "numbers" ? copy.hideNumbers : copy.showNumbers}</button>}
        {withSql.length > 0 && <button type="button" className={open === "query" ? btnOn : btn} onClick={() => toggle("query")}>{open === "query" ? copy.hideQuery : copy.showQuery}</button>}
      </div>
      {problem && <p className="mt-2.5 text-[13.5px] text-red">{problem}</p>}
      <p className="mt-2.5 text-[13px] text-ink-2">{draft ? copy.approveNoteItem(item.action.type, crmLabel) : <>{decidedLine(item)}{note ? ` ${note}` : ""}</>}</p>

      {open === "numbers" && (
        <div className="mt-3 rounded-[10px] border border-line bg-surface px-[18px] py-4">
          {withRows.map((f) => (
            <div key={f.name} className="mb-3 last:mb-0">
              <div className="text-[13px] font-semibold text-ink-2">{copy.factReturned(f.label, f.rows.length)}</div>
              <Table rows={f.rows} />
            </div>
          ))}
        </div>
      )}
      {open === "query" && (
        <div className="mt-3 rounded-[10px] border border-line bg-white px-[18px] py-4">
          {withSql.map((f) => (
            <div key={f.name} className="mb-3 last:mb-0">
              <div className="mb-2 text-[13px] font-semibold text-ink-2">{f.label}{f.source ? ` (${f.source})` : ""}</div>
              <pre className="sql">{f.sql}</pre>
            </div>
          ))}
        </div>
      )}
    </article>
  );
}
