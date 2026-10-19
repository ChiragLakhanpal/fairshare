import * as Dropdown from "@radix-ui/react-dropdown-menu";
import { motion, useReducedMotion } from "motion/react";
import { useRef } from "react";
import { copy } from "../copy";
import { copyText, emailDraft, printElement } from "../lib/export";
import { greeting, money, monthLabel, pct, pts, signed, todayLabel, upDown } from "../lib/format";
import { rise, stagger, useTween } from "../lib/motion";
import { summaryHtml, summaryText } from "../lib/share";
import { signalFacts } from "../lib/signals";
import type { Mover, SignalAction, Signals, Summary as SummaryT } from "../lib/types";
import { ChevronDown, Copy, Mail, File as FileIcon, ShareIcon } from "./Icons";
import { SeverityDot } from "./ItemRows";
import { SignalLine } from "./Signals";
import { SummarySkeleton } from "./Skeleton";
import { Term } from "./Term";

type Props = {
  summary: SummaryT | null; loading: boolean; error: string | null; name?: string | null; onWhy: (m: Mover) => void; onAsk: (q: string) => void;
  signals: Signals | null; waiting: number; onAction: (a: SignalAction) => void; onOpenDelegate: () => void;
};

type StatProps = { value: number | null; format: (x: number | null) => string; label: string; term?: string; note: string; color?: string };

function Stat({ value, format, label, term, note, color }: StatProps) {
  const reduced = useReducedMotion();
  const shown = useTween(value, 450, !reduced);   // a new month's value is reached, not jumped to; the first shows at once
  return (
    <div>
      <div className="t-display whitespace-nowrap" style={color ? { color } : undefined}>{format(shown)}</div>
      <div className="mt-1.5 text-[13.5px] text-ink-2">{term ? <Term kpi={term}>{label}</Term> : label}</div>
      <div className="mt-0.5 max-w-[150px] text-[13.5px] text-ink-2">{note}</div>
    </div>
  );
}

