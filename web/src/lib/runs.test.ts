import { describe, expect, it } from "vitest";
import { approvalLine, barFraction, decidedLine, draftCount, minutesWord, nounFor, numberTitle, pageLine, progressLine, proseParts, scopeLabel, sidebarLine, startedToast, statusLabel, stepStates, versionLabel, waitingLine, whenLabel } from "./runs";
import type { AgentStep, Progress } from "./types";

const steps: AgentStep[] = [
  { key: "numbers", title: "Numbers", sub: "" }, { key: "why", title: "Why", sub: "" }, { key: "agreement", title: "Agreement", sub: "" }, { key: "crm", title: "CRM", sub: "" },
  { key: "draft", title: "Draft", sub: "" }, { key: "check", title: "Check", sub: "" }, { key: "approve", title: "Approve", sub: "" },
];
const progress = (p: Partial<Progress>): Progress => ({ done: 0, total: 0, text: "", phase: null, item: null, ...p });

describe("runs helpers", () => {
  it("labels statuses, kinds and nouns in plain words", () => {
    expect(statusLabel("needs_approval")).toBe("Needs approval");
    expect(statusLabel("superseded")).toBe("Replaced by a newer run");
    expect(nounFor("precall")).toEqual(["page", "pages"]);
    expect(nounFor("mystery")).toEqual(["item", "items"]);
    expect(draftCount([{ status: "draft" }, { status: "approved" }, { status: "draft" }])).toBe(2);
  });

  it("writes the sidebar line from what the agent is doing", () => {
    const base = { key: "precall", running: null, waiting: 0, last_run: null };
    expect(sidebarLine(base)).toEqual({ text: "Not run yet", tone: "none" });
    expect(sidebarLine({ ...base, running: { run_id: "r1", progress: progress({ done: 1, total: 4, phase: "draft" }) } })).toEqual({ text: "Running, page 2 of 4", tone: "running" });
    expect(sidebarLine({ ...base, waiting: 4, last_run: { run_id: "r1", status: "needs_approval", created_at: "" } })).toEqual({ text: "4 pages waiting", tone: "waiting" });
    expect(sidebarLine({ ...base, key: "watch", waiting: 1, last_run: { run_id: "r1", status: "needs_approval", created_at: "" } })).toEqual({ text: "1 alert waiting", tone: "waiting" });
    expect(sidebarLine({ ...base, last_run: { run_id: "r1", status: "approved", created_at: "" } })).toEqual({ text: "Last run needs nothing from you", tone: "quiet" });
    expect(sidebarLine({ ...base, last_run: { run_id: "r1", status: "failed", created_at: "" } })).toEqual({ text: "The last run failed", tone: "failed" });
  });

  it("lights the stepper by phase", () => {
    expect(stepStates(steps, null)).toEqual(["idle", "idle", "idle", "idle", "idle", "idle", "idle"]);
    expect(stepStates(steps, { status: "running", progress: progress({ total: 4, phase: "facts" }) })).toEqual(["current", "current", "current", "current", "idle", "idle", "idle"]);
    expect(stepStates(steps, { status: "running", progress: progress({ total: 4, phase: "draft" }) })).toEqual(["done", "done", "done", "done", "current", "idle", "idle"]);
    expect(stepStates(steps, { status: "running", progress: progress({ total: 4, phase: "check" }) })).toEqual(["done", "done", "done", "done", "done", "current", "idle"]);
    expect(stepStates(steps, { status: "needs_approval", progress: progress({ done: 4, total: 4, phase: "done" }) })).toEqual(["done", "done", "done", "done", "done", "done", "current"]);
    expect(stepStates(steps, { status: "approved", progress: progress({ done: 4, total: 4 }) })).toEqual(["done", "done", "done", "done", "done", "done", "done"]);
    expect(stepStates(steps, { status: "failed", progress: progress({ done: 1, total: 4 }) })).toEqual(["idle", "idle", "idle", "idle", "idle", "idle", "idle"]);
  });

  it("writes the progress line and the bar from the progress", () => {
    expect(progressLine(progress({ done: 1, total: 4, phase: "draft", item: "BlueSky Corporate Travel" }), "page")).toBe("Page 2 of 4: BlueSky Corporate Travel");
    expect(progressLine(progress({ done: 4, total: 4, phase: "done" }), "page")).toBe("Page 4 of 4");
    expect(progressLine(progress({}), "page")).toBeNull();
    expect(barFraction(progress({ done: 1, total: 4, phase: "draft" }))).toBeCloseTo(0.375);
    expect(barFraction(progress({ done: 4, total: 4, phase: "done" }))).toBe(1);
    expect(barFraction(progress({}))).toBe(0);
  });

  it("states what approving does, in plain words", () => {
    expect(approvalLine({ type: "email", subject: "", body: "", crm: { agency_id: 5, activity_type: "Pre-call pack", subject: "" } })).toBe("Approving records a Pre-call pack in the CRM stand-in and opens this email in your mail app. Nothing is sent until you press send there.");
    expect(approvalLine({ type: "email", subject: "", body: "", crm: null })).toBe("Approving opens this email in your mail app. Nothing is sent until you press send there.");
    expect(approvalLine({ type: "crm", subject: "", body: "", crm: null })).toBe("Approving records a note in the CRM stand-in. Nothing else is sent.");
    expect(approvalLine({ type: "none", subject: "", body: "", crm: null })).toBe("Nothing is recorded. This brief is for reading, and approving marks it as read.");
  });

  it("words the time and the start toast", () => {
    expect(minutesWord(1)).toBe("a minute");
    expect(minutesWord(4)).toBe("two minutes");
    expect(startedToast(4, "pages")).toBe("Started. Four pages take about two minutes. You can switch to Ask and come back; the pages wait here.");
    expect(startedToast(null, "pages")).toBe("Started. You can switch to Ask and come back; the results wait here.");
  });

  it("splits a sentence around its checked numbers, in order, and titles each one", () => {
    const parts = proseParts("Harbor sold $330K, down 16.4% from last year.", [{ raw: "$330K", source: "numbers", fact: "aa_revenue=330114.0" }, { raw: "16.4%", source: "numbers", fact: "yoy_pct=-16.4" }]);
    expect(parts).toEqual(["Harbor sold ", { raw: "$330K", source: "numbers", fact: "aa_revenue=330114.0" }, ", down ", { raw: "16.4%", source: "numbers", fact: "yoy_pct=-16.4" }, " from last year."]);
    expect(proseParts("No numbers here.", [])).toEqual(["No numbers here."]);
    expect(proseParts("Twice 5 and 5.", [{ raw: "5", source: "a", fact: "x=5" }, { raw: "5", source: "a", fact: "x=5" }])).toEqual(["Twice ", { raw: "5", source: "a", fact: "x=5" }, " and ", { raw: "5", source: "a", fact: "x=5" }, "."]);
    expect(numberTitle({ source: "numbers", fact: "aa_revenue=330114.0" })).toBe("Matched aa_revenue=330114.0 from numbers");
    expect(numberTitle({ source: null, fact: null })).toBe("");
  });

  it("names a scope, a time and a decision", () => {
    expect(scopeLabel({ manager: "Marcus Lee", month: "2026-09" })).toBe("Marcus Lee, September 2026");
    expect(scopeLabel({ region: "East", month: "2026-09" })).toBe("the East region, September 2026");
    expect(scopeLabel({ region: "All", month: "2026-09" })).toBe("all regions, September 2026");
    expect(scopeLabel({ market: "CLT-LGA" })).toBe("CLT-LGA");
    expect(whenLabel("2026-10-14T21:03:10")).toBe("October 14 at 9:03 PM");
    expect(decidedLine({ status: "approved", decided_by: "dana@example.com", decided_at: "2026-10-14T21:03:10" })).toBe("Approved by dana@example.com on October 14 at 9:03 PM.");
    expect(decidedLine({ status: "rejected", decided_by: null, decided_at: "2026-10-14T21:03:10" })).toBe("Rejected on October 14 at 9:03 PM.");
    expect(decidedLine({ status: "superseded", decided_by: null, decided_at: null })).toBe("Replaced by a newer version.");
  });

  it("words a page row, a version and the strip", () => {
    expect(pageLine({ status: "draft", decided_at: null })).toBe("Waiting for you");
    expect(pageLine({ status: "approved", decided_at: "2026-10-14T21:03:10" })).toBe("Approved October 14");
    expect(pageLine({ status: "rejected", decided_at: "2026-10-14T21:03:10.250" })).toBe("Rejected October 14");
    expect(versionLabel({ created_at: "2026-10-15T20:57:00", scope: { market: "SEA-DEN" } })).toBe("October 15 at 8:57 PM, for SEA-DEN");
    expect(waitingLine(0)).toBe("Nothing needs a decision right now.");
    expect(waitingLine(1)).toBe("One page waits for your decision.");
    expect(waitingLine(3)).toBe("Three pages wait for your decision.");
    expect(waitingLine(12)).toBe("12 pages wait for your decision.");
  });
});
