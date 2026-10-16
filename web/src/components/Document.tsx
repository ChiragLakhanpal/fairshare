// One version of a page as a document: the sections with their checked numbers underlined, the email as a card, the
// note, the page's other versions, and the approve bar that says in plain words what approving does.
import * as Dropdown from "@radix-ui/react-dropdown-menu";
import { useEffect, useRef, useState } from "react";
import { copy } from "../copy";
import { api } from "../lib/api";
import { copyText, emailDraft, printElement } from "../lib/export";
import { approvalLine, decidedLine, proseParts, versionLabel, whenLabel } from "../lib/runs";
import type { ApiError, Item, ItemEmail, PageVersion, Sentence } from "../lib/types";
import { Check, Copy, Dots, External, File as FileIcon, Info, Mail } from "./Icons";
import { SeverityChip } from "./ItemRows";
import { Num } from "./Num";
import { Table } from "./Table";

const btn = "press rounded-lg border border-line bg-white px-3 py-1.5 text-[13px] font-medium text-ink hover:border-blue hover:text-blue";
const btnOn = "press rounded-lg border border-tint-line bg-tint px-3 py-1.5 text-[13px] font-medium text-navy";
const menuItem = "flex cursor-pointer items-center gap-2.5 rounded-md px-2.5 py-2 text-sm text-ink outline-none data-[highlighted]:bg-surface";

type ProseProps = { sentences: Sentence[]; className?: string; facts: Item["facts"]; onOpen: (source: string) => void };

function Prose({ sentences, className = "", facts, onOpen }: ProseProps) {
  const shown = sentences.filter((s) => s.status !== "flagged");
  if (shown.length === 0) return null;
  return (
    <p className={`m-0 text-[15.5px] leading-[1.6] ${className}`}>
      {shown.map((s, i) => (
        <span key={i} className={s.status === "note" ? "text-ink-2" : ""}>
          {proseParts(s.text, s.numbers ?? []).map((p, j) => (typeof p === "string" ? <span key={j}>{p}</span> : <Num key={j} n={p} facts={facts} onOpen={onOpen} />))}
          {i < shown.length - 1 ? " " : ""}
        </span>
      ))}
    </p>
  );
}

/** The email's paragraphs as written (a greeting, the body, a sign-off); a page written before paragraphs were kept has one. */
function emailParagraphs(email: ItemEmail): Sentence[][] {
  return email.paragraphs?.length ? email.paragraphs : [email.sentences];
}

function emailBody(email: ItemEmail): string {
  return emailParagraphs(email).map((p) => p.filter((s) => s.status !== "flagged").map((s) => s.text).join(" ")).filter(Boolean).join("\n\n");
}

function pageText(item: Item): string {
  const sections = item.sections?.length ? item.sections : [{ title: "", sentences: item.sentences }];
  const body = sections.map((s) => [s.title, s.sentences.filter((x) => x.status !== "flagged").map((x) => x.text).join(" ")].filter(Boolean).join("\n")).join("\n\n");
  const mail = item.email ? `\n\n${copy.emailSubject}: ${item.email.subject}\n\n${emailBody(item.email)}` : "";
  return `${item.title}\n${item.subtitle}\n\n${body}${mail}`;
}

type Props = { runId: string; item: Item; versions: PageVersion[]; onOpenVersion: (v: PageVersion) => void; onChange: (i: Item) => void };

