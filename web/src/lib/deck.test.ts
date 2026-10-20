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

import { checkpointPlan, drift, keyAction, nextPart, plannedStart } from "./deck";

describe("keyAction", () => {
  it("maps clicker and keyboard keys, letters in either case", () => {
    for (const k of ["ArrowRight", " ", "PageDown"]) expect(keyAction({ key: k })).toBe("next");
    for (const k of ["ArrowLeft", "PageUp"]) expect(keyAction({ key: k })).toBe("prev");
    expect([keyAction({ key: "Home" }), keyAction({ key: "End" }), keyAction({ key: "s" }), keyAction({ key: "S" }), keyAction({ key: "p" })])
      .toEqual(["first", "last", "part", "part", "notes"]);
  });
  it("leaves browser shortcuts alone", () => {
    expect(keyAction({ key: "p", metaKey: true })).toBeNull();
    expect(keyAction({ key: "f", ctrlKey: true, metaKey: true })).toBeNull();
    expect(keyAction({ key: "ArrowRight", altKey: true })).toBeNull();
  });
});

describe("parts and the clock", () => {
  it("jumps to the first slide of the next part on the path", () => {
    expect(nextPart(S, "full", "title")).toBe("pipeline");
    expect(nextPart(S, "short", "ask")).toBe("system");
    expect(nextPart(S, "full", "start")).toBe("start");
  });
  it("plans each slide's start from the minutes before it", () => {
    expect(plannedStart(S, "full", "ask")).toBe(0.5);
    expect(plannedStart(S, "short", "system")).toBe(3);
  });
  it("says how far behind plan the talk is", () => expect(drift(S, "full", "ask", 1.5)).toBe(1));
  it("puts the checkpoints where the spec says", () => {
    expect(checkpointPlan(slides, "full")).toEqual([{ label: "precall done", planned: 28, by: 29 }, { label: "start", planned: 35.25, by: 36 }]);
    expect(checkpointPlan(slides, "short")).toEqual([{ label: "ask done", planned: 4.5, by: 5 }, { label: "start", planned: 9.75, by: 11 }]);
  });
});

import { clock, destination, liveDrift } from "./deck";

describe("where the keys go, and the notes window's clock", () => {
  it("sends Home and End to the main path's ends from anywhere, S to the next part, and the arrows along the path", () => {
    expect(destination(S, "short", "words", "first")).toBe("title");
    expect(destination(S, "full", "ask", "last")).toBe("start");
    expect(destination(S, "full", "title", "part")).toBe("pipeline");
    expect(destination(S, "short", "ask", "next")).toBe("system");
    expect(destination(S, "full", "ask", "prev")).toBe("title");
    expect(keyAction({ key: "P" })).toBe("notes");
  });
  it("keeps S on a backup slide, and walks the real deck's parts", () => {
    expect(nextPart(S, "full", "words")).toBe("words");
    expect(nextPart(slides, "full", "title")).toBe("elevator-opener");
    expect(nextPart(slides, "short", "title")).toBe("system");
  });
  it("shows the drift a slide arrived with until the slide runs past its minutes", () => {
    expect(liveDrift(S, "full", "ask", 1.5, 1.5)).toBe(1);
    expect(liveDrift(S, "full", "ask", 1.5, 4)).toBe(1); // two and a half of its three and a half minutes
    expect(liveDrift(S, "full", "ask", 1.5, 6)).toBe(2); // a minute over
    expect(liveDrift(S, "short", "pipeline", 3, 4)).toBe(1); // off the short path, every minute counts
  });
  it("reads minutes as a clock", () => {
    expect([clock(80 / 60), clock(-0.75), clock(35.25), clock(0), clock(59.6 / 60)]).toEqual(["1:20", "0:45", "35:15", "0:00", "1:00"]);
  });
});

import { clockStart } from "./deck";

