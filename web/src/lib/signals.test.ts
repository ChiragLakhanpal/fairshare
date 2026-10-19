import { describe, expect, it } from "vitest";
import { chipsFrom, relatedSignal, signalFacts } from "./signals";
import type { Signal, Signals } from "./types";

const sig = (over: Partial<Signal>): Signal => ({
  kind: "clause", severity: "watch", agency: null, chip: null,
  sentence: { text: "x", status: "verified", numbers: [] },
  action: { kind: "delegate", agent: "watch", label: "Open Agreement watch" },
  ...over,
});
const summit = sig({ agency: "Summit Travel Partners", chip: "What does Summit Travel Partners' agreement say about its incentive tier?" });
const harbor = sig({ agency: "Harbor Business Travel", chip: "Why is Harbor Business Travel down in September 2026?" });
const harborDeal = sig({ kind: "mismatch", agency: "Harbor Business Travel", chip: "Why is Harbor Business Travel down in September 2026?" });
const seats = sig({ kind: "capacity", chip: "How did AA's seats on ORD-SFO change against last year?", action: { kind: "ask", question: "q", label: "Ask about the market" } });
const fallback = ["Why is Harbor down this month?", "Which agencies are behind pace?", "What does Summit's agreement say about a share floor?"];

describe("chipsFrom", () => {
  it("takes the first three distinct questions the signals suggest", () => {
    expect(chipsFrom([summit, harbor, harborDeal, seats], fallback)).toEqual([summit.chip, harbor.chip, seats.chip]);
  });
  it("pads with the standing chips when the signals suggest fewer than three", () => {
    expect(chipsFrom([summit], fallback)).toEqual([summit.chip, fallback[0], fallback[1]]);
    expect(chipsFrom([sig({ chip: "Why is Harbor down this month?" })], fallback)).toEqual([fallback[0], fallback[1], fallback[2]]);
  });
  it("falls back to the standing chips with no signals", () => {
    expect(chipsFrom(null, fallback)).toEqual(fallback);
    expect(chipsFrom([], fallback)).toEqual(fallback);
  });
});

describe("relatedSignal", () => {
  it("matches an agency by its full name or its first word, as whole words", () => {
    expect(relatedSignal("Why is Harbor down this month? Harbor sold $330K.", [summit, harbor, harborDeal])).toBe(harbor);
    expect(relatedSignal("Compare summit travel partners with last year.", [harbor, summit])).toBe(summit);
    expect(relatedSignal("Which agencies sell alone on DFW-ORD?", [sig({ agency: "Lone Star Travel Group" })])).toBeNull();
  });
  it("ignores lines about no agency and returns null when nothing matches", () => {
    expect(relatedSignal("Which agencies are behind pace?", [seats, summit])).toBeNull();
  });
});

describe("signalFacts", () => {
  it("names each call by tool and position, with the block label and the table it read", () => {
    const s: Signals = {
      region: "All", month: "2026-09", signals: [],
      calls: [{ i: 1, tool: "signals", args: { block: "agreement checks", table: "ops.agreement_checks" }, sql: "SELECT 1", rows: 1, note: "", preview: [{ dollars: 187794 }], genie: null, ms: 0 }],
    };
    expect(signalFacts(s)).toEqual([{ name: "signals#1", label: "agreement checks", source: "ops.agreement_checks", rows: [{ dollars: 187794 }] }]);
  });
});
