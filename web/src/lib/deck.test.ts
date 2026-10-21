import { describe, expect, it } from "vitest";
import { arrivalKey, FRAME_FALLBACK_MS, fromHash, move, pressTarget, type Slide } from "./deck";

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
  it("arrives at step 0 going forward, and at the end going back and after a load (a reload, or the way back from a demo)", () => {
    expect(arrivalKey("forward", 100, false)).toBe("Home");
    expect(arrivalKey("backward", 100, false)).toBe("End");
    expect(arrivalKey("load", 100, false)).toBe("End");
  });
  it("shows the end when the frame got ready after the finished figure showed in its place, or motion is reduced", () => {
    expect(arrivalKey("forward", FRAME_FALLBACK_MS - 1, false)).toBe("Home");
    expect(arrivalKey("forward", FRAME_FALLBACK_MS + 1, false)).toBe("End");
    expect(arrivalKey("forward", 100, true)).toBe("End");
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

// The talk as the spec's table tells it: the main path in order, each slide with its part, its minutes and, on the short path, its minutes
// there. row is split in two, row and seats, a minute each, and numbers keeps 1.75 minutes until gaps joins the path after it.
const TALK: [id: string, part: Slide["part"], min: number, short?: number][] = [
  ["welcome", "open", 0.5, 0.5], ["agenda", "open", 0.5, 0.5],
  ["problem", "steps", 1, 1],
  ["what", "modes", 0.5, 0.5], ["query-opener", "modes", 0.25], ["ask", "modes", 3.5, 2.5], ["director", "modes", 1.25], ["riffle-opener", "modes", 0.25],
  ["delegate", "modes", 1.25], ["precall", "modes", 3, 2],
  ["stack-opener", "numbers", 0.25], ["system", "numbers", 2.25, 1.5], ["elevator-opener", "numbers", 0.25], ["pipeline", "numbers", 1.5],
  ["row", "numbers", 1], ["seats", "numbers", 1], ["revenue", "numbers", 0.75], ["checks", "numbers", 1], ["numbers", "numbers", 1.75],
  ["share-fair", "numbers", 1], ["moved", "numbers", 1.5],
  ["sieve-opener", "checks", 0.25], ["checked", "checks", 2], ["guardrails", "checks", 1.5], ["evals", "checks", 1, 1.5], ["evals-more", "checks", 1],
  ["limits", "checks", 1],
  ["at-aa", "aa", 1.5], ["azure", "aa", 0.75], ["start", "aa", 1, 1], ["know", "aa", 1],
  ["thanks", "close", 0.25, 0.25],
];

describe("the talk's order", () => {
  const byId = (id: string) => slides.find((x) => x.id === id);
  it("walks the main path in the spec's order, each slide in its part", () => {
    expect(onPath(slides, "full").map((x) => [x.id, x.part])).toEqual(TALK.map(([id, part]) => [id, part]));
  });
  it("plans each slide's minutes on the main path and, for the slides on it, on the short path", () => {
    expect(onPath(slides, "full").map((x) => [x.id, x.min, x.short ?? null])).toEqual(TALK.map(([id, , min, short]) => [id, min, short ?? null]));
  });
  it("walks the short path from the welcome to the thanks", () => {
    expect(onPath(slides, "short").map((x) => x.id)).toEqual(["welcome", "agenda", "problem", "what", "ask", "precall", "system", "evals", "start", "thanks"]);
  });
  it("has left out the old title, coverage, built-how and measured", () => {
    for (const id of ["title", "coverage", "built-how", "measured"]) expect(byId(id), id).toBeUndefined();
  });
  it("keeps planted, the table of all eight checks and the sales table among the backups", () => {
    for (const id of ["planted", "checks-all", "dict-facts"]) expect(byId(id)?.part, id).toBe("backup");
  });
  it("gives every slide its own id", () => expect(new Set(slides.map((x) => x.id)).size).toBe(slides.length));
});

// test_labels.py lists the figures that print values from the data, and each of them says so in its logo band
const labels = Object.values(import.meta.glob("../../../evals/test_labels.py", { query: "?raw", import: "default", eager: true }))[0] as string;
const DATA_FIGURES = [...(labels.match(/DATA_FIGURES = \[([^\]]*)\]/)?.[1] ?? "").matchAll(/"([^"]+)"/g)].map((m) => m[1]);

describe("what the talk's slides hold", () => {
  const byId = (id: string) => slides.find((x) => x.id === id)!;
  const layout = <L extends Native["layout"]>(id: string, l: L) => {
    const n = byId(id).native;
    expect(n?.layout, id).toBe(l);
    return n as Extract<Native, { layout: L }>;
  };

  it("opens on the airliner page, with his name, the role as the posting names it and a line that the data is made up", () => {
    const w = byId("welcome");
    expect([w.part, w.kind, w.asset, w.thumb]).toEqual(["open", "live", "hairline/title-b-airliner.html", "hairline/png/title-b.png"]);
    expect(w.byline?.slice(0, 2)).toEqual(["Chirag Lakhanpal", "Analyst/Sr Analyst, Sales AI & Innovation"]);
    expect(w.byline).toHaveLength(3);
    expect(w.byline![2]).toMatch(/^Every number in this talk comes from made-up data\.$/);
  });
  it("lists the five topics on the agenda", () => expect(byId("agenda").native).toEqual({ layout: "agenda" }));
  it("ends on a thank-you with his name, his email and a question to the room, and no link", () => {
    const t = byId("thanks");
    const { lines } = layout("thanks", "close");
    expect(t.title).toMatch(/^Thank you/);
    expect(lines.slice(0, 2)).toEqual(["Chirag Lakhanpal", "chirag.lakhanpal.cl@gmail.com"]);
    expect(lines).toHaveLength(3);
    expect(lines[2]).toMatch(/\?$/);
    texts(t).forEach((x) => expect(x).not.toMatch(/https?:|www\.|github|databricksapps|\.com\//i));
  });
  it("brings in the two slow steps a press each, and then the question to the room", () => {
    const n = layout("problem", "statement");
    expect(n.lines).toHaveLength(2);
    expect(n.ask).toMatch(/\?$/);
  });
  it("shows one sales row and one seats row, four columns each, in the order the slide names them", () => {
    expect(byId("row").native).toEqual({ layout: "table", tables: ["gold.fact_agency_sales_monthly"], columns: ["aa_revenue", "market_revenue", "aa_pax", "market_pax"] });
    expect(byId("seats").native).toEqual({ layout: "table", tables: ["gold.fact_market_capacity"], columns: ["aa_seats", "total_seats", "aa_seat_share", "source"] });
    expect(byId("dict-facts").native).toEqual({ layout: "table", tables: ["gold.fact_agency_sales_monthly"] }); // every column, as the backup
  });
  it("steps through revenue by month on its animated page, with the static figure as its thumb, as a figure that prints data", () => {
    const r = byId("revenue");
    expect([r.kind, r.asset, r.thumb, r.data]).toEqual(["animated", "11-revenue-by-month-animated.html", "export/11-revenue-by-month.png", true]);
  });
  it("names four checks on the main path, under a title that does not say checks, and all eight in the backup", () => {
    const { keys } = layout("checks", "checks");
    expect(keys).toHaveLength(4);
    expect(new Set(keys).size).toBe(4);
    keys!.forEach((k) => expect(facts.checks.map((c) => c.key), k).toContain(k));
    expect(byId("checks").title).not.toMatch(/check/i);
    expect(byId("checks-all").native).toEqual({ layout: "checks" });
  });
  it("brings in the four guardrails a press each, none tagged a possibility", () => {
    const { tiles } = layout("guardrails", "tiles");
    expect(tiles).toHaveLength(4);
    tiles.forEach((t) => expect(t.tag, t.head).toBeUndefined());
  });
  it("gives the evals two slides, Genie and the whole app and then the other three, with results and misses from the dated facts", () => {
    expect(layout("evals", "results").items).toHaveLength(2);
    expect(layout("evals-more", "results").items).toHaveLength(3);
    const said = (id: string) => new Set(texts(byId(id)).flatMap(placeholders));
    for (const k of ["genie_benchmark", "genie_benchmark_earlier", "genie_benchmark_date", "app_model_date", "app_model_right", "app_model_partly", "app_model_wrong",
      "app_model_questions", "app_model_gave_up_passed"]) expect(said("evals").has(k), `evals: {${k}}`).toBe(true);
    for (const k of ["foundry_eval_date", "foundry_quality_pages", "foundry_groundedness_misses", "foundry_shield_refused", "nightly_parity_runs", "nightly_parity_from",
      "nightly_parity_to", "nightly_parity_drift", "twins_checked"]) expect(said("evals-more").has(k), `evals-more: {${k}}`).toBe(true);
    for (const id of ["evals", "evals-more"]) layout(id, "results").items.forEach((r) => placeholders(`${r.result} ${r.miss ?? ""}`).forEach((k) => expect(known.has(k)).toBe(true)));
  });
  it("marks as data every figure that prints values from the data, and no other figure", () => {
    expect(DATA_FIGURES.length).toBeGreaterThan(5); // the list was read from test_labels.py
    for (const s of slides.filter((x) => (x.kind === "image" || x.kind === "animated") && !x.still)) {
      const figure = (s.kind === "image" ? s.asset! : s.thumb!).replace(/^export\/|\.png$/g, "");
      expect(!!s.data, `${s.id} (${figure})`).toBe(DATA_FIGURES.includes(figure));
    }
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
    expect(nextPart(slides, "full", "welcome")).toBe("problem"); // the welcome and the agenda are the open part
    expect(nextPart(slides, "short", "welcome")).toBe("problem");
    expect(nextPart(slides, "full", "know")).toBe("thanks"); // the last topic ends and the thanks begins
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

import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { NativeSlide } from "../deck/layouts";
import { knownTables } from "./deck";

// A table slide names its tables by key, and the deck has no error boundary: a key that facts.json does not describe used to
// leave facts.columns[key] undefined and throw while the slide drew.
describe("a table slide's keys", () => {
  const tableKeys = (list: Slide[]) => list.flatMap((s) => (s.native?.layout === "table" ? s.native.tables.map((key) => ({ id: s.id, key })) : []));
  const unknown = (list: Slide[]) => tableKeys(list).filter(({ key }) => knownTables([key], facts.columns).length === 0).map(({ id, key }) => `${id}: ${key}`);
  const named = ["gold.dim_market", "gold.no_such_table", "gold.dim_agency"];
  const fake: Slide = { id: "fake", part: "backup", kind: "native", title: "A fixture", min: 0, note: "", native: { layout: "table", tables: named } };

  it("are tables that facts.json describes, on every slide of the deck", () => expect(unknown(slides)).toEqual([]));
  it("catches a key that facts.json does not describe (a fixture, not the deck)", () => expect(unknown([fake])).toEqual(["fake: gold.no_such_table"]));
  it("are skipped by the guard when unknown, in order", () => expect(knownTables(named, facts.columns)).toEqual(["gold.dim_market", "gold.dim_agency"]));
  // the checks have a layout of their own, so "checks" is no table key
  it("do not take the checks", () => expect(knownTables(["checks"], facts.columns)).toEqual([]));
  it("do not stop a table slide from drawing, and the unknown one is left out", () => {
    const html = renderToStaticMarkup(createElement(NativeSlide, { slide: fake, facts }));
    expect(html).toContain("gold.dim_agency");
    expect(html).not.toContain("no_such_table");
  });
});

// A slide that names a check or a column facts.json does not hold draws without it and says nothing, so the content rules catch the name.
describe("the checks and columns a slide names", () => {
  const checkKeys = new Set(facts.checks.map((c) => c.key));
  const columns = facts.columns as Record<string, { name: string }[]>;
  const unknownNames = (list: Slide[]) => list.flatMap((s) => {
    const n = s.native;
    if (n?.layout === "checks") return (n.keys ?? []).filter((k) => !checkKeys.has(k)).map((k) => `${s.id}: check ${k}`);
    if (n?.layout === "table" && n.columns) {
      const names = new Set(n.tables.flatMap((t) => (columns[t] ?? []).map((c) => c.name)));
      return n.columns.filter((c) => !names.has(c)).map((c) => `${s.id}: column ${c}`);
    }
    return [];
  });
  const fixture = (native: Native): Slide => ({ id: "fake", part: "backup", kind: "native", title: "A fixture", min: 0, note: "", native });

  it("are ones facts.json holds, on every slide of the deck", () => expect(unknownNames(slides)).toEqual([]));
  it("catch a check or a column facts.json does not hold (fixtures, not the deck)", () => {
    expect(unknownNames([fixture({ layout: "checks", keys: ["no_repeated_rows", "no_such_check"] })])).toEqual(["fake: check no_such_check"]);
    expect(unknownNames([fixture({ layout: "table", tables: ["gold.fact_market_capacity"], columns: ["aa_seats", "aa_revenue"] })])).toEqual(["fake: column aa_revenue"]);
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

import { frameInfo, isTopic, PARTS, type FrameInfo, type PathName, type Topic } from "./deck";

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
  // the logo only: what the first and last slides of the path get, and the base the other cases change. The tracker's segments have tests of
  // their own, at the end.
  type Parts = Omit<FrameInfo, "segments">;
  const frame = (over: Partial<Parts> = {}): Parts => ({ bare: false, tracker: false, topic: null, inTopic: null, number: null, footer: false, backup: false, ...over });
  const parts = (path: PathName, id: string): Parts => {
    const { segments: _, ...rest } = frameInfo(F, path, id);
    return rest;
  };

  it("lights the topic of a topic slide, with its place among that topic's slides on the path and its number on the path", () => {
    expect(parts("full", "problem")).toEqual(frame({ tracker: true, topic: "steps", inTopic: { at: 1, of: 1 }, number: { at: 3, of: 11 }, footer: true }));
    expect(parts("full", "what")).toEqual(frame({ tracker: true, topic: "modes", inTopic: { at: 1, of: 2 }, number: { at: 4, of: 11 }, footer: true }));
    expect(parts("full", "ask")).toEqual(frame({ tracker: true, topic: "modes", inTopic: { at: 2, of: 2 }, number: { at: 5, of: 11 }, footer: true }));
    expect(parts("full", "limits")).toEqual(frame({ tracker: true, topic: "checks", inTopic: { at: 2, of: 2 }, number: { at: 9, of: 11 }, footer: true }));
    expect(parts("full", "start")).toEqual(frame({ tracker: true, topic: "aa", inTopic: { at: 1, of: 1 }, number: { at: 10, of: 11 }, footer: true }));
  });
  it("counts only the slides on the path that is on", () => {
    expect(parts("full", "system")).toEqual(frame({ tracker: true, topic: "numbers", inTopic: { at: 2, of: 2 }, number: { at: 7, of: 11 }, footer: true }));
    // pipeline is off the short path, so system is the only slide of its topic on it
    expect(parts("short", "system")).toEqual(frame({ tracker: true, topic: "numbers", inTopic: { at: 1, of: 1 }, number: { at: 6, of: 8 }, footer: true }));
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
    for (const path of ["full", "short"] as const) for (const id of ["welcome", "thanks"]) expect(parts(path, id), `${path} ${id}`).toEqual(frame());
  });
  it("shows the footer but no tracker on an open slide that is not the first", () => {
    expect(parts("full", "agenda")).toEqual(frame({ number: { at: 2, of: 11 }, footer: true }));
    expect(parts("short", "agenda")).toEqual(frame({ number: { at: 2, of: 8 }, footer: true }));
  });
  it("gives a backup slide the frame with no number and no topic lit, and a still no frame at all", () => {
    expect(parts("full", "words")).toEqual(frame({ tracker: true, footer: true, backup: true }));
    expect(parts("short", "words")).toEqual(frame({ tracker: true, footer: true, backup: true }));
    // a still is no backup to the frame, so nothing that reads the frame labels it
    expect(parts("full", "ask-still")).toEqual(frame({ bare: true }));
  });
  it("draws exactly the two stills of the real deck bare, and a still is an image slide", () => {
    expect(slides.filter((s) => frameInfo(slides, "full", s.id).bare).map((s) => s.id)).toEqual(["ask-still", "precall-still"]);
    slides.filter((s) => s.still).forEach((s) => expect(s.kind, s.id).toBe("image"));
  });
  it("lights the topic of a slide the path leaves out, but gives it no place and no number", () => {
    expect(parts("short", "pipeline")).toEqual(frame({ tracker: true, topic: "numbers", footer: true }));
    expect(parts("short", "limits")).toEqual(frame({ tracker: true, topic: "checks", footer: true }));
  });
  it("takes an unknown id for the first slide", () => expect(parts("full", "nope")).toEqual(parts("full", "welcome")));

  it("gives each topic a segment for each of its slides on the path: passed before the slide, current for it and later after it", () => {
    expect(frameInfo(F, "full", "ask").segments).toEqual({ steps: ["passed"], modes: ["passed", "current"], numbers: ["later", "later"], checks: ["later", "later"], aa: ["later"] });
    expect(frameInfo(F, "full", "start").segments).toEqual({ steps: ["passed"], modes: ["passed", "passed"], numbers: ["passed", "passed"], checks: ["passed", "passed"], aa: ["current"] });
    // the short path leaves out pipeline and the whole of Checks and misses
    expect(frameInfo(F, "short", "system").segments).toEqual({ steps: ["passed"], modes: ["passed", "passed"], numbers: ["current"], checks: [], aa: ["later"] });
  });
  it("marks no segment current on a slide the path leaves out, and none passed on a backup slide, which sits outside the path", () => {
    expect(frameInfo(F, "short", "pipeline").segments).toEqual({ steps: ["passed"], modes: ["passed", "passed"], numbers: ["later"], checks: [], aa: ["later"] });
    expect(frameInfo(F, "full", "words").segments).toEqual({ steps: ["later"], modes: ["later", "later"], numbers: ["later", "later"], checks: ["later", "later"], aa: ["later"] });
  });
  it("counts the real deck's segments along the path that is on", () => {
    for (const path of ["full", "short"] as const) {
      const topical = onPath(slides, path).filter((x) => isTopic(x.part));
      topical.forEach((x, i) => {
        const f = frameInfo(slides, path, x.id);
        const all = TOPIC_ORDER.flatMap((t) => f.segments[t]);
        expect(all, `${path} ${x.id}`).toHaveLength(topical.length);
        expect(all.filter((g) => g === "passed"), `${path} ${x.id}`).toHaveLength(i);
        expect(all.filter((g) => g === "current"), `${path} ${x.id}`).toHaveLength(1);
        expect(f.segments[x.part as Topic][f.inTopic!.at - 1], `${path} ${x.id}`).toBe("current");
      });
    }
  });
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

describe("the notes window's line for a slide with steps", () => {
  it("says which point of how many the deck is on, and counts the title alone as point 0", () => {
    expect(copy.notesPoint(2, 3)).toBe("Point 2 of 3");
    expect(copy.notesPoint(0, 3)).toBe("Point 0 of 3");
    expect(copy.notesPoint(4, 4)).not.toMatch(/[\u2013\u2014]/);
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

import { BODY, DISPLAY, HEAD, LABEL, MISS, NOTE, STEP, TITLE, UNREACHED } from "../deck/ramp";

describe("the type ramp", () => {
  const has = (cls: string, want: string) => want.split(" ").forEach((c) => expect(cls.split(" "), `${c} in ${cls}`).toContain(c));
  it("holds the size, weight, leading and color of each kind of text on a native slide", () => {
    has(TITLE, "text-[40px] font-semibold leading-[1.15] tracking-[-0.01em] text-navy");
    has(BODY, "text-[28px] font-normal leading-[1.35] text-ink");
    has(HEAD, "text-[28px] font-semibold leading-[1.35] text-ink");
    has(NOTE, "text-[20px] font-normal leading-[1.45] text-[#5a7181]");
    has(DISPLAY, "text-[56px] font-semibold leading-none text-[#006cbf]");
    has(LABEL, "font-['Geist_Mono',ui-monospace,monospace] text-[12px] font-medium uppercase tracking-[0.14em] text-[#5a7181]");
    has(MISS, "text-[20px] font-normal leading-[1.45] text-red");
  });
  it("brings an item in from 8px below and recedes its text to the muted color, in 320ms, and moves nothing under reduced motion", () => {
    has(STEP, "duration-[320ms] ease-out motion-reduce:transition-none [&[data-receded]_*]:text-[#5a7181]");
    has(UNREACHED, "invisible opacity-0 translate-y-[8px]");
  });
});

// A native slide drawn on its own, without the frame, at a step or (with none) complete.
const drawNative = (slide: Slide, step?: number) => renderToStaticMarkup(createElement(NativeSlide, { slide, facts, step }));
// The items a press brings in, one opening tag each (the elements with a data-step): its step, whether it is hidden from assistive tech,
// current or receded, and its classes.
type StepItem = { n: number; hidden: boolean; current: boolean; receded: boolean; classes: string[] };
function stepItems(html: string): StepItem[] {
  return [...html.matchAll(/<[a-z]+\s[^>]*\bdata-step="(\d+)"[^>]*>/g)].map(([tag, n]) => ({
    n: Number(n),
    hidden: tag.includes('aria-hidden="true"'),
    current: tag.includes('data-current=""'),
    receded: tag.includes('data-receded=""'),
    classes: (/\sclass="([^"]*)"/.exec(tag)?.[1] ?? "").split(/\s+/),
  }));
}
// The words a viewer can see and a screen reader can reach: the text outside every element marked aria-hidden="true", with React's
// comment markers dropped and its escapes read back.
const VOID = new Set(["area", "br", "col", "embed", "hr", "img", "input", "link", "meta", "source", "track", "wbr"]);
const ENTITIES: Record<string, string> = { "&amp;": "&", "&lt;": "<", "&gt;": ">", "&quot;": '"', "&#x27;": "'" };
function visibleText(html: string): string {
  const hidden: boolean[] = [];
  let out = "";
  for (const [, close, name, attrs, text] of html.replace(/<!--.*?-->/g, "").matchAll(/<(\/?)([a-zA-Z][\w-]*)([^>]*)>|([^<]+)/g)) {
    const under = hidden.at(-1) ?? false;
    if (text !== undefined) {
      if (!under) out += text.replace(/&[#\w]+;/g, (e) => ENTITIES[e] ?? e);
      continue;
    }
    out += " "; // a tag ends a word
    if (close) hidden.pop();
    else if (!VOID.has(name) && !attrs.endsWith("/")) hidden.push(under || attrs.includes('aria-hidden="true"'));
  }
  return out.replace(/\s+/g, " ");
}
const esc = (s: string) => s.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");

/** A stepped slide at every step from 0 to its count. Every item is drawn at every step, in order, so an item holds its place before it
 * arrives. At step k the first k show; the rest are hidden from assistive tech and carry the invisible style (never display: none);
 * item k is current and the ones before it have receded. With no step the slide is complete. */
function expectSteps(slide: Slide) {
  const count = stepCount(slide);
  const unreached = UNREACHED.split(" ");
  expect(count, slide.id).toBeGreaterThan(0);
  for (let k = 0; k <= count; k++) {
    const items = stepItems(drawNative(slide, k));
    expect(items.map((i) => i.n), `step ${k}`).toEqual(Array.from({ length: count }, (_, i) => i + 1));
    for (const it of items) {
      const at = `item ${it.n} at step ${k}`;
      const shown = it.n <= k;
      expect(it.hidden, at).toBe(!shown);
      expect(unreached.filter((c) => it.classes.includes(c)), at).toEqual(shown ? [] : unreached);
      expect(it.classes, at).not.toContain("hidden");
      expect(it.current, at).toBe(it.n === k);
      expect(it.receded, at).toBe(it.n < k);
    }
  }
  expect(drawNative(slide)).toBe(drawNative(slide, count));
}

describe("native layouts, one item a press", () => {
  const nat = (native: Native): Slide => ({ id: "fixture", part: "backup", kind: "native", title: "A fixture", min: 0, note: "", native });
  const tile = (head: string, tag?: "Possibility"): Tile => ({ head, body: `${head} in a sentence.`, tag });

  it("bring a statement's lines in one a press, and the question to the room last, set apart in a callout", () => {
    const slide = nat({ layout: "statement", lines: ["The first line.", "The second line."], ask: "A question for the room?" });
    expectSteps(slide);
    const zero = drawNative(slide, 0);
    expect(zero).toContain("The first line."); // drawn, so it holds its place
    expect(visibleText(zero)).not.toContain("The first line.");
    expect(visibleText(zero)).toContain("A fixture"); // the title shows on arrival
    const one = visibleText(drawNative(slide, 1));
    expect(one).toContain("The first line.");
    expect(one).not.toContain("The second line.");
    const html = drawNative(slide);
    const ask = stepItems(html).at(-1)!;
    expect(ask.n).toBe(3);
    expect(ask.classes).toEqual(expect.arrayContaining(["bg-tint", "border-l-4", "border-blue"]));
    expect(html.indexOf("A question for the room?")).toBeGreaterThan(html.lastIndexOf("</ul>"));
  });
  it("hold a step outside the slide's steps to its first or last, and say on the slide's root where it stands", () => {
    const slide = nat({ layout: "statement", lines: ["One.", "Two."] });
    expect(drawNative(slide, 9)).toBe(drawNative(slide, 2));
    expect(drawNative(slide, -1)).toBe(drawNative(slide, 0));
    expect(drawNative(slide, 1)).toContain('data-step-current="1" data-step-count="2"');
  });
  it("bring tiles in one a press, a possibility with its label", () => {
    const slide = nat({ layout: "tiles", tiles: [tile("Alpha"), tile("Beta", "Possibility"), tile("Gamma"), tile("Delta")] });
    expectSteps(slide);
    const two = visibleText(drawNative(slide, 2));
    expect(two).toContain("Beta in a sentence.");
    expect(two).toContain("Possibility");
    expect(two).not.toContain("Gamma");
  });
  it("bring a table slide's tables in one a press, and keep only the columns it names", () => {
    expectSteps(nat({ layout: "table", tables: ["gold.dim_agency", "gold.dim_market"] }));
    const tables = ["gold.fact_agency_sales_monthly", "gold.fact_market_capacity"];
    const html = drawNative(nat({ layout: "table", tables, columns: ["aa_revenue", "aa_seat_share"] }));
    expect(html).toContain(">aa_revenue<");
    expect(html).toContain(">aa_seat_share<");
    for (const name of ["agency_id", "market_id", "sales_month", "aa_pax", "total_seats", "source"]) expect(html, name).not.toContain(`>${name}<`);
    expect(visibleText(html)).toContain("$80,582.47"); // the example, with its unit
    expect(visibleText(drawNative(nat({ layout: "table", tables })))).toContain("total_seats"); // and every column with none named
  });
  it("keep a table slide's columns in the order the slide names them, which may not be the table's", () => {
    const html = drawNative(nat({ layout: "table", tables: ["gold.fact_agency_sales_monthly"], columns: ["aa_revenue", "market_revenue", "aa_pax", "market_pax"] }));
    const at = ["aa_revenue", "market_revenue", "aa_pax", "market_pax"].map((name) => html.indexOf(`>${name}<`));
    expect(at.every((i) => i > 0)).toBe(true);
    expect(at).toEqual([...at].sort((a, b) => a - b));
  });
  it("bring the checks a slide names in one a press, in its order, each with what it guards against", () => {
    const keys = ["sales_have_seats", "no_repeated_rows"];
    const slide = nat({ layout: "checks", keys });
    expectSteps(slide);
    const text = visibleText(drawNative(slide));
    for (const c of facts.checks) {
      expect(text.includes(c.name), c.key).toBe(keys.includes(c.key));
      expect(text.includes(c.why), c.key).toBe(keys.includes(c.key));
    }
    const name = (key: string) => facts.checks.find((c) => c.key === key)!.name;
    expect(text.indexOf(name("sales_have_seats"))).toBeLessThan(text.indexOf(name("no_repeated_rows")));
  });
  it("show all eight checks at once when the slide names none", () => {
    const html = drawNative(nat({ layout: "checks" }), 0);
    expect(stepItems(html)).toEqual([]);
    expect(facts.checks).toHaveLength(8);
    facts.checks.forEach((c) => expect(visibleText(html), c.key).toContain(c.name));
  });
  it("print each check's values with their units in the table of all of them", () => {
    const text = visibleText(drawNative(nat({ layout: "checks" })));
    for (const shown of ["$4,920.87", "Sep 2026 and Sep 2026", "3,000"]) expect(text).toContain(shown);
    for (const raw of ["4920.87", "2026-09-01", "3000"]) expect(text).not.toContain(raw);
  });
  it("say on the layout's box how far it is zoomed, full size when it fits", () => {
    expect(drawNative(nat({ layout: "statement", lines: ["One."] }))).toContain('data-fit-zoom="1"');
  });
  it("bring results in one a press: the head, the body, the result as a display number and the miss in red", () => {
    const items: Result[] = [
      { head: "Head one", body: "Who grades one.", result: "20 of 20", miss: "The miss of one." },
      { head: "Head two", body: "Who grades two.", result: "15 of 20" },
    ];
    const slide = nat({ layout: "results", items });
    expectSteps(slide);
    const html = drawNative(slide);
    const styled = (cls: string, text: string) => expect(html, `${text} in ${cls}`).toMatch(new RegExp(`class="[^"]*${esc(cls)}[^"]*">${esc(text)}<`));
    styled(HEAD, "Head one");
    styled(NOTE, "Who grades one.");
    styled(DISPLAY, "20 of 20");
    styled(MISS, "The miss of one.");
    styled(DISPLAY, "15 of 20");
    expect(html.match(new RegExp(esc(MISS), "g"))).toHaveLength(1); // the second result has no miss
  });
  it("bring the agenda's five topics in one a press, each with its line", () => {
    const slide = nat({ layout: "agenda" });
    expectSteps(slide);
    expect(stepCount(slide)).toBe(TOPIC_ORDER.length);
    const all = visibleText(drawNative(slide));
    TOPIC_ORDER.forEach((t) => {
      expect(all).toContain(TOPICS[t].name);
      expect(all).toContain(TOPICS[t].line);
    });
    const two = visibleText(drawNative(slide, 2));
    expect(two).toContain(TOPICS.modes.line);
    expect(two).not.toContain(TOPICS.numbers.name);
  });
  it("show the close at once, with no steps", () => {
    const html = drawNative(nat({ layout: "close", lines: ["Thank you.", "Questions are welcome."] }), 0);
    expect(stepItems(html)).toEqual([]);
    expect(visibleText(html)).toContain("Thank you.");
    expect(visibleText(html)).toContain("Questions are welcome.");
  });
  it("show a demo's button from step 0, and bring its lines in one a press", () => {
    const ask = nat({ layout: "demo", demo: { kind: "ask", question: "Why is it down?" }, lines: ["Watch the split.", "Click a number."] });
    expectSteps(ask);
    const zero = visibleText(drawNative(ask, 0));
    expect(zero).toContain(copy.askLive);
    expect(zero).toContain("Why is it down?");
    expect(zero).not.toContain("Watch the split.");
    expect(visibleText(drawNative(nat({ layout: "demo", demo: { kind: "precall" }, lines: ["One."] }), 0))).toContain(copy.openPrecall);
  });
  it("draw the title, and do not throw, for a layout with nothing in it", () => {
    for (const native of [{ layout: "results", items: [] }, { layout: "tiles", tiles: [] }, { layout: "statement", lines: [] }] as Native[]) {
      expect(visibleText(drawNative(nat(native))), native.layout).toContain("A fixture");
    }
  });
  it("draw every native slide of the deck at its first step and complete", () => {
    for (const s of slides.filter((x) => x.native)) {
      expect(() => drawNative(s, 0), s.id).not.toThrow();
      expect(visibleText(drawNative(s)), s.id).toContain(fill(s.title, facts));
    }
  });
});

import { copy } from "../copy";
import { DeckFrame } from "../deck/Frame";
import { showPage, SlideView } from "../deck/SlideView";

// The frame drawn on its own around a stand-in for a slide, from the frame info of the talk in miniature. A topic's column is cut out of the
// markup by its data-topic attribute.
describe("the frame's strips", () => {
  const draw = (info: FrameInfo, label = "A label") => renderToStaticMarkup(createElement(DeckFrame, { info, label, children: createElement("p", null, "The slide") }));
  const times = (html: string, text: string) => html.split(text).length - 1;
  const column = (html: string, t: Topic) => html.split(`data-topic="${t}"`)[1]?.split("data-topic=")[0] ?? "";
  const segments = (html: string, t: Topic) => [...column(html, t).matchAll(/data-segment="(\w+)"/g)].map((m) => m[1]);

  it("names each topic once, lights the slide's topic, and draws a segment for each topic slide on the path with this one marked", () => {
    const html = draw(frameInfo(F, "full", "ask"));
    expect(html).toContain("The slide");
    expect(html).toContain('src="/aa-logo.svg"');
    TOPIC_ORDER.forEach((t) => expect(times(html, `>${TOPICS[t].name}<`), t).toBe(1));
    expect(times(html, 'aria-current="step"')).toBe(1);
    expect(column(html, "modes")).toMatch(/aria-current="step"[^>]*>Ask and Delegate</);
    expect(Object.fromEntries(TOPIC_ORDER.map((t) => [t, segments(html, t)]))).toEqual({
      steps: ["passed"], modes: ["passed", "current"], numbers: ["later", "later"], checks: ["later", "later"], aa: ["later"],
    });
    expect(html).toContain(">5 / 11<");
    expect(html).toContain(">A label<");
  });
  it("draws no topic names without the tracker, and no footer without the footer", () => {
    const agenda = draw(frameInfo(F, "full", "agenda"));
    TOPIC_ORDER.forEach((t) => expect(agenda, t).not.toContain(TOPICS[t].name));
    expect(agenda).not.toContain("data-segment");
    expect(agenda).toContain(">2 / 11<");
    const welcome = draw(frameInfo(F, "full", "welcome"));
    expect(welcome).toContain('src="/aa-logo.svg"');
    TOPIC_ORDER.forEach((t) => expect(welcome, t).not.toContain(TOPICS[t].name));
    expect(welcome).not.toContain('data-frame="footer"');
    expect(welcome).not.toContain("A label");
  });
  it("says Backup in place of a number on a backup slide, with no topic lit", () => {
    const html = draw(frameInfo(F, "full", "words"));
    expect(html).toContain(">Backup<");
    expect(html).not.toMatch(/\d+ \/ \d+/);
    expect(html).not.toContain("aria-current");
    TOPIC_ORDER.forEach((t) => expect(times(html, `>${TOPICS[t].name}<`), t).toBe(1));
  });
  it("leaves the number out on a slide the path leaves out", () => {
    const html = draw(frameInfo(F, "short", "pipeline"));
    expect(html).toContain('data-frame="footer"');
    expect(html).not.toMatch(/\d+ \/ \d+/);
    expect(html).not.toContain(">Backup<");
  });
});

describe("a slide in its frame", () => {
  const byId = (id: string) => slides.find((s) => s.id === id)!;
  const view = (slide: Slide, frame: FrameInfo = frameInfo(slides, "full", slide.id), step?: number) =>
    renderToStaticMarkup(createElement(SlideView, { slide, frame, arrival: "forward", frameRef: { current: null }, facts, onDemo: () => {}, step }));

  it("says Synthetic data on a slide that shows data, and the talk's title on one that does not", () => {
    expect(copy.deckFooter).toBe("Fairshare: sales answers you can check");
    expect(copy.deckFooterData).toBe("Synthetic data");
    expect(view(byId("checks"))).toContain(`>${copy.deckFooterData}<`);
    expect(view(byId("problem"))).toContain(`>${copy.deckFooter}<`);
    expect(view(byId("problem"))).not.toContain(copy.deckFooterData);
  });
  it("draws a still bare, with no frame", () => {
    const html = view(byId("ask-still"));
    expect(html).not.toContain("data-frame");
    expect(html).not.toContain("/aa-logo.svg");
  });
  it("keeps an animated slide's finished figure out of sight until its frame has had FRAME_FALLBACK_MS to get ready, and a live slide's still in view", () => {
    const thumb = (html: string) => html.match(/<img[^>]*data-thumb[^>]*>/)?.[0] ?? "";
    expect(thumb(view(byId("pipeline")))).toMatch(/visibility:\s*hidden/);
    expect(thumb(view(byId("query-opener")))).not.toBe("");
    expect(thumb(view(byId("query-opener")))).not.toMatch(/visibility:\s*hidden/);
  });
  it("draws a native slide and a figure inside the frame", () => {
    for (const id of ["problem", "revenue"]) expect(view(byId(id)), id).toContain('data-frame="header"');
  });
  it("hands its step to a native slide, which shows complete without one", () => {
    const problem = byId("problem");
    const shown = (step?: number) => stepItems(view(problem, undefined, step)).filter((i) => !i.hidden).length;
    expect(shown(1)).toBe(1);
    expect(shown()).toBe(stepCount(problem));
  });

  it("draws a live slide's title and byline lines at the bottom when it has a byline, and nothing there when it has none", () => {
    const welcome = byId("welcome");
    const [name, role, data] = welcome.byline!.map(esc);
    expect(view(welcome)).toMatch(new RegExp(`data-byline[^>]*>.*${esc(welcome.title)}.*${name}.*${role.replace(/&/g, "&amp;")}.*${data}`));
    const plain = { ...welcome, byline: undefined };
    expect(view(plain, frameInfo([plain], "full", plain.id))).not.toContain("data-byline");
    // two lines alike still draw as two
    const twice = { ...welcome, byline: ["The same line", "The same line"] };
    expect(view(twice, frameInfo([twice], "full", twice.id)).split("The same line")).toHaveLength(3);
  });
  it("hides a live page's logo and readout, and its caption only when the slide has a byline", () => {
    // a stand-in for the hairline page in the frame: the parts showPage reads, each with the display it ends up with
    const page = () => {
      const parts: Record<string, { style: { display: string; setProperty: (p: string, v: string) => void } }> = {};
      for (const sel of [".frame", "#read", ".brand", ".caption"]) {
        const style = { display: "", setProperty: (p: string, v: string) => void (p === "display" && (style.display = v)) };
        parts[sel] = { style };
      }
      const doc = { querySelector: (sel: string) => parts[sel.trim()] ?? null };
      const hidden = () => Object.keys(parts).filter((sel) => parts[sel].style.display === "none").sort();
      return { frame: { contentDocument: doc as unknown as Document }, hidden };
    };
    const plain = page();
    expect(showPage(plain.frame, false)).toBe(true);
    expect(plain.hidden()).toEqual(["#read", ".brand"]);
    const withByline = page();
    expect(showPage(withByline.frame, true)).toBe(true);
    expect(withByline.hidden()).toEqual(["#read", ".brand", ".caption"]);
    expect(showPage({ contentDocument: null }, true)).toBe(false); // a frame that failed keeps the thumb
  });
});

import { outlineArrival, outlineParts } from "./deck";

describe("the notes window's outline", () => {
  it("lists only the parts that have slides, in the order of the talk", () => {
    expect(outlineParts(slides)).toEqual(["open", ...TOPIC_ORDER, "close", "backup"]);
    expect(outlineParts(S)).toEqual(["open", "modes", "numbers", "aa", "backup"]); // the miniature has no steps, checks or close slides
  });
  it("lands a jump on a backup slide complete, and on a slide of the path on its first step, wherever the deck stands", () => {
    const byId = (id: string) => slides.find((x) => x.id === id)!;
    expect(arrivalStep(byId("words"), outlineArrival(byId("words")))).toBe(stepCount(byId("words")));
    expect(stepCount(byId("words"))).toBeGreaterThan(0);
    for (const id of ["problem", "guardrails", "start"]) expect(arrivalStep(byId(id), outlineArrival(byId(id))), id).toBe(0);
  });
});
