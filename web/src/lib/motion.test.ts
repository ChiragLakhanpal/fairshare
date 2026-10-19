import { describe, expect, it } from "vitest";
import { depthOf, easeOut, slideDirection, stagger, tweenAt } from "./motion";

describe("slideDirection", () => {
  it("brings Delegate in from the right and Ask in from the left, the way the switch is drawn", () => {
    expect(slideDirection("delegate")).toBe(1);
    expect(slideDirection("ask")).toBe(-1);
  });
});

describe("depthOf", () => {
  it("counts how deep a Delegate view is: the overview, an agent, a page", () => {
    expect(depthOf({ agent: null, runId: null, itemId: null })).toBe(0);
    expect(depthOf({ agent: "watch", runId: null, itemId: null })).toBe(1);
    expect(depthOf({ agent: "watch", runId: "r1", itemId: "i1" })).toBe(2);
  });
});

describe("stagger", () => {
  it("delays each row a little more than the last and stops growing after eight", () => {
    expect(stagger(0)).toBe(0);
    expect(stagger(1)).toBeCloseTo(0.035);
    expect(stagger(3)).toBeCloseTo(0.105);
    expect(stagger(20)).toBeCloseTo(stagger(8));
  });
});

describe("tweenAt", () => {
  it("starts at the old value, ends at the new one, and moves fastest at the start", () => {
    expect(tweenAt(100, 200, 0)).toBe(100);
    expect(tweenAt(100, 200, 1)).toBe(200);
    const early = tweenAt(100, 200, 0.25) - 100;
    const late = 200 - tweenAt(100, 200, 0.75);
    expect(early).toBeGreaterThan(late);
    expect(easeOut(0.5)).toBeGreaterThan(0.5);
  });
  it("keeps the sign and the decimals of the values it moves between", () => {
    expect(tweenAt(-1.2, 3.4, 0.5)).toBeGreaterThan(-1.2);
    expect(tweenAt(-1.2, 3.4, 0.5)).toBeLessThan(3.4);
  });
});