export function Summary({ summary, loading, error, name, onWhy, onAsk, signals, waiting, onAction, onOpenDelegate }: Props) {
  const ref = useRef<HTMLDivElement>(null);
  const reduced = useReducedMotion();
  if (error) return <p className="text-red">{error}</p>;
  if (!summary) return <SummarySkeleton />;
  const k = summary.kpis;
  const text = summaryText(summary);
  const item = "flex cursor-pointer items-center gap-2.5 rounded-md px-2.5 py-2 text-sm text-ink outline-none data-[highlighted]:bg-surface";
  const scopeKey = `${summary.region}-${summary.month}`;
  // the worth-knowing lines show only once they belong to the month on screen; while a new month's lines load, the block waits
  const lines = signals && signals.region === summary.region && signals.month === summary.month ? signals : null;
  const facts = lines ? signalFacts(lines) : [];
  const enter = (i: number) => ({ initial: reduced ? false : rise.initial, animate: rise.animate, transition: { duration: 0.25, delay: stagger(i) } });
  const stats: StatProps[] = [
    { value: k.aa_revenue, format: (x) => money(x), label: "AA revenue", note: `${upDown(k.yoy_pct).replace(/^./, (c) => c.toUpperCase())} from ${monthLabel(summary.prior_month)}.` },
    { value: k.aa_share_pct, format: (x) => pct(x), label: "AA share", term: "aa_share", note: "Of all carriers on these markets." },
    { value: k.fair_share_pct, format: (x) => pct(x), label: "Fair share", term: "fair_share", note: "AA's share of the seats here." },
    { value: k.share_gap_pts, format: (x) => pts(x), label: "Share gap", term: "share_gap_pts", note: `That is ${money(Math.abs(k.share_gap_usd))} ${k.share_gap_usd < 0 ? "below" : "above"} fair share.`, color: k.share_gap_pts < 0 ? "#C30019" : "#0078D2" },
    { value: k.pace_pct, format: (x) => pct(x, 0), label: "Pace to goal", term: "pace_pct", note: "Year to date, against the goal.", color: k.pace_pct !== null && k.pace_pct < 100 ? "#C30019" : "#0078D2" },
  ];
  return (
    <div ref={ref} className={`print-section transition-opacity duration-200 ${loading ? "opacity-60" : ""}`} aria-busy={loading || undefined}>
      <div className="flex items-end justify-between gap-6">
        <div>
          <div className="t-label">{greeting(name)} {todayLabel()}</div>
          <motion.h1 key={summary.headline} initial={reduced ? false : { opacity: 0, y: 4 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.2 }} className="t-title mt-2">{summary.headline}</motion.h1>
          {waiting > 0 && (
            <p className="mt-2 text-[14px] text-ink-2">{copy.waitingHome(waiting)} <button type="button" className="no-print text-blue hover:underline" onClick={onOpenDelegate}>{copy.openDelegate}</button></p>
          )}
        </div>
        <Dropdown.Root>
          <Dropdown.Trigger asChild>
            <button type="button" className="press no-print inline-flex items-center gap-1.5 rounded-md px-1.5 py-1 text-[13.5px] font-medium text-blue transition-colors hover:bg-tint" aria-label="Share this summary"><ShareIcon width={15} height={15} />{copy.share}<ChevronDown width={13} height={13} /></button>
          </Dropdown.Trigger>
          <Dropdown.Portal>
            <Dropdown.Content align="end" sideOffset={6} className="menu z-20 min-w-[230px] rounded-lg border border-line bg-white p-1.5 shadow-xl">
              <Dropdown.Item className={item} onSelect={() => void copyText(text, summaryHtml(summary))}><Copy className="text-ink-2" />{copy.shareCopy}</Dropdown.Item>
              <Dropdown.Item className={item} onSelect={() => emailDraft(`${summary.region === "All" ? "All regions" : summary.region}, ${monthLabel(summary.month)}: the month's summary`, text)}><Mail className="text-ink-2" />{copy.shareEmail}</Dropdown.Item>
              <Dropdown.Item className={item} onSelect={() => printElement(ref.current)}><FileIcon className="text-ink-2" />{copy.sharePdf}</Dropdown.Item>
            </Dropdown.Content>
          </Dropdown.Portal>
        </Dropdown.Root>
      </div>

      <div className="mt-7 grid grid-cols-2 justify-between gap-x-5 gap-y-7 sm:grid-cols-3 md:grid-cols-[repeat(5,auto)]">
        {stats.map((s, i) => <motion.div key={s.label} {...enter(i)}><Stat {...s} /></motion.div>)}
      </div>

      <div className="mt-9">
        <div className="flex items-baseline justify-between">
          <h2 className="text-[15px] font-semibold text-ink">{summary.movers.length ? copy.moversTitle(summary.movers.length) : copy.moversNone}</h2>
          <button type="button" className="no-print text-[13.5px] text-blue hover:underline" onClick={() => onAsk(`Show every agency's share against fair share for ${monthLabel(summary.month)}.`)}>{copy.seeAll(summary.agency_count)}</button>
        </div>
        <div className="mt-2">
          {summary.movers.map((m, i) => (
            <motion.div key={`${scopeKey}-${m.agency_id}`} {...enter(i)} className="grid grid-cols-[10px_minmax(0,1fr)_auto] items-center gap-4 border-t hairline py-[13px] text-[14.5px] last:border-b">
              <span className="inline-block h-2.5 w-2.5 rounded-full" style={{ background: m.share_chg_pts < 0 ? "#C30019" : "#0078D2" }} />
              <span>
                <strong>{m.agency}</strong> {m.share_chg_pts < 0 ? "lost" : "gained"} <strong style={{ color: m.share_chg_pts < 0 ? "#C30019" : "#0078D2" }}>{Math.abs(m.share_chg_pts).toFixed(1)} points</strong> of share, from {pct(m.share_prior_pct)} to {pct(m.share_now_pct)}. Revenue was {money(m.revenue_now)}, {upDown(m.yoy_pct)}.
              </span>
              <button type="button" className="no-print text-[14px] text-blue hover:underline" onClick={() => onWhy(m)}>{copy.why}</button>
            </motion.div>
          ))}
        </div>
        <p className="mt-3 text-[14px] text-ink-2">{copy.behindPace(summary.behind_pace.map((b) => `${b.agency} at ${pct(b.pace_pct)}`), summary.agency_count)}</p>
      </div>

      {lines && lines.signals.length > 0 && (
        <div className="mt-9">
          <h2 className="text-[15px] font-semibold text-ink">{copy.signalsTitle}</h2>
          <div className="mt-2">
            {lines.signals.map((s, i) => (
              <motion.div key={`${scopeKey}-${i}`} {...enter(i)} className="grid grid-cols-[10px_minmax(0,1fr)] items-start gap-4 border-t hairline py-[13px] text-[14.5px] leading-[1.5] last:border-b">
                <SeverityDot s={s.severity} className="mt-[7px]" />
                <SignalLine s={s} facts={facts} onAction={onAction} />
              </motion.div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

export function stripParts(s: SummaryT) {
  const k = s.kpis;
  return { revenue: money(k.aa_revenue), yoy: upDown(k.yoy_pct), share: pct(k.aa_share_pct), fair: pct(k.fair_share_pct), gap: `${Math.abs(k.share_gap_pts).toFixed(1)} points`, gapNeg: k.share_gap_pts < 0, pace: pct(k.pace_pct, 0), yoySigned: signed(k.yoy_pct) };
}
