// What leaves the app by the clipboard or mail. One structure, two renderings: plain text with blank lines and bullets
// (Messages, Teams, a text field) and HTML for targets that keep bold and lists (Mail, Teams, Slack).
import { copy } from "../copy";
import { money, monthLabel, pct, pts, upDown } from "./format";
import type { Answer, Sentence, Summary } from "./types";

const esc = (s: string) => s.replace(/[&<>]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;" })[c] ?? c);

function summaryParts(s: Summary) {
  const k = s.kpis;
  const numbers: [string, string, string][] = [
    ["AA revenue", money(k.aa_revenue), `, ${upDown(k.yoy_pct)} from ${monthLabel(s.prior_month)}.`],
    ["AA share", pct(k.aa_share_pct), `, against a fair share of ${pct(k.fair_share_pct)}.`],
    ["Share gap", pts(k.share_gap_pts), `. That is ${money(Math.abs(k.share_gap_usd))} ${k.share_gap_usd < 0 ? "below" : "above"} fair share.`],
    ["Pace to goal", pct(k.pace_pct, 0), "."],
  ];
  const movers = s.movers.map((m) => ({
    agency: m.agency, verb: m.share_chg_pts < 0 ? "lost" : "gained", points: `${Math.abs(m.share_chg_pts).toFixed(1)} points`,
    rest: ` of share, from ${pct(m.share_prior_pct)} to ${pct(m.share_now_pct)}. Revenue was ${money(m.revenue_now)}, ${upDown(m.yoy_pct)}.`,
  }));
  return {
    scope: `${s.region === "All" ? "All regions" : `${s.region} region`}, ${monthLabel(s.month)}.`, headline: s.headline, numbers,
    moversTitle: s.movers.length ? copy.moversTitle(s.movers.length) : copy.moversNone, movers,
    pace: copy.behindPace(s.behind_pace.map((b) => `${b.agency} at ${pct(b.pace_pct)}`), s.agency_count),
  };
}

export function summaryText(s: Summary): string {
  const p = summaryParts(s);
  return [`${p.scope} ${p.headline}`, "", ...p.numbers.map(([l, v, r]) => `${l}: ${v}${r}`), "", p.moversTitle, ...p.movers.map((m) => `• ${m.agency} ${m.verb} ${m.points}${m.rest}`), "", p.pace].join("\n");
}

export function summaryHtml(s: Summary): string {
  const p = summaryParts(s);
  return [
    `<p><b>${esc(p.scope)}</b> ${esc(p.headline)}</p>`,
    `<ul>${p.numbers.map(([l, v, r]) => `<li>${esc(l)}: <b>${esc(v)}</b>${esc(r)}</li>`).join("")}</ul>`,
    `<p>${esc(p.moversTitle)}</p>`,
    p.movers.length ? `<ul>${p.movers.map((m) => `<li><b>${esc(m.agency)}</b> ${m.verb} <b>${esc(m.points)}</b>${esc(m.rest)}</li>`).join("")}</ul>` : "",
    `<p>${esc(p.pace)}</p>`,
  ].join("");
}

const isNote = (t: string) => /^sources?:/i.test(t.trim()) || t.trim().toLowerCase().startsWith("could not verify");
/** The sentences on screen: nothing the checker removed, no "Source:" lines. */
export function shownSentences(a: Answer): Sentence[] {
  return a.sentences.filter((s) => s.status !== "flagged" && !isNote(s.text));
}
export function answerBody(a: Answer): string {
  const shown = shownSentences(a);
  return shown.length === 0 && a.removed.length > 0 ? copy.allRemoved : shown.map((s) => s.text).join(" ");
}
export function trustLine(a: Answer): string {
  const shown = shownSentences(a);
  const nums = shown.reduce((n, s) => n + (s.numbers?.length ?? 0), 0);
  if (a.kind === "refusal") return copy.trustRefusal;
  if (a.kind === "general") return copy.trustGeneral;
  if (a.kind === "meta") return copy.trustMeta;
  if (a.cached) return copy.trustCached;
  if (shown.length === 0 && a.removed.length > 0) return copy.trustNone;
  return a.removed.length ? copy.verifiedShown(nums) : copy.verified(nums);
}
export function answerText(a: Answer): string {
  return `${a.question}\n\n${answerBody(a)}\n\n${trustLine(a)}`;
}
export function answerHtml(a: Answer): string {
  return `<p><b>${esc(a.question)}</b></p><p>${esc(answerBody(a))}</p><p>${esc(trustLine(a))}</p>`;
}
