import * as Dropdown from "@radix-ui/react-dropdown-menu";
import { useRef } from "react";
import { copy } from "../copy";
import { copyText, emailDraft, printElement } from "../lib/export";
import { money, monthLabel, pct, pts, signed, todayLabel, upDown } from "../lib/format";
import type { Mover, Summary as SummaryT } from "../lib/types";
import { ChevronDown, Copy, Mail, File as FileIcon, ShareIcon } from "./Icons";
import { Term } from "./Term";

type Props = { summary: SummaryT | null; loading: boolean; error: string | null; onWhy: (m: Mover) => void; onAsk: (q: string) => void };

function Stat({ value, label, term, note, color }: { value: string; label: string; term?: string; note: string; color?: string }) {
  return (
    <div>
      <div className="t-display" style={color ? { color } : undefined}>{value}</div>
      <div className="mt-1.5 text-[13.5px] text-ink-2">{term ? <Term kpi={term}>{label}</Term> : label}</div>
      <div className="mt-0.5 text-[13.5px] text-ink-2">{note}</div>
    </div>
  );
}

export function summaryText(s: SummaryT): string {
  const k = s.kpis;
  const scope = s.region === "All" ? "All regions" : `${s.region} region`;
  const lines = [
    `${scope}, ${monthLabel(s.month)}. ${s.headline}`,
    `AA revenue ${money(k.aa_revenue)}, ${upDown(k.yoy_pct)} from ${monthLabel(s.prior_month)}. AA share ${pct(k.aa_share_pct)} against a fair share of ${pct(k.fair_share_pct)}, a gap of ${pts(k.share_gap_pts)} worth ${money(k.share_gap_usd)}. Pace to goal ${pct(k.pace_pct, 0)}.`,
    ...s.movers.map((m) => `${m.agency} ${m.share_chg_pts < 0 ? "lost" : "gained"} ${Math.abs(m.share_chg_pts).toFixed(1)} points of share, from ${pct(m.share_prior_pct)} to ${pct(m.share_now_pct)}. Revenue was ${money(m.revenue_now)}, ${upDown(m.yoy_pct)}.`),
    copy.behindPace(s.behind_pace.map((b) => `${b.agency} at ${pct(b.pace_pct)}`), 12),
  ];
  return lines.join("\n");
}

