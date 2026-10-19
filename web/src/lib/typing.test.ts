import { describe, expect, it } from "vitest";
import { charCount, revealParts, typingDuration } from "./typing";
import type { ProsePart } from "./runs";

const n = (raw: string): ProsePart => ({ raw, source: "run_sql#1", fact: `x=${raw}` });
const parts: ProsePart[] = ["Harbor sold ", n("$330K"), " of AA travel, down ", n("16.4%"), "."];

describe("revealParts", () => {
  it("shows nothing at zero and everything once the budget covers the text", () => {
    expect(revealParts(parts, 0)).toEqual([]);
    expect(revealParts(parts, charCount(parts))).toEqual(parts);
    expect(revealParts(parts, 999)).toEqual(parts);
  });
  it("cuts a string part mid-way and shows a number only when the budget reaches its end", () => {
    expect(revealParts(parts, 6)).toEqual(["Harbor"]);
    expect(revealParts(parts, 14)).toEqual(["Harbor sold "]);          // two characters into "$330K": not yet
    expect(revealParts(parts, 17)).toEqual(["Harbor sold ", n("$330K")]);
    expect(revealParts(parts, 20)).toEqual(["Harbor sold ", n("$330K"), " of"]);
  });
  it("counts every character, numbers included", () => {
    expect(charCount(parts)).toBe("Harbor sold $330K of AA travel, down 16.4%.".length);
  });
});

describe("typingDuration", () => {
  it("is short for a short answer, grows with length, and never drags past two and a half seconds", () => {
    expect(typingDuration(40)).toBe(500);
    expect(typingDuration(600)).toBeGreaterThan(typingDuration(300));
    expect(typingDuration(20000)).toBe(2500);
  });
});
