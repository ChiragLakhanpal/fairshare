import * as Dropdown from "@radix-ui/react-dropdown-menu";
import { useRef, useState } from "react";
import { copy } from "../copy";
import { api } from "../lib/api";
import { copyText, emailDraft, printElement } from "../lib/export";
import { monthLabel } from "../lib/format";
import type { Brief as BriefT } from "../lib/types";
import { Check, ChevronDown, Copy, File as FileIcon, Link, Mail } from "./Icons";

const item = "flex cursor-pointer items-center gap-2.5 rounded-md px-2.5 py-2 text-sm text-ink outline-none data-[highlighted]:bg-surface data-[disabled]:opacity-50";

export function Brief({ brief, onApproved }: { brief: BriefT; onApproved: (b: BriefT) => void }) {
  const ref = useRef<HTMLDivElement>(null);
  const [editing, setEditing] = useState(false);
  const [text, setText] = useState(brief.verified_text);
  const [busy, setBusy] = useState(false);
  const scope = `${brief.region === "All" ? "all regions" : `the ${brief.region} region`}, ${monthLabel(brief.month)}`;
  const subject = `Monday brief: ${brief.region === "All" ? "all regions" : brief.region}, ${monthLabel(brief.month)}`;
  const link = `${location.origin}/brief/${brief.run_id}`;
  const approved = brief.status === "approved";
  const approve = async () => {
    setBusy(true);
    try {
      await api.approveBrief(brief.run_id);
      onApproved({ ...brief, status: "approved" });
      emailDraft(subject, text);
    } finally {
      setBusy(false);
    }
  };
  const verified = brief.sentences.filter((s) => s.status === "verified");
  return (
    <div ref={ref} className="print-section">
      <p className="mb-2 text-ink-2">{copy.briefIntro(scope)}</p>
      {editing ? (
        <textarea value={text} onChange={(e) => setText(e.target.value)} rows={8} className="w-full rounded-lg border border-line p-3 text-[14.5px] leading-[1.5] text-ink focus:outline-none focus:ring-2 focus:ring-tint-line" />
      ) : (
        <div>
          {verified.map((s, i) => (
            <div key={i} className="grid grid-cols-[20px_minmax(0,1fr)] gap-2.5 py-[5px] text-[14.5px] leading-[1.5]">
              <span className="mt-1 flex h-4 w-4 items-center justify-center rounded-full bg-tint text-navy"><Check width={10} height={10} strokeWidth={3} /></span>
              <span>{s.text}</span>
            </div>
          ))}
          {brief.sentences.filter((s) => s.status === "note").map((s, i) => (
            <div key={`n${i}`} className="grid grid-cols-[20px_minmax(0,1fr)] gap-2.5 py-[5px] text-[14.5px] leading-[1.5]"><span /><span className="text-ink-2">{s.text}</span></div>
          ))}
        </div>
      )}
      {brief.removed.length > 0 && (
        <div className="mt-2.5 rounded-lg border border-[#F0C7CC] bg-red-tint px-3 py-2.5 text-[13.5px] leading-[1.5]">
          <strong className="text-red">{brief.removed.length === 1 ? "I removed one sentence before sending." : `I removed ${brief.removed.length} sentences before sending.`}</strong>{" "}
          <span className="text-ink-2">{brief.removed.map((r) => `It said "${r.sentence}" and ${r.reason}.`).join(" ")}</span>
        </div>
      )}
      <div className="no-print mt-3.5 flex flex-wrap items-center gap-2.5">
        {!approved && <button type="button" onClick={() => void approve()} disabled={busy} className="press rounded-lg bg-blue px-3.5 py-2 text-sm font-semibold text-white hover:bg-navy disabled:opacity-60">{copy.approve}</button>}
        {!approved && <button type="button" onClick={() => setEditing((e) => !e)} className="press rounded-lg border border-line bg-white px-3.5 py-2 text-sm font-semibold text-ink hover:border-blue hover:text-blue">{editing ? "Done editing" : copy.edit}</button>}
        <Dropdown.Root>
          <Dropdown.Trigger asChild><button type="button" className="press inline-flex items-center gap-1.5 rounded-lg border border-line bg-surface px-3.5 py-2 text-sm font-semibold text-ink hover:border-blue">{copy.export}<ChevronDown width={14} height={14} /></button></Dropdown.Trigger>
          <Dropdown.Portal>
            <Dropdown.Content align="start" sideOffset={6} className="z-20 min-w-[240px] rounded-lg border border-line bg-white p-1.5 shadow-xl">
              <Dropdown.Item className={item} onSelect={() => void copyText(text)}><Copy className="text-ink-2" />{copy.exportCopy}</Dropdown.Item>
              <Dropdown.Item className={item} onSelect={() => emailDraft(subject, text)}><Mail className="text-ink-2" />{copy.exportEmail}</Dropdown.Item>
              <Dropdown.Item className={item} onSelect={() => printElement(ref.current)}><FileIcon className="text-ink-2" />{copy.exportPdf}</Dropdown.Item>
              <Dropdown.Item className={item} disabled={!approved} onSelect={() => void copyText(link)}><Link className="text-ink-2" />{approved ? copy.exportLink : copy.exportLinkLater}</Dropdown.Item>
            </Dropdown.Content>
          </Dropdown.Portal>
        </Dropdown.Root>
      </div>
      <p className="mt-2.5 text-[13px] text-ink-2">{approved ? <>{copy.approved} <a href={link}>{link}</a></> : copy.approveNote}</p>
    </div>
  );
}