export function Document({ runId, item, versions, onOpenVersion, onChange }: Props) {
  const ref = useRef<HTMLElement>(null);
  const [open, setOpen] = useState<null | "numbers" | "queries">(null);
  const [editing, setEditing] = useState(false);
  const [text, setText] = useState(item.verified_text);
  const [busy, setBusy] = useState(false);
  const [problem, setProblem] = useState<string | null>(null);
  const [note, setNote] = useState<string | null>(null);
  useEffect(() => {
    setText(item.verified_text);
    setEditing(false);
    setProblem(null);
    setNote(null);
    setOpen(null);
  }, [item.item_id, item.verified_text]);

  const current = versions[0] ?? null;
  const mine = versions.find((v) => v.item_id === item.item_id) ?? null;
  const replaced = current && current.item_id !== item.item_id ? current : null;   // an earlier version, whatever its row says: nothing to approve
  const draft = item.status === "draft" && !replaced;
  const sections = item.sections?.length ? item.sections : [{ title: "", sentences: item.sentences }];
  const checked = item.numbers_checked ?? item.sentences.filter((s) => s.status === "verified").reduce((n, s) => n + (s.numbers?.length ?? 0), 0);
  const withRows = item.facts.filter((f) => f.rows.length);
  const withSql = item.facts.filter((f) => f.sql);
  const toggle = (k: "numbers" | "queries") => setOpen(open === k ? null : k);
  const show = (source: string) => {   // a click on a number: the rows it came from, or the source it quotes
    const target = source.startsWith("web:") ? "page-sources" : `fact-${source}`;
    if (!source.startsWith("web:")) setOpen("numbers");
    window.setTimeout(() => document.getElementById(target)?.scrollIntoView({ block: "nearest", behavior: "smooth" }), 60);
  };
  const openDraft = (it: Item) => it.email && emailDraft(it.email.subject || it.action.subject, emailBody(it.email), it.email.to);

  const approve = async () => {
    setBusy(true);
    setProblem(null);
    try {
      const edited = editing && text.trim() !== item.verified_text.trim();
      const updated = await api.approveItem(runId, item.item_id, edited ? text : undefined);
      setEditing(false);
      onChange(updated);
      if (updated.action.type === "email" && updated.email) {
        openDraft(updated);
        setNote(copy.approvedEmail);
      } else setNote(updated.action.type === "crm" ? copy.approvedCrm : copy.approvedPlain);
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
    <article ref={ref} className="flex min-h-0 min-w-0 flex-1 flex-col overflow-y-auto" aria-label={item.title}>
      <div className="mx-auto w-full max-w-[760px] px-10 pb-8 pt-7">
        {replaced && (
          <p className="mb-4 flex flex-wrap items-center gap-x-3 gap-y-1 rounded-lg border border-line bg-surface px-3.5 py-2.5 text-[13.5px]">
            <span>{copy.earlierVersionNote(whenLabel(replaced.created_at))}</span>
            <button type="button" onClick={() => onOpenVersion(replaced)} className="press font-medium text-blue hover:underline">{copy.openCurrent}</button>
          </p>
        )}
        <div className="flex items-start justify-between gap-4">
          <div className="min-w-0">
            <h1 className="t-title">{item.title}</h1>
            <div className="mt-1.5 flex items-center gap-2.5 text-[14px] text-ink-2">{item.subtitle}<SeverityChip s={item.severity} /></div>
            {mine && <div className="mt-1 text-[13px] text-ink-2">{copy.versionOf(versionLabel(mine))}</div>}
          </div>
          <div className="no-print flex shrink-0 gap-1.5">
            {withRows.length > 0 && <button type="button" className={open === "numbers" ? btnOn : btn} onClick={() => toggle("numbers")}>{open === "numbers" ? copy.hideNumbers : copy.showNumbers}</button>}
            {withSql.length > 0 && <button type="button" className={open === "queries" ? btnOn : btn} onClick={() => toggle("queries")}>{open === "queries" ? copy.hideQueries : copy.showQueries}</button>}
            <Dropdown.Root>
              <Dropdown.Trigger asChild><button type="button" aria-label={copy.moreForPage} className="press flex h-[34px] w-[34px] items-center justify-center rounded-lg border border-line bg-white text-ink-2 hover:text-ink"><Dots /></button></Dropdown.Trigger>
              <Dropdown.Portal>
                <Dropdown.Content align="end" sideOffset={6} className="z-20 min-w-[220px] rounded-lg border border-line bg-white p-1.5 shadow-xl">
                  <Dropdown.Item className={menuItem} onSelect={() => void copyText(pageText(item))}><Copy className="text-ink-2" />{copy.copyPage}</Dropdown.Item>
                  <Dropdown.Item className={menuItem} onSelect={() => printElement(ref.current)}><FileIcon className="text-ink-2" />{copy.printPage}</Dropdown.Item>
                </Dropdown.Content>
              </Dropdown.Portal>
            </Dropdown.Root>
          </div>
        </div>

        <div className="mt-4 flex items-start gap-2 text-[13.5px] leading-[1.45] text-ink-2">
          <Check className="mt-[3px] shrink-0 text-blue" width={15} height={15} strokeWidth={2.5} />
          <span>{copy.checkedLine(checked)} {item.removed.length ? copy.removedCount(item.removed.length) : copy.nothingRemoved} {checked > 0 ? copy.hoverNumber : ""}</span>
        </div>
        {item.removed.length > 0 && (
          <div className="mt-3 rounded-lg border border-[#F0C7CC] bg-red-tint px-3 py-2.5 text-[13.5px] leading-[1.5]">
            <strong className="text-red">{copy.removedCount(item.removed.length)}</strong>{" "}
            <span className="text-ink-2">{item.removed.map((r) => `It said "${r.sentence}" and ${r.reason}.`).join(" ")}</span>
          </div>
        )}

        {open === "numbers" && (
          <div className="mt-4 rounded-[10px] border border-line bg-surface px-[18px] py-4">
            {withRows.map((f) => (
              <div key={f.name} id={`fact-${f.name}`} className="mb-3 scroll-mt-4 last:mb-0">
                <div className="text-[13px] font-semibold text-ink-2">{copy.factReturned(f.label, f.rows.length)}</div>
                <Table rows={f.rows} />
              </div>
            ))}
          </div>
        )}
        {open === "queries" && (
          <div className="mt-4 rounded-[10px] border border-line bg-white px-[18px] py-4">
            {withSql.map((f) => (
              <div key={f.name} className="mb-3 last:mb-0">
                <div className="mb-2 flex items-center justify-between gap-3">
                  <span className="text-[13px] font-semibold text-ink-2">{f.label}{f.source ? ` (${f.source})` : ""}</span>
                  <button type="button" onClick={() => void copyText(f.sql ?? "")} className="press inline-flex items-center gap-1.5 text-[13px] font-medium text-blue hover:underline"><Copy width={14} height={14} />{copy.copyQuery}</button>
                </div>
                <pre className="sql">{f.sql}</pre>
              </div>
            ))}
          </div>
        )}

        {editing ? (
          <div className="mt-5">
            <textarea value={text} onChange={(e) => setText(e.target.value)} rows={14} aria-label={`Edit ${item.title}`} className="w-full rounded-lg border border-line p-3 text-[14.5px] leading-[1.55] text-ink focus:outline-none focus:ring-2 focus:ring-tint-line" />
            <p className="mt-2 text-[13px] text-ink-2">{copy.editHint}</p>
          </div>
        ) : (
          <>
            {sections.map((s, i) => (
              <section key={i} className="mt-5">
                {s.title && <h3 className="mb-1.5 text-[15px] font-semibold text-ink">{s.title}</h3>}
                <Prose sentences={s.sentences} facts={item.facts} onOpen={show} />
              </section>
            ))}
            {item.email && (
              <div className="mt-6 overflow-hidden rounded-xl border border-line">
                <div className="flex items-center justify-between gap-3 bg-surface px-4 py-2.5">
                  <span className="inline-flex items-center gap-2 text-[13px] font-semibold"><Mail width={15} height={15} />{copy.draftEmail}</span>
                  <span className="text-[12.5px] text-ink-2">{copy.emailFooter}</span>
                </div>
                <div className="px-4 py-3.5 text-[14px] leading-[1.55]">
                  <div className="grid grid-cols-[70px_minmax(0,1fr)] gap-x-2.5 gap-y-1 text-[13.5px] text-ink-2">
                    <span>{copy.emailTo}</span><span className="text-ink">{item.email.to_name || item.email.to}{item.email.to_name && item.email.to ? <span className="text-ink-2"> ({item.email.to})</span> : null}</span>
                    <span>{copy.emailSubject}</span><span className="text-ink">{item.email.subject}</span>
                  </div>
                  {emailParagraphs(item.email).map((p, k) => <Prose key={k} sentences={p} className="mt-3 !text-[14.5px]" facts={item.facts} onOpen={show} />)}
                </div>
              </div>
            )}
            {item.note && (
              <p className="mt-4 flex items-start gap-2 text-[13.5px] text-ink-2"><Info className="mt-[3px] shrink-0" width={15} height={15} /><span>{copy.notInData(item.note)}</span></p>
            )}
            {item.sources.length > 0 && (
              <div id="page-sources" className="mt-5 scroll-mt-4">
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
            {versions.length > 1 && (
              <div className="no-print mt-7">
                <div className="t-label">{copy.versionsTitle}</div>
                <ol className="mt-1.5 flex flex-col text-[13.5px] leading-[1.5]">
                  {versions.map((v) => (
                    <li key={v.item_id} className="flex items-center justify-between gap-3 border-t hairline py-2 last:border-b">
                      <span>{versionLabel(v)}<span className="text-ink-2">{`, ${v.status === "draft" ? copy.pageWaiting.toLowerCase() : decidedLine(v).replace(/\.$/, "").toLowerCase()}`}</span></span>
                      {v.item_id === item.item_id ? <span className="shrink-0 text-[12.5px] text-ink-2">{copy.thisVersion}</span>
                        : <button type="button" onClick={() => onOpenVersion(v)} className="press shrink-0 font-medium text-blue hover:underline">{copy.open}</button>}
                    </li>
                  ))}
                </ol>
              </div>
            )}
          </>
        )}
      </div>

      <div className="no-print sticky bottom-0 mt-auto border-t hairline bg-white/95 py-3.5 backdrop-blur">
        <div className="mx-auto w-full max-w-[760px] px-10">
          <div className="flex flex-wrap items-center gap-2.5">
            {draft && <button type="button" onClick={() => void approve()} disabled={busy} className="press rounded-lg bg-blue px-4 py-2 text-[14px] font-semibold text-white hover:bg-navy disabled:opacity-60">{copy.approveItem}</button>}
            {draft && <button type="button" onClick={() => setEditing((e) => !e)} disabled={busy} className="press rounded-lg border border-line bg-white px-3.5 py-2 text-[14px] font-semibold text-ink hover:border-blue hover:text-blue">{editing ? copy.doneEditing : copy.editItem}</button>}
            {draft && <button type="button" onClick={() => void reject()} disabled={busy} className="press rounded-lg border border-line bg-white px-3.5 py-2 text-[14px] font-semibold text-ink hover:border-blue hover:text-blue">{copy.rejectItem}</button>}
            {item.status === "approved" && item.email && <button type="button" onClick={() => openDraft(item)} className="press inline-flex items-center gap-1.5 rounded-lg border border-line bg-white px-3.5 py-2 text-[14px] font-semibold text-ink hover:border-blue hover:text-blue"><Mail width={15} height={15} />{copy.openDraft}</button>}
            <span className="text-[13px] text-ink-2">{draft ? approvalLine(item.action) : replaced ? copy.replacedLine(whenLabel(replaced.created_at)) : `${decidedLine(item)}${note ? ` ${note}` : ""}`}</span>
          </div>
          {problem && <p className="mt-2 text-[13.5px] text-red">{problem}</p>}
        </div>
      </div>
    </article>
  );
}