describe("the clock's start", () => {
  it("dates the talk back by the planned start of the slide the first move lands on, on the path that is on", () => {
    expect(clockStart(S, "full", "ask", 600000)).toBe(600000 - 0.5 * 60000);
    expect(clockStart(S, "short", "ask", 600000)).toBe(600000 - 0.5 * 60000);
    expect(clockStart(S, "short", "system", 600000)).toBe(600000 - 3 * 60000); // the short plan's start
    expect(clockStart(S, "full", "system", 600000)).toBe(600000 - 5.5 * 60000);
  });
  it("starts at the move itself on a backup slide, which has no planned time", () => expect(clockStart(S, "full", "words", 600000)).toBe(600000));
});

import { askQuestion } from "./deck";

describe("the Ask demo's question", () => {
  it("is the one the Ask demo slide holds, and none when no slide asks", () => {
    expect(askQuestion(slides)).toBe("Why is Harbor Business Travel down in September?");
    expect(askQuestion(S)).toBeNull();
  });
});

import { showEyebrow } from "./deck";

describe("the part label", () => {
  const byId = (id: string) => slides.find((s) => s.id === id)!;
  it("is drawn on an ordinary slide and left off a still, which has the app's own top bar under that corner", () => {
    expect(showEyebrow(byId("coverage"))).toBe(true); // an ordinary image slide
    expect(showEyebrow(byId("title"))).toBe(true);
    expect(showEyebrow(byId("ask-still"))).toBe(false);
    expect(showEyebrow(byId("precall-still"))).toBe(false);
  });
  it("is left off exactly the two stills, and a still is an image slide", () => {
    expect(slides.filter((s) => !showEyebrow(s)).map((s) => s.id)).toEqual(["ask-still", "precall-still"]);
    slides.filter((s) => s.still).forEach((s) => expect(s.kind, s.id).toBe("image"));
  });
});

import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { NativeSlide } from "../deck/layouts";
import { knownTables } from "./deck";

// A table slide names its tables by key, and the deck has no error boundary: a key that facts.json does not describe used to
// leave facts.columns[key] undefined and throw while the slide drew.
describe("a table slide's keys", () => {
  const tableKeys = (list: Slide[]) => list.flatMap((s) => (s.native?.layout === "table" ? s.native.tables.map((key) => ({ id: s.id, key })) : []));
  const unknown = (list: Slide[]) => tableKeys(list).filter(({ key }) => knownTables([key], facts.columns).length === 0).map(({ id, key }) => `${id}: ${key}`);
  const named = ["checks", "gold.dim_agency", "gold.no_such_table"];
  const fake: Slide = { id: "fake", part: "backup", kind: "native", title: "A fixture", min: 0, note: "", native: { layout: "table", tables: named } };

  it("are the checks or a table that facts.json describes, on every slide of the deck", () => expect(unknown(slides)).toEqual([]));
  it("catches a key that facts.json does not describe (a fixture, not the deck)", () => expect(unknown([fake])).toEqual(["fake: gold.no_such_table"]));
  it("are skipped by the guard when unknown, in order", () => expect(knownTables(named, facts.columns)).toEqual(["checks", "gold.dim_agency"]));
  it("do not stop a table slide from drawing, and the unknown one is left out", () => {
    const html = renderToStaticMarkup(createElement(NativeSlide, { slide: fake, facts }));
    expect(html).toContain("gold.dim_agency");
    expect(html).not.toContain("no_such_table");
  });
});

import { driftIsRed } from "./deck";

describe("the drift line's colour", () => {
  it("stays plain until the talk is 30 seconds behind plan, then turns red", () => {
    expect([1, 5, 29].map((s) => driftIsRed(s / 60))).toEqual([false, false, false]);
    expect([30, 31, 120].map((s) => driftIsRed(s / 60))).toEqual([true, true, true]);
  });
  it("is never red when the talk is on time or ahead", () => expect([driftIsRed(0), driftIsRed(-0.5), driftIsRed(-10)]).toEqual([false, false, false]));
});
