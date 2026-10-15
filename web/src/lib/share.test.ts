import { describe, expect, it } from "vitest";
import { answerHtml, answerText, summaryHtml, summaryText } from "./share";
import type { Answer, Summary } from "./types";

const summary: Summary = {
  region: "All", month: "2026-09", prior_month: "2025-09", headline: "September closed ahead of pace and a little under fair share.",
  kpis: { aa_revenue: 4492373, aa_revenue_prior_year: 4456241, yoy_pct: 0.8, aa_share_pct: 37.8, fair_share_pct: 39.0, share_gap_pts: -1.2, share_gap_usd: -143384, pace_pct: 139.1 },
  movers: [{ agency_id: 5, agency: "Harbor Business Travel", region: "East", share_now_pct: 34.2, share_prior_pct: 44.3, share_chg_pts: -10.1, revenue_now: 330114, yoy_pct: -16.4 }],
  behind_pace: [{ agency_id: 5, agency: "Harbor Business Travel", pace_pct: 96.1, aa_revenue: 330114, yoy_pct: -16.4 }], agency_count: 4, calls: [],
};
const answer: Answer = {
  question: "Why is Harbor down this month?", text: "Harbor sold $330K, down 16.4%. Source: ask_metrics.", model: "x", kind: "numbers",
  sentences: [
    { text: "Harbor sold $330K, down 16.4%.", status: "verified", numbers: [{ raw: "$330K", source: "run_sql#1", fact: "330114" }, { raw: "16.4%", source: "run_sql#1", fact: "-16.4" }] },
    { text: "Source: ask_metrics.", status: "note", numbers: [] },
  ],
  removed: [], could_not_verify: [], verified_text: "Harbor sold $330K, down 16.4%. Source: ask_metrics.", calls: [], sources: [], follow_ups: [],
  genie_conversation_id: null, timing: { total_ms: 40, tools_ms: 12 }, cached: null, trace_url: null,
};

describe("summaryText", () => {
  it("is sections split by blank lines, one line per number, a bullet per mover", () => {
    expect(summaryText(summary).split("\n")).toEqual([
      "All regions, September 2026. September closed ahead of pace and a little under fair share.",
      "",
      "AA revenue: $4.49M, up 0.8% from September 2025.",
      "AA share: 37.8%, against a fair share of 39.0%.",
      "Share gap: −1.2 pts. That is $143K below fair share.",
      "Pace to goal: 139%.",
      "",
      "One agency moved the most this month.",
      "• Harbor Business Travel lost 10.1 points of share, from 44.3% to 34.2%. Revenue was $330K, down 16.4%.",
      "",
      "One agency is behind pace: Harbor Business Travel at 96.1%. The other 3 are ahead.",
    ]);
  });
});

describe("summaryHtml", () => {
  it("keeps the structure for rich targets and escapes the text", () => {
    const h = summaryHtml({ ...summary, headline: "Harbor & co <moved>." });
    expect(h).toContain("<p><b>All regions, September 2026.</b> Harbor &amp; co &lt;moved&gt;.</p>");
    expect(h.match(/<li>/g)?.length).toBe(5);
    expect(h).toContain("<li>AA revenue: <b>$4.49M</b>, up 0.8% from September 2025.</li>");
    expect(h).toContain("<li><b>Harbor Business Travel</b> lost <b>10.1 points</b> of share, from 44.3% to 34.2%. Revenue was $330K, down 16.4%.</li>");
  });
});

describe("answerText", () => {
  it("is the question, the sentences you can see, and the trust line", () => {
    expect(answerText(answer)).toBe("Why is Harbor down this month?\n\nHarbor sold $330K, down 16.4%.\n\nAll 2 numbers in this answer came from the query results.");
  });
  it("says what was removed when the checker cut a sentence", () => {
    const cut = { ...answer, removed: [{ sentence: "Harbor sold $999K.", reason: "no query supports $999K" }] };
    expect(answerText(cut).split("\n\n")[2]).toBe("The 2 numbers you can see came from the query results.");
  });
});

describe("answerHtml", () => {
  it("bolds the question and keeps three paragraphs", () => {
    expect(answerHtml(answer)).toBe("<p><b>Why is Harbor down this month?</b></p><p>Harbor sold $330K, down 16.4%.</p><p>All 2 numbers in this answer came from the query results.</p>");
  });
});
