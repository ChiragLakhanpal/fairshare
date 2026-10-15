import { describe, expect, it } from "vitest";
import { copy } from "../copy";
import { doneLabel, hintFor, stepDetail, visibleSteps } from "./steps";
import type { Step } from "./types";

const step = (phase: string, extra: Partial<Step> = {}): Step => ({ phase, text: "", t_ms: 0, ...extra });

describe("stepDetail", () => {
  it("shows the workings from the tool arguments", () => {
    expect(stepDetail(step("genie", { tool: "ask_metrics", args: { question: "What was Harbor's AA share in September 2026?" } }))).toBe('"What was Harbor\'s AA share in September 2026?"');
    expect(stepDetail(step("sql", { tool: "run_sql", args: { sql: "  SELECT agency_name, aa_revenue\nFROM aa_demo.gold.sales_metrics" } }))).toBe("SELECT agency_name, aa_revenue …");
    expect(stepDetail(step("sql", { tool: "run_sql", args: { sql: "SELECT 1" } }))).toBe("SELECT 1");
    expect(stepDetail(step("explain", { tool: "explain_change", args: { agency: "Harbor", month: "2026-09" } }))).toBe("Harbor, September 2026");
    expect(stepDetail(step("agreement", { tool: "search_contracts", args: { agency: "Summit", topic: "share floor" } }))).toBe("Summit: share floor");
    expect(stepDetail(step("model"))).toBeNull();
    expect(stepDetail(step("sql"))).toBeNull();
  });
  it("cuts a long SQL line", () => {
    const d = stepDetail(step("sql", { args: { sql: "SELECT " + "a, ".repeat(60) + "b FROM t" } }))!;
    expect(d.length).toBeLessThanOrEqual(92);
    expect(d.endsWith(" …")).toBe(true);
  });
});

describe("doneLabel", () => {
  it("is past tense with the time it took", () => {
    expect(doneLabel(step("genie"), 23)).toBe("Genie answered in 23 s.");
    expect(doneLabel(step("genie"), 0)).toBe("Genie answered in under a second.");
    expect(doneLabel(step("sql"), 1)).toBe("The query ran in 1 s.");
    expect(doneLabel(step("warehouse"), 1)).toBe("The warehouse was already awake.");
    expect(doneLabel(step("warehouse"), 9)).toBe("The warehouse woke up in 9 s.");
    expect(doneLabel(step("explain"), 2)).toBe("I worked out what moved in 2 s.");
    expect(doneLabel(step("agreement"), 2)).toBe("I read the agreement in 2 s.");
  });
});

describe("hintFor", () => {
  it("is silent for ten seconds, then patient, then specific", () => {
    expect(hintFor("genie", 9)).toBeNull();
    expect(hintFor("genie", 10)).toBe(copy.waitHint);
    expect(hintFor("genie", 45)).toBe(copy.waitGenie);
    expect(hintFor("warehouse", 45)).toBe(copy.waitGenie);
    expect(hintFor("sql", 45)).toBe(copy.waitHint);
    expect(hintFor("sql", 90)).toBe(copy.waitLong);
    expect(hintFor("genie", 90)).toBe(copy.waitLong);
  });
});

describe("visibleSteps", () => {
  it("hides the model's pauses except the current one and times each step from its arrival", () => {
    const steps: Step[] = [
      step("model", { text: "I am reading your question.", at: 1000 }),
      step("sql", { at: 3000 }),
      step("model", { text: "I am reading the results.", at: 8000 }),
      step("verify", { at: 9000 }),
    ];
    expect(visibleSteps(steps, 12000).map((v) => [v.step.phase, v.current, v.seconds])).toEqual([["sql", false, 5], ["verify", true, 3]]);
    expect(visibleSteps(steps.slice(0, 1), 4000).map((v) => [v.step.phase, v.current, v.seconds])).toEqual([["model", true, 3]]);
    expect(visibleSteps([], 4000)).toEqual([]);
  });
});
