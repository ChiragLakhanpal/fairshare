// A plain table for query results: numbers right-aligned with thousands separators, at most fifty rows.
export function Table({ rows }: { rows: Record<string, unknown>[] }) {
  if (!rows.length) return <p className="text-[13px] text-ink-2">The query returned no rows.</p>;
  const cols = Object.keys(rows[0]);
  const num = (v: unknown) => typeof v === "number";
  return (
    <div className="overflow-x-auto">
      <table className="mt-2.5 w-full border-collapse text-[13px]">
        <thead><tr>{cols.map((c) => <th key={c} className={`border-b border-line px-2 py-1.5 font-semibold text-ink-2 ${num(rows[0][c]) ? "text-right" : "text-left"}`}>{c}</th>)}</tr></thead>
        <tbody>
          {rows.slice(0, 50).map((r, i) => (
            <tr key={i}>{cols.map((c) => <td key={c} className={`border-b hairline px-2 py-1.5 tabular-nums ${num(r[c]) ? "text-right" : ""}`}>{r[c] === null || r[c] === undefined ? "" : typeof r[c] === "number" ? (Number.isInteger(r[c]) ? (r[c] as number).toLocaleString("en-US") : (r[c] as number).toLocaleString("en-US", { maximumFractionDigits: 2 })) : String(r[c])}</td>)}</tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
