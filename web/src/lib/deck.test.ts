import { describe, expect, it } from "vitest";
import { arrivalKey, fromHash, move, pressTarget, type Slide } from "./deck";

const s = (id: string, part: Slide["part"], min: number, short?: number): Slide => ({ id, part, kind: "native", title: id, min, short, note: "" });
export const S: Slide[] = [s("title", "open", 0.5, 0.5), s("ask", "modes", 3.5, 2.5), s("pipeline", "numbers", 1.5), s("system", "numbers", 2.25, 1.5),
  s("start", "aa", 1, 1), s("words", "backup", 0), s("dict-crm", "backup", 0)];
// A talk in miniature, for the frame and the clock's checkpoints: the welcome and the agenda, then the five topics (pipeline is off the short
// path, and so is the whole of Checks and misses), the thanks, a still and a backup slide.
const F: Slide[] = [s("welcome", "open", 0.5, 0.5), s("agenda", "open", 0.5, 0.5), s("problem", "steps", 1, 1), s("what", "modes", 0.5, 0.5),
  s("ask", "modes", 3.5, 2.5), s("pipeline", "numbers", 1.5), s("system", "numbers", 2.25, 1.5), s("checked", "checks", 2), s("limits", "checks", 1),
  s("start", "aa", 1, 1), s("thanks", "close", 0.25, 0.25), { ...s("ask-still", "backup", 0), kind: "image", still: true }, s("words", "backup", 0)];

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

import { checkpointPlan, drift, keyAction, nextPart, plannedStart, TOPIC_ORDER, TOPICS } from "./deck";

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
    expect(nextPart(S, "full", "title")).toBe("ask");
    expect(nextPart(S, "full", "pipeline")).toBe("start"); // system is in the same part
    expect(nextPart(S, "short", "ask")).toBe("system");
    expect(nextPart(S, "full", "start")).toBe("start");
  });
  it("plans each slide's start from the minutes before it", () => {
    expect(plannedStart(S, "full", "ask")).toBe(0.5);
    expect(plannedStart(S, "short", "system")).toBe(3);
  });
  it("says how far behind plan the talk is", () => expect(drift(S, "full", "ask", 1.5)).toBe(1));
  it("puts one checkpoint at the end of each topic on the path, to be reached by the next whole minute", () => {
    expect(checkpointPlan(F, "full")).toEqual([
      { label: "Two slow steps", planned: 2, by: 2 }, { label: "Ask and Delegate", planned: 6, by: 6 }, { label: "Where the numbers come from", planned: 9.75, by: 10 },
      { label: "Checks and misses", planned: 12.75, by: 13 }, { label: "Starting at AA", planned: 13.75, by: 14 },
    ]);
    // a topic ends at its last slide on the path that is on, and a topic with no slide on it has no checkpoint
    expect(checkpointPlan(F, "short")).toEqual([
      { label: "Two slow steps", planned: 2, by: 2 }, { label: "Ask and Delegate", planned: 5, by: 5 },
      { label: "Where the numbers come from", planned: 6.5, by: 7 }, { label: "Starting at AA", planned: 7.5, by: 8 },
    ]);
  });
  it("has a checkpoint for each of the five topics on both paths of the real deck", () => {
    for (const path of ["full", "short"] as const) {
      const plan = checkpointPlan(slides, path);
      expect(plan.map((c) => c.label), path).toEqual(TOPIC_ORDER.map((t) => TOPICS[t].name));
      plan.forEach((c) => expect(c.by, `${path} ${c.label}`).toBe(Math.ceil(c.planned)));
    }
  });
});

import { clock, destination, liveDrift } from "./deck";

