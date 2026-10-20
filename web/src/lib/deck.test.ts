import { describe, expect, it } from "vitest";
import { arrivalKey, fromHash, move, pressTarget, type Slide } from "./deck";

const s = (id: string, part: Slide["part"], min: number, short?: number): Slide => ({ id, part, kind: "native", title: id, min, short, note: "" });
export const S: Slide[] = [s("title", "first", 0.5, 0.5), s("ask", "first", 3.5, 2.5), s("pipeline", "data", 1.5), s("system", "built", 2.25, 1.5),
  s("start", "proof", 1, 1), s("words", "backup", 0), s("dict-crm", "backup", 0)];

describe("move", () => {
  it("walks the full path and stops at both ends", () => {
    expect(move(S, "full", "title", 1)).toBe("ask");
    expect(move(S, "full", "title", -1)).toBe("title");
    expect(move(S, "full", "start", 1)).toBe("start"); // never into the backup slides
  });
  it("walks the short path, and from a slide off it goes to the nearest one on it", () => {
    expect(move(S, "short", "ask", 1)).toBe("system");
    expect(move(S, "short", "pipeline", 1)).toBe("system");
    expect(move(S, "short", "pipeline", -1)).toBe("ask");
  });
  it("keeps backup slides among themselves", () => {
    expect(move(S, "full", "words", 1)).toBe("dict-crm");
    expect(move(S, "full", "words", -1)).toBe("words");
  });
  it("sends an unknown id to the first slide", () => expect(move(S, "full", "nope", 1)).toBe("title"));
});

describe("fromHash", () => {
  it("reads the slide id and falls back to the first slide", () => {
    expect(fromHash(S, "#pipeline")).toBe("pipeline");
    expect(fromHash(S, "#dict-crm")).toBe("dict-crm");
    expect(fromHash(S, "")).toBe("title");
    expect(fromHash(S, "#nope")).toBe("title");
  });
});

describe("the animated handoff", () => {
  it("moves the diagram until its last step, then the deck", () => {
    expect(pressTarget(0, 5, 1)).toBe("diagram");
    expect(pressTarget(4, 5, 1)).toBe("diagram");
    expect(pressTarget(5, 5, 1)).toBe("deck");
    expect(pressTarget(3, 5, -1)).toBe("diagram");
    expect(pressTarget(0, 5, -1)).toBe("deck");
  });
  it("counts a frame with no steps as zero steps", () => {
    expect(pressTarget(0, 0, 1)).toBe("deck");
    expect(pressTarget(NaN, NaN, 1)).toBe("deck");
  });
  it("arrives at step 0 going forward and at the end going back", () => {
    expect(arrivalKey(false, 100, false)).toBe("Home");
    expect(arrivalKey(true, 100, false)).toBe("End");
  });
  it("shows the end when the frame started late or motion is reduced", () => {
    expect(arrivalKey(false, 2500, false)).toBe("End");
    expect(arrivalKey(false, 100, true)).toBe("End");
  });
});
