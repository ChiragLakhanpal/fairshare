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

import facts from "../deck/facts.json";
import { images, pages } from "../deck/assets";
import { BUILT, slides } from "../deck/slides";
import { bareNumbers, fill, onPath, placeholders, texts, words } from "./deck";

describe("text helpers", () => {
  const f = { facts: { a: { display: "$1,234" } }, dated: { b: { display: "20 of 20" } } };
  it("fills placeholders from facts and dated facts", () => expect(fill("{a} and {b}", f)).toBe("$1,234 and 20 of 20"));
  it("throws on an unknown placeholder", () => expect(() => fill("{nope}", f)).toThrow());
  it("finds digits outside placeholders and the allowlist", () => {
    expect(bareNumbers("In Q3 2026 Summit sent {summit_q3_aa_share} to AA; figure 09; gpt-5-mini; Dynamics 365; the 6 am job")).toEqual([]);
    expect(bareNumbers("Summit sent 53.5% to AA")).toEqual(["53.5"]);
  });
  it("counts words", () => expect(words("one two  three")).toBe(3));
});

// the names come from .env and never from a list in the repo; a clone without .env skips the check
const env = Object.values(import.meta.glob("../../../.env", { query: "?raw", import: "default", eager: true }))[0] as string | undefined;
const blocked = (env?.match(/^FAIRSHARE_DECK_BLOCKLIST=(.*)$/m)?.[1] ?? "").split(",").map((n) => n.trim().toLowerCase()).filter(Boolean);
const known = new Set([...Object.keys(facts.facts), ...Object.keys(facts.dated)]);

describe("slides.ts", () => {
  it("gives every slide a note under 40 words", () => slides.forEach((s) => expect(words(s.note), s.id).toBeLessThan(40)));
  it("finds every asset and every thumb in the build", () => slides.forEach((s) => {
    if (s.kind === "image") expect(images[s.asset!], s.id).toBeTruthy();
    if (s.kind === "live" || s.kind === "animated") {
      expect(pages[s.asset!], s.id).toBeTruthy();
      expect(images[s.thumb!], `${s.id} thumb`).toBeTruthy();
    }
  }));
  it("has no em or en dashes", () => slides.forEach((s) => texts(s).forEach((t) => expect(t, s.id).not.toMatch(/[\u2013\u2014]/))));
  it("names no interviewer", () => slides.forEach((s) => texts(s).forEach((t) => blocked.forEach((n) => expect(t.toLowerCase().includes(n), s.id).toBe(false)))));
  it("tags every Azure possibility and nothing built", () => {
    const tiles = slides.flatMap((s) => (s.native?.layout === "tiles" ? s.native.tiles.map((t) => ({ id: s.id, ...t })) : []));
    tiles.filter((t) => t.id === "azure").forEach((t) => expect(t.tag, t.head).toBe("Possibility"));
    tiles.filter((t) => t.tag === "Possibility").forEach((t) => {
      expect(t.id, t.head).toBe("azure");
      BUILT.forEach((b) => expect(`${t.head} ${t.body}`.includes(b), `${t.head} names ${b}`).toBe(false));
    });
  });
  it("has a fact for every placeholder", () => slides.forEach((s) => texts(s).flatMap(placeholders).forEach((k) => expect(known.has(k), `${s.id}: {${k}}`).toBe(true))));
  it("types no data number by hand", () => slides.forEach((s) => texts(s).forEach((t) => expect(bareNumbers(t), s.id).toEqual([]))));
  it("runs the main path in 35 to 40 minutes and the short one in about 11", () => {
    const full = onPath(slides, "full").reduce((m, s) => m + s.min, 0);
    const short = onPath(slides, "short").reduce((m, s) => m + (s.short ?? 0), 0);
    expect(full >= 35 && full <= 40, `main path ${full}`).toBe(true);
    expect(short >= 10 && short <= 12, `short path ${short}`).toBe(true);
  });
});