describe("where the keys go, and the notes window's clock", () => {
  it("sends Home and End to the main path's ends from anywhere, S to the next part, and the arrows along the path", () => {
    expect(destination(S, "short", "words", "first")).toBe("title");
    expect(destination(S, "full", "ask", "last")).toBe("start");
    expect(destination(S, "full", "title", "part")).toBe("ask");
    expect(destination(S, "short", "ask", "next")).toBe("system");
    expect(destination(S, "full", "ask", "prev")).toBe("title");
    expect(keyAction({ key: "P" })).toBe("notes");
  });
  it("keeps S on a backup slide, and walks the real deck's parts", () => {
    expect(nextPart(S, "full", "words")).toBe("words");
    expect(nextPart(slides, "full", "title")).toBe("problem"); // the welcome is a part of its own
    expect(nextPart(slides, "short", "title")).toBe("problem");
    expect(nextPart(slides, "full", "problem")).toBe("what"); // the first topic ends and the second begins
    expect(nextPart(slides, "short", "problem")).toBe("what");
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

import { frameInfo, isTopic, PARTS, type FrameInfo } from "./deck";

describe("the topics", () => {
  it("are the five the talk is told in, word for word and in order", () => {
    expect(TOPIC_ORDER).toEqual(["steps", "modes", "numbers", "checks", "aa"]);
    expect(TOPIC_ORDER.map((t) => TOPICS[t])).toEqual([
      { name: "Two slow steps", line: "What I heard in round one about share questions and pre-call packs." },
      { name: "Ask and Delegate", line: "The app answers a share question and drafts a pre-call pack, live." },
      { name: "Where the numbers come from", line: "The data behind the seven numbers, and why Harbor fell in September." },
      { name: "Checks and misses", line: "How the app checks each number, what the tests found, and what it can't do yet." },
      { name: "Starting at AA", line: "The same layers on AA's own data, and the first four steps." },
    ]);
  });
  it("name the parts, in the order the notes window's outline lists them", () => {
    expect(Object.keys(PARTS)).toEqual(["open", ...TOPIC_ORDER, "close", "backup"]);
    expect(Object.values(PARTS)).toEqual(["Welcome", "Two slow steps", "Ask and Delegate", "Where the numbers come from", "Checks and misses", "Starting at AA", "Thank you", "Backup"]);
  });
  it("are told from the other parts", () => {
    expect(TOPIC_ORDER.every(isTopic)).toBe(true);
    expect((["open", "close", "backup"] as const).some(isTopic)).toBe(false);
  });
  it("hold to the content rules, as the slides do", () => {
    Object.values(TOPICS).flatMap((t) => [t.name, t.line]).forEach((t) => {
      expect(t).not.toMatch(/[\u2013\u2014]/);
      expect(bareNumbers(t), t).toEqual([]);
      blocked.forEach((n) => expect(t.toLowerCase().includes(n), t).toBe(false));
    });
  });
});

describe("what the frame draws", () => {
  // the logo only: what the first and last slides of the path get, and the base the other cases change
  const frame = (over: Partial<FrameInfo> = {}): FrameInfo => ({ bare: false, tracker: false, topic: null, inTopic: null, number: null, footer: false, backup: false, ...over });

  it("lights the topic of a topic slide, with its place among that topic's slides on the path and its number on the path", () => {
    expect(frameInfo(F, "full", "problem")).toEqual(frame({ tracker: true, topic: "steps", inTopic: { at: 1, of: 1 }, number: { at: 3, of: 11 }, footer: true }));
    expect(frameInfo(F, "full", "what")).toEqual(frame({ tracker: true, topic: "modes", inTopic: { at: 1, of: 2 }, number: { at: 4, of: 11 }, footer: true }));
    expect(frameInfo(F, "full", "ask")).toEqual(frame({ tracker: true, topic: "modes", inTopic: { at: 2, of: 2 }, number: { at: 5, of: 11 }, footer: true }));
    expect(frameInfo(F, "full", "limits")).toEqual(frame({ tracker: true, topic: "checks", inTopic: { at: 2, of: 2 }, number: { at: 9, of: 11 }, footer: true }));
    expect(frameInfo(F, "full", "start")).toEqual(frame({ tracker: true, topic: "aa", inTopic: { at: 1, of: 1 }, number: { at: 10, of: 11 }, footer: true }));
  });
  it("counts only the slides on the path that is on", () => {
    expect(frameInfo(F, "full", "system")).toEqual(frame({ tracker: true, topic: "numbers", inTopic: { at: 2, of: 2 }, number: { at: 7, of: 11 }, footer: true }));
    // pipeline is off the short path, so system is the only slide of its topic on it
    expect(frameInfo(F, "short", "system")).toEqual(frame({ tracker: true, topic: "numbers", inTopic: { at: 1, of: 1 }, number: { at: 6, of: 8 }, footer: true }));
  });
  it("numbers the short path from 1 to its length, and the welcome and the thanks show no number", () => {
    const line = onPath(F, "short");
    expect(line).toHaveLength(8);
    expect(line.map((x) => frameInfo(F, "short", x.id).number?.at ?? null)).toEqual([null, 2, 3, 4, 5, 6, 7, null]);
    line.slice(1, -1).forEach((x) => expect(frameInfo(F, "short", x.id).number?.of, x.id).toBe(8));
  });
  it("numbers the real deck along the path that is on", () => {
    for (const path of ["full", "short"] as const) {
      const line = onPath(slides, path);
      line.slice(1, -1).forEach((x, i) => expect(frameInfo(slides, path, x.id).number, `${path} ${x.id}`).toEqual({ at: i + 2, of: line.length }));
    }
  });
  it("shows the logo only on the first and last slides of the path", () => {
    for (const path of ["full", "short"] as const) for (const id of ["welcome", "thanks"]) expect(frameInfo(F, path, id), `${path} ${id}`).toEqual(frame());
  });
  it("shows the footer but no tracker on an open slide that is not the first", () => {
    expect(frameInfo(F, "full", "agenda")).toEqual(frame({ number: { at: 2, of: 11 }, footer: true }));
    expect(frameInfo(F, "short", "agenda")).toEqual(frame({ number: { at: 2, of: 8 }, footer: true }));
  });
  it("gives a backup slide the frame with no number and no topic lit, and a still no frame at all", () => {
    expect(frameInfo(F, "full", "words")).toEqual(frame({ tracker: true, footer: true, backup: true }));
    expect(frameInfo(F, "short", "words")).toEqual(frame({ tracker: true, footer: true, backup: true }));
    expect(frameInfo(F, "full", "ask-still")).toEqual(frame({ bare: true, backup: true }));
  });
  it("lights the topic of a slide the path leaves out, but gives it no place and no number", () => {
    expect(frameInfo(F, "short", "pipeline")).toEqual(frame({ tracker: true, topic: "numbers", footer: true }));
    expect(frameInfo(F, "short", "limits")).toEqual(frame({ tracker: true, topic: "checks", footer: true }));
  });
  it("takes an unknown id for the first slide", () => expect(frameInfo(F, "full", "nope")).toEqual(frameInfo(F, "full", "welcome")));
});

import { arrivalStep, showsData, stepCount, type Facts, type Native, type Result, type Tile } from "./deck";

describe("native steps", () => {
  const native = (n: Native): Slide => ({ ...s("x", "steps", 1), native: n });
  const tile = (head: string): Tile => ({ head, body: "A body." });
  const result: Result = { head: "A test", body: "What it tests.", result: "What it found." };

  it("counts a step for each line, tile, table, check, result and demo line", () => {
    expect(stepCount(native({ layout: "statement", lines: ["One.", "Two.", "Three."] }))).toBe(3);
    expect(stepCount(native({ layout: "tiles", tiles: [tile("A"), tile("B")] }))).toBe(2);
    expect(stepCount(native({ layout: "table", tables: ["gold.dim_agency", "gold.dim_market"] }))).toBe(2);
    expect(stepCount(native({ layout: "checks", keys: ["a", "b", "c", "d"] }))).toBe(4);
    expect(stepCount(native({ layout: "results", items: [result, result, result] }))).toBe(3);
    expect(stepCount(native({ layout: "demo", demo: { kind: "precall" }, lines: ["One.", "Two."] }))).toBe(2);
  });
  it("counts the question to the room as a step after the lines", () => {
    expect(stepCount(native({ layout: "statement", lines: ["One.", "Two."], ask: "A question?" }))).toBe(3);
    expect(stepCount(native({ layout: "statement", lines: [], ask: "A question?" }))).toBe(1);
  });
  it("counts the five topics for the agenda, and none for the checks shown at once or for the close", () => {
    expect(stepCount(native({ layout: "agenda" }))).toBe(5);
    expect(stepCount(native({ layout: "checks" }))).toBe(0);
    expect(stepCount(native({ layout: "close", lines: ["Thank you.", "Questions?"] }))).toBe(0);
  });
  it("counts none on a figure, a live page or a slide with no layout", () => {
    for (const kind of ["image", "live", "animated", "native"] as const) expect(stepCount({ ...s("fig", "steps", 1), kind }), kind).toBe(0);
  });
  it("arrives on step 0 going forward, and complete going back or on a load", () => {
    const three = native({ layout: "statement", lines: ["One.", "Two.", "Three."] });
    expect(arrivalStep(three, "forward")).toBe(0);
    expect(arrivalStep(three, "backward")).toBe(3);
    expect(arrivalStep(three, "load")).toBe(3);
    expect(arrivalStep(native({ layout: "close", lines: ["Thank you."] }), "backward")).toBe(0);
  });
  it("hands a press to the slide until its last step, then to the deck, with pressTarget", () => {
    const three = native({ layout: "statement", lines: ["One.", "Two.", "Three."] });
    const count = stepCount(three);
    // pressTarget calls a press that stays on the slide "diagram", whatever the slide holds
    expect([0, 1, 2, 3].map((at) => pressTarget(at, count, 1))).toEqual(["diagram", "diagram", "diagram", "deck"]);
    expect([0, 1, 2, 3].map((at) => pressTarget(at, count, -1))).toEqual(["deck", "diagram", "diagram", "diagram"]);
    expect(pressTarget(arrivalStep(three, "backward"), count, 1)).toBe("deck"); // complete on arrival, so a forward press moves on
    expect(pressTarget(arrivalStep(three, "forward"), count, -1)).toBe("deck"); // nothing shown yet, so a back press moves back
  });
});

describe("a slide that shows data", () => {
  const f: Facts = { facts: { rows: { display: "3,000" } }, dated: { when: { display: "Oct 19" } } };
  const native = (n: Native, over: Partial<Slide> = {}): Slide => ({ ...s("x", "numbers", 1), native: n, ...over });
  const byId = (id: string) => slides.find((x) => x.id === id)!;

  it("is a table, the checks, or a figure marked as data", () => {
    expect(showsData(native({ layout: "table", tables: ["gold.dim_agency"] }), f)).toBe(true);
    expect(showsData(native({ layout: "checks" }), f)).toBe(true);
    expect(showsData({ ...s("fig", "numbers", 1), kind: "image", data: true }, f)).toBe(true);
  });
  it("is native text that holds a fact, in any layout and in the title", () => {
    expect(showsData(native({ layout: "statement", lines: ["{rows} rows."] }), f)).toBe(true);
    expect(showsData(native({ layout: "statement", lines: ["One."], ask: "Why {rows}?" }), f)).toBe(true);
    expect(showsData(native({ layout: "tiles", tiles: [{ head: "A", body: "{rows} rows." }] }), f)).toBe(true);
    expect(showsData(native({ layout: "results", items: [{ head: "A", body: "B", result: "C", miss: "{rows} missed" }] }), f)).toBe(true);
    expect(showsData(native({ layout: "close", lines: ["{rows}"] }), f)).toBe(true);
    expect(showsData(native({ layout: "agenda" }, { title: "{rows} rows" }), f)).toBe(true);
  });
  it("is not a dated fact, a fact only in the note, or a figure that is not marked", () => {
    expect(showsData(native({ layout: "statement", lines: ["Scored on {when}."] }), f)).toBe(false);
    expect(showsData(native({ layout: "statement", lines: ["Plain words."] }, { note: "There are {rows} rows." }), f)).toBe(false);
    expect(showsData({ ...s("fig", "numbers", 1), kind: "image" }, f)).toBe(false);
    expect(showsData(native({ layout: "agenda" }), f)).toBe(false);
  });
  it("keeps the checks and the row slides of the deck on the synthetic data footer, and the problem slide off it", () => {
    expect(showsData(byId("checks"), facts)).toBe(true);
    expect(showsData(byId("row"), facts)).toBe(true);
    expect(showsData(byId("problem"), facts)).toBe(false);
  });
});

describe("the words a slide shows", () => {
  const base: Slide = { ...s("x", "steps", 1), title: "T", note: "N" };
  const native = (n: Native): Slide => ({ ...base, native: n });

  it("lists a live slide's byline after its title", () => expect(texts({ ...base, kind: "live", byline: ["B1", "B2"] })).toEqual(["T", "B1", "B2", "N"]));
  it("lists the question to the room after a statement's lines", () => {
    expect(texts(native({ layout: "statement", lines: ["L1", "L2"], ask: "Q" }))).toEqual(["T", "L1", "L2", "Q", "N"]);
    expect(texts(native({ layout: "statement", lines: ["L1"] }))).toEqual(["T", "L1", "N"]);
  });
  it("lists every field of every result, and a miss only where there is one", () => {
    const items = [{ head: "H1", body: "B1", result: "R1", miss: "M1" }, { head: "H2", body: "B2", result: "R2" }];
    expect(texts(native({ layout: "results", items }))).toEqual(["T", "H1", "B1", "R1", "M1", "H2", "B2", "R2", "N"]);
  });
  it("lists the closing lines, and nothing more for the agenda, whose words are the topics'", () => {
    expect(texts(native({ layout: "close", lines: ["C1", "C2"] }))).toEqual(["T", "C1", "C2", "N"]);
    expect(texts(native({ layout: "agenda" }))).toEqual(["T", "N"]);
  });
  it("still lists a table's keys, a tile's tag and the Ask demo's question", () => {
    expect(texts(native({ layout: "table", tables: ["gold.dim_agency"] }))).toEqual(["T", "gold.dim_agency", "N"]);
    expect(texts(native({ layout: "tiles", tiles: [{ head: "H", body: "B", tag: "Possibility" }] }))).toEqual(["T", "H", "B", "Possibility", "N"]);
    expect(texts(native({ layout: "demo", demo: { kind: "ask", question: "Why?" }, lines: ["L"] }))).toEqual(["T", "Why?", "L", "N"]);
  });
});

describe("the checks layout", () => {
  const slide: Slide = { id: "fake-checks", part: "numbers", kind: "native", title: "A fixture", min: 0, note: "", native: { layout: "checks" } };

  it("draws every check, and says the data is synthetic", () => {
    const html = renderToStaticMarkup(createElement(NativeSlide, { slide, facts }));
    facts.checks.filter((c) => !c.name.includes("'")).forEach((c) => expect(html).toContain(c.name)); // React escapes an apostrophe
    expect(html).toContain("synthetic data");
  });
  it("draws the title and does not throw for a layout no slide uses yet", () => {
    for (const native of [{ layout: "results", items: [] }, { layout: "agenda" }, { layout: "close", lines: ["Thank you."] }] as Native[]) {
      expect(renderToStaticMarkup(createElement(NativeSlide, { slide: { ...slide, native }, facts })), native.layout).toContain("A fixture");
    }
  });
});
