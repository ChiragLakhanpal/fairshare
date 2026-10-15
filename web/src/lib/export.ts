// Copy, email, print (the browser's own "Save as PDF") and CSV. No library: the platform does all four.
import { copy } from "../copy";

/** A short confirmation at the bottom of the screen; App.tsx shows it for `ms` milliseconds. */
export function toast(message: string, ms = 1800): void {
  window.dispatchEvent(new CustomEvent("fairshare:toast", { detail: { message, ms } }));
}
/** Plain text always; with html too, rich targets (Mail, Teams, Slack) keep bold and lists. Says "Copied." either way. */
export async function copyText(text: string, html?: string): Promise<boolean> {
  try {
    if (html && typeof ClipboardItem !== "undefined") {
      try {
        await navigator.clipboard.write([new ClipboardItem({ "text/plain": new Blob([text], { type: "text/plain" }), "text/html": new Blob([html], { type: "text/html" }) })]);
      } catch {
        await navigator.clipboard.writeText(text);
      }
    } else await navigator.clipboard.writeText(text);
    toast(copy.copied);
    return true;
  } catch {
    toast(copy.copyFailed);
    return false;
  }
}
export function emailDraft(subject: string, body: string, to = ""): void {
  const url = `mailto:${encodeURIComponent(to)}?subject=${encodeURIComponent(subject)}&body=${encodeURIComponent(body)}`;
  window.location.href = url;
}
export function printElement(el: HTMLElement | null): void {
  if (!el) return window.print();
  // ponytail: mark the element, print the page with a print stylesheet that hides everything else
  document.querySelectorAll(".print-target").forEach((n) => n.classList.remove("print-target"));
  el.classList.add("print-target");
  document.body.classList.add("printing");
  const done = () => {
    document.body.classList.remove("printing");
    el.classList.remove("print-target");
    window.removeEventListener("afterprint", done);
  };
  window.addEventListener("afterprint", done);
  window.print();
}
export function downloadCsv(name: string, rows: Record<string, unknown>[]): void {
  if (!rows.length) return;
  const cols = Object.keys(rows[0]);
  const esc = (v: unknown) => {
    const s = v === null || v === undefined ? "" : String(v);
    return /[",\n]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s;
  };
  const csv = [cols.join(","), ...rows.map((r) => cols.map((c) => esc(r[c])).join(","))].join("\n");
  const a = document.createElement("a");
  a.href = URL.createObjectURL(new Blob([csv], { type: "text/csv" }));
  a.download = name.endsWith(".csv") ? name : `${name}.csv`;
  a.click();
  URL.revokeObjectURL(a.href);
}
