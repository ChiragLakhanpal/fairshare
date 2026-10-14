import { forwardRef, useEffect, useState, type FormEvent } from "react";
import { copy } from "../copy";
import { ArrowUp, Stop } from "./Icons";

type Props = { busy: boolean; showChips: boolean; onSend: (q: string) => void; onStop: () => void; onHow: () => void; followUp: boolean; prefill?: { text: string; n: number } };

export const FloatingBar = forwardRef<HTMLInputElement, Props>(function FloatingBar({ busy, showChips, onSend, onStop, onHow, followUp, prefill }, ref) {
  const [value, setValue] = useState("");
  useEffect(() => {
    if (prefill?.text) setValue(prefill.text);
  }, [prefill]);
  const submit = (e: FormEvent) => {
    e.preventDefault();
    if (busy) return onStop();
    const q = value.trim();
    if (!q) return;
    onSend(q);
    setValue("");
  };
  return (
    <div className="no-print sticky bottom-0 z-10 px-6 pb-[18px] pt-7" style={{ background: "linear-gradient(to top, #fff 55%, rgba(255,255,255,0))" }}>
      <div className="mx-auto max-w-[760px]">
        {showChips && (
          <div className="mb-3">
            <p className="mb-0.5 text-[13px] text-ink-2">{copy.tryThese}</p>
            <div className="flex flex-wrap gap-2">
              {copy.chips.map((c) => (
                <button key={c} type="button" onClick={() => onSend(c)} className="press rounded-lg border border-line bg-white px-3 py-[7px] text-left text-[13.5px] font-medium text-ink hover:border-blue hover:text-blue">{c}</button>
              ))}
            </div>
          </div>
        )}
        <form onSubmit={submit} className="floating flex items-center gap-2.5 rounded-[14px] py-[9px] pl-[18px] pr-[9px]">
          <label className="sr-only" htmlFor="ask">Ask a question</label>
          <input id="ask" ref={ref} value={value} onChange={(e) => setValue(e.target.value)} placeholder={followUp ? copy.placeholderFollowUp : copy.placeholder}
            className="min-w-0 flex-1 bg-transparent text-base text-ink outline-none placeholder:text-ink-2" autoComplete="off" />
          <button type="submit" aria-label={busy ? copy.stop : copy.send} className={`press flex h-[38px] w-[38px] shrink-0 items-center justify-center rounded-[10px] text-white ${busy ? "bg-ink" : "bg-blue hover:bg-navy"}`}>
            {busy ? <Stop width={14} height={14} /> : <ArrowUp width={18} height={18} strokeWidth={2.2} />}
          </button>
        </form>
        <div className="mt-2.5 text-center text-[12.5px] text-ink-2">{copy.footer} <button type="button" onClick={onHow} className="text-blue hover:underline">{copy.footerLink}</button></div>
      </div>
    </div>
  );
});
