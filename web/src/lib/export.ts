// Copy, email, print (the browser's own "Save as PDF") and CSV. No library: the platform does all four.
export async function copyText(text: string): Promise<boolean> {
  try {
    await navigator.clipboard.writeText(text);
    return true;
  } catch {
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