export function Summary({ summary, loading, error, onWhy, onAsk }: Props) {
  const ref = useRef<HTMLDivElement>(null);
  if (error) return <p className="text-red">{error}</p>;
  if (!summary || loading) return <div className="animate-pulse text-ink-2">Loading the month.</div>;
  const k = summary.kpis;
  const text = summaryText(summary);
  const item = "flex cursor-pointer items-center gap-2.5 rounded-md px-2.5 py-2 text-sm text-ink outline-none data-[highlighted]:bg-surface";
  return (
    <div ref={ref} className="print-section">
      <div className="flex items-end justify-between gap-6">
        <div>
          <div className="t-label">{todayLabel()}</div>
          <h1 className="t-title mt-2">{summary.headline}</h1>
        </div>
        <Dropdown.Root>
          <Dropdown.Trigger asChild>
            <button type="button" className="press no-print inline-flex items-center gap-1.5 rounded-md px-1.5 py-1 text-[13.5px] font-medium text-blue hover:bg-tint" aria-label="Share this summary"><ShareIcon width={15} height={15} />{copy.share}<ChevronDown width={13} height={13} /></button>
          </Dropdown.Trigger>
          <Dropdown.Portal>
            <Dropdown.Content align="end" sideOffset={6} className="z-20 min-w-[230px] rounded-lg border border-line bg-white p-1.5 shadow-xl">
              <Dropdown.Item className={item} onSelect={() => void copyText(text)}><Copy className="text-ink-2" />{copy.shareCopy}</Dropdown.Item>
              <Dropdown.Item className={item} onSelect={() => emailDraft(`${summary.region === "All" ? "All regions" : summary.region}, ${monthLabel(summary.month)}: the month's summary`, text)}><Mail className="text-ink-2" />{copy.shareEmail}</Dropdown.Item>
              <Dropdown.Item className={item} onSelect={() => printElement(ref.current)}><FileIcon className="text-ink-2" />{copy.sharePdf}</Dropdown.Item>
            </Dropdown.Content>
          </Dropdown.Portal>
        </Dropdown.Root>
      </div>

      <div className="mt-7 flex flex-wrap gap-x-11 gap-y-7">
        <Stat value={money(k.aa_revenue)} label="AA revenue" note={`${upDown(k.yoy_pct).replace(/^./, (c) => c.toUpperCase())} from ${monthLabel(summary.prior_month)}.`} />
        <Stat value={pct(k.aa_share_pct)} label="AA share" term="aa_share" note={k.aa_revenue_prior_year ? "Against all carriers on these markets." : "No comparison a year ago."} />
        <Stat value={pct(k.fair_share_pct)} label="Fair share" term="fair_share" note="AA's share of the seats on these markets." />
        <Stat value={pts(k.share_gap_pts)} label="Share gap" term="share_gap_pts" note={`That is ${money(k.share_gap_usd)} ${k.share_gap_usd < 0 ? "below" : "above"} fair share.`} color={k.share_gap_pts < 0 ? "#C30019" : "#0078D2"} />
        <Stat value={pct(k.pace_pct, 0)} label="Pace to goal" term="pace_pct" note="Year to date, against this year's goal." color={k.pace_pct !== null && k.pace_pct < 100 ? "#C30019" : "#0078D2"} />
      </div>

      <div className="mt-9">
        <div className="flex items-baseline justify-between">
          <h2 className="text-[15px] font-semibold text-ink">{summary.movers.length ? copy.moversTitle : copy.moversNone}</h2>
          <button type="button" className="no-print text-[13.5px] text-blue hover:underline" onClick={() => onAsk(`Show every agency's share against fair share for ${monthLabel(summary.month)}.`)}>{copy.seeAll}</button>
        </div>
        <div className="mt-2">
          {summary.movers.map((m) => (
            <div key={m.agency_id} className="grid grid-cols-[10px_minmax(0,1fr)_auto] items-center gap-4 border-t hairline py-[13px] text-[14.5px] last:border-b">
              <span className="inline-block h-2.5 w-2.5 rounded-full" style={{ background: m.share_chg_pts < 0 ? "#C30019" : "#0078D2" }} />
              <span>
                <strong>{m.agency}</strong> {m.share_chg_pts < 0 ? "lost" : "gained"} <strong style={{ color: m.share_chg_pts < 0 ? "#C30019" : "#0078D2" }}>{Math.abs(m.share_chg_pts).toFixed(1)} points</strong> of share, from {pct(m.share_prior_pct)} to {pct(m.share_now_pct)}. Revenue was {money(m.revenue_now)}, {upDown(m.yoy_pct)}.
              </span>
              <button type="button" className="no-print text-[14px] text-blue hover:underline" onClick={() => onWhy(m)}>{copy.why}</button>
            </div>
          ))}
        </div>
        <p className="mt-3 text-[14px] text-ink-2">{copy.behindPace(summary.behind_pace.map((b) => `${b.agency} at ${pct(b.pace_pct)}`), 12)}</p>
      </div>
    </div>
  );
}

export function stripParts(s: SummaryT) {
  const k = s.kpis;
  return { revenue: money(k.aa_revenue), yoy: upDown(k.yoy_pct), share: pct(k.aa_share_pct), fair: pct(k.fair_share_pct), gap: `${Math.abs(k.share_gap_pts).toFixed(1)} points`, gapNeg: k.share_gap_pts < 0, pace: pct(k.pace_pct, 0), yoySigned: signed(k.yoy_pct) };
}
