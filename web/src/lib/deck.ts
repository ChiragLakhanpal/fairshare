// The /present deck's rules: which slide a press reaches on the full or the short path, which slide a URL hash names, what
// the frame draws around a slide (the topic tracker and the slide number), and the handoff on a stepped slide, where a press
// steps the framed diagram, or the native slide's own steps, until the last one and then moves the deck. frameState, sendKey
// and arrive are the only three that touch a frame, and all read it inside try and catch, because an aborted or blocked frame
// cannot be read. The text helpers fill a slide's {placeholders} from facts.json and read its words for the content rules.
// The topics and the parts are at the top; the keys, the clock and the messages between the deck and its notes window are
// at the end. The pure parts are tested in deck.test.ts.

/** The five topics the talk is told in, in the order of TOPIC_ORDER. */
export type Topic = "steps" | "modes" | "numbers" | "checks" | "aa";
/** What a slide belongs to: the welcome and the agenda (open), a topic, the thanks (close) or the backup slides. */
export type Part = "open" | Topic | "close" | "backup";
export type Kind = "image" | "live" | "animated" | "native";
export type PathName = "full" | "short";
/** still: a screenshot of the app itself, drawn edge to edge. The app has its own top bar, so a still gets no frame (frameInfo).
 * data: a figure that prints values from the data. byline: lines a live slide shows under its title, in place of its page's caption. */
export type Slide = { id: string; part: Part; kind: Kind; title: string; min: number; short?: number; asset?: string; thumb?: string; still?: boolean; data?: boolean; byline?: string[]; native?: Native; note: string };
export type Demo = { kind: "ask"; question: string } | { kind: "precall" } | { kind: "dashboard" };
/** The demos the deck jumps into the app for. The dashboard only opens in a new tab, so it needs no jump. */
export type Jump = Exclude<Demo["kind"], "dashboard">;
export type Tile = { head: string; body: string; tag?: "Possibility" };
/** One test or evaluation: its head, a body saying what it tests and who grades it, its result and, where it has one, its miss. */
export type Result = { head: string; body: string; result: string; miss?: string };
/** A native slide's layout. Its steps (stepCount) are one press each: a statement's lines and then its question, a tile, a table, a check, a
 * result, a topic of the agenda, a demo line. */
export type Native =
  | { layout: "statement"; lines: string[]; ask?: string } // ask: the question to the room, after the last line
  | { layout: "tiles"; tiles: Tile[] }
  | { layout: "table"; tables: string[]; columns?: string[] } // keys of facts.columns; columns keeps only those column names, in its own order
  | { layout: "checks"; keys?: string[] } // keys of facts.checks; none means all of them, shown at once
  | { layout: "results"; items: Result[] }
  | { layout: "agenda" } // the five topics, name and line
  | { layout: "close"; lines: string[] }
  | { layout: "demo"; demo: Demo; lines: string[] };
/** What fill() reads from facts.json: the display string of every fact and every dated fact. */
export type Facts = { facts: Record<string, { display: string }>; dated: Record<string, { display: string }> };
/** All of facts.json that a slide shows: the facts, plus the columns of each table (each with an example that carries its unit) and the basic
 * checks (each with a snake_case key, a why, one plain sentence on what the check guards against, and its values as the query returned them
 * and as a slide prints them, with their units). */
export type DeckFacts = Facts & {
  columns: Record<string, { name: string; meaning: string; example: string }[]>;
  checks: { key: string; name: string; why: string; expected: unknown; actual: unknown; ok: boolean; display: { expected: string; actual: string } }[];
};

/** The topics in the order of the talk. */
export const TOPIC_ORDER: readonly Topic[] = ["steps", "modes", "numbers", "checks", "aa"];

/** Each topic's name, which the tracker and the outline show, and its line, which the agenda shows. */
export const TOPICS: Record<Topic, { name: string; line: string }> = {
  steps: { name: "Two slow steps", line: "What I heard in round one about share questions and pre-call packs." },
  modes: { name: "Ask and Delegate", line: "The app answers a share question and drafts a pre-call pack, live." },
  numbers: { name: "Where the numbers come from", line: "The data behind the seven numbers, and why Harbor fell in September." },
  checks: { name: "Checks and misses", line: "How the app checks each number, what the tests found, and what it can't do yet." },
  aa: { name: "Starting at AA", line: "The same layers on AA's own data, and the first four steps." },
};

/** The name of each part: the heading of its section in the notes window's outline, which lists the parts in this order. The frame's footer
 * says the backup part's name in place of a slide number. */
export const PARTS: Record<Part, string> = {
  open: "Welcome",
  steps: TOPICS.steps.name,
  modes: TOPICS.modes.name,
  numbers: TOPICS.numbers.name,
  checks: TOPICS.checks.name,
  aa: TOPICS.aa.name,
  close: "Thank you",
  backup: "Backup",
};

/** Whether a part is one of the five topics, and not the welcome, the thanks or a backup. */
export function isTopic(p: Part): p is Topic {
  return Object.hasOwn(TOPICS, p);
}

/** The parts the notes window's outline lists, in the order of PARTS: only those with a slide, so no heading stands alone. */
export function outlineParts(slides: Slide[]): Part[] {
  return (Object.keys(PARTS) as Part[]).filter((p) => slides.some((s) => s.part === p));
}

/** A slide on the path as the tracker marks it, from where the slide on the screen stands: shown before it, the slide itself, or still
 * to come. */
export type Segment = "passed" | "current" | "later";

/** What the frame draws around a slide. bare: nothing at all, not even the logo (a still). tracker: the five topic names across the top, with
 * topic lit and inTopic marking which of that topic's slides on the path is showing; segments holds a mark for each topic's slides on the path,
 * in order. footer: the line along the bottom, with the slide's number on the path that is on (null off it, and on the first and last slides)
 * or, when backup is true, the word Backup in its place. */
export type FrameInfo = {
  bare: boolean;
  tracker: boolean;
  topic: Topic | null;
  inTopic: { at: number; of: number } | null;
  segments: Record<Topic, Segment[]>;
  number: { at: number; of: number } | null;
  footer: boolean;
  backup: boolean;
};

/** The frame for a slide, on the path that is on. The first and last slides of the path (the welcome and the thanks) get the logo only, an open
 * slide after the first (the agenda) the footer without the tracker, a backup slide the tracker with no topic lit and the footer, and a still
 * nothing. The place in the topic and the number count the slides on the path, so a slide the path leaves out keeps its topic lit and has
 * neither. The segments mark the path's slides by their place in the deck: the ones before this slide passed, this one current, the rest
 * later; a backup slide sits outside the path, so every segment is later. An unknown id takes the first slide. */
export function frameInfo(slides: Slide[], path: PathName, id: string): FrameInfo {
  const s = slides.find((x) => x.id === id) ?? slides[0];
  const backup = s.part === "backup";
  const line = onPath(slides, path);
  const here = slides.indexOf(s);
  const mark = (x: Slide): Segment => (x === s ? "current" : !backup && slides.indexOf(x) < here ? "passed" : "later");
  const segments = Object.fromEntries(TOPIC_ORDER.map((t) => [t, line.filter((x) => x.part === t).map(mark)])) as Record<Topic, Segment[]>;
  if (s.still) return { bare: true, tracker: false, topic: null, inTopic: null, segments, number: null, footer: false, backup: false };
  const at = line.indexOf(s);
  const ends = at >= 0 && (at === 0 || at === line.length - 1);
  const topic = isTopic(s.part) ? s.part : null;
  const group = line.filter((x) => x.part === s.part);
  return {
    bare: false,
    tracker: !ends && s.part !== "open" && s.part !== "close",
    topic,
    inTopic: topic && at >= 0 ? { at: group.indexOf(s) + 1, of: group.length } : null,
    segments,
    number: at >= 0 && !ends ? { at: at + 1, of: line.length } : null,
    footer: !ends,
    backup,
  };
}

/** The slides a talk walks through, in order: every slide but the backup ones, and on the short path only those with a
 * short-path time. */
export function onPath(slides: Slide[], path: PathName): Slide[] {
  return slides.filter((s) => s.part !== "backup" && (path === "full" || s.short !== undefined));
}

/** The slide one press away. On the path it steps along it and stops at both ends; a backup slide steps among the backup
 * slides; a main slide off the short path goes to the nearest path slide in that direction. An unknown id goes to the
 * first slide. */
export function move(slides: Slide[], path: PathName, id: string, dir: 1 | -1): string {
  const line = onPath(slides, path);
  const at = slides.findIndex((s) => s.id === id);
  if (at < 0) return (line[0] ?? slides[0]).id;
  const here = slides[at];
  const group = here.part === "backup" ? slides.filter((s) => s.part === "backup") : line;
  const i = group.indexOf(here);
  if (i >= 0) return group[Math.min(group.length - 1, Math.max(0, i + dir))].id;
  // off the short path: the nearest path slide in the direction of the press, by position in the deck
  const near = dir === 1 ? line.find((s) => slides.indexOf(s) > at) : [...line].reverse().find((s) => slides.indexOf(s) < at);
  return (near ?? here).id;
}

/** The slide a URL hash names ("#pipeline"), or the first slide when it names none. */
export function fromHash(slides: Slide[], hash: string): string {
  const id = hash.replace(/^#/, "");
  return (slides.find((s) => s.id === id) ?? slides[0]).id;
}

/** The question the Ask demo puts in the app's box, from the one slide that asks a question, or null when none does. Like
 * every slide text it may hold {placeholders}, which fill() fills. */
export function askQuestion(slides: Slide[]): string | null {
  for (const s of slides) if (s.native?.layout === "demo" && s.native.demo.kind === "ask") return s.native.demo.question;
  return null;
}

/** Whether a press on a stepped slide steps within it or moves the deck: forward steps until its last step, back until
 * step 0. "diagram" is a step within the slide, an animated slide's framed diagram or a native slide's own steps. A frame
 * with no steps, or steps it could not read (NaN), counts as zero steps. */
export function pressTarget(current: number, count: number, dir: 1 | -1): "diagram" | "deck" {
  const steps = count > 0 ? count : 0; // NaN > 0 is false
  const at = current > 0 ? Math.min(current, steps) : 0;
  return (dir === 1 ? at < steps : at > 0) ? "diagram" : "deck";
}

/** How many presses a native slide takes to show all of it: one for each step of its layout (see Native), none for a layout shown at once. A
 * figure, a live page and a slide with no layout have none here; an animated slide's frame counts its own steps. */
export function stepCount(s: Slide): number {
  const n = s.native;
  if (!n) return 0;
  switch (n.layout) {
    case "statement": return n.lines.length + (n.ask ? 1 : 0);
    case "tiles": return n.tiles.length;
    case "table": return n.tables.length;
    case "checks": return n.keys?.length ?? 0;
    case "results": return n.items.length;
    case "agenda": return TOPIC_ORDER.length;
    case "close": return 0;
    case "demo": return n.lines.length;
  }
}

/** How a slide comes onto the screen: a press or a jump forward, one back, or the page loading on it (a reload, or the way back from a
 * demo). */
export type Arrival = "forward" | "backward" | "load";

/** The step a stepped slide arrives on: 0 going forward, so the title shows alone, and the last step going back or when the page loads on
 * the slide (a reload, or the way back from a demo), so the slide shows complete. */
export function arrivalStep(s: Slide, how: Arrival): number {
  return how === "forward" ? 0 : stepCount(s);
}

/** How a jump from the notes window's outline arrives, wherever the deck stands: a backup slide as going back would bring it, complete, since a
 * question pulls it up to be read at once; a slide of the path as going forward would, on its first step, so the presenter walks it again. */
export function outlineArrival(s: Slide): "forward" | "backward" {
  return s.part === "backup" ? "backward" : "forward";
}

/** How long an animated slide waits for its frame's controller before it shows the finished figure (its thumb, the static
 * page's PNG) in the frame's place. Until then the slide shows nothing of the figure, so no step shows before its press. A
 * frame that gets ready after that has had the room looking at the whole figure, so it arrives whole (arrivalKey). */
export const FRAME_FALLBACK_MS = 3000;

/** The key a framed diagram gets when its slide arrives: Home (step 0, which also stops the reveal from playing on its
 * own) going forward, and End (the whole figure) going back, after a load (a reload, or the way back from a demo), once
 * the finished figure has shown in the frame's place (FRAME_FALLBACK_MS), and under reduced motion, where Home would still
 * hide most of the figure because the controller's keys ignore reduced motion. */
export function arrivalKey(how: Arrival, elapsedMs: number, reduced: boolean): "Home" | "End" {
  return how !== "forward" || reduced || elapsedMs > FRAME_FALLBACK_MS ? "End" : "Home";
}

function motionRoot(f: HTMLIFrameElement): HTMLElement | null {
  try {
    return f.contentDocument?.querySelector<HTMLElement>("[data-motion-root]") ?? null;
  } catch {
    return null; // an aborted or blocked frame cannot be read
  }
}

/** Where the framed diagram stands, or null until SlideView has marked the frame ready (data-ready="1"). */
export function frameState(f: HTMLIFrameElement | null): { current: number; count: number } | null {
  if (!f || f.getAttribute("data-ready") !== "1") return null;
  const root = motionRoot(f);
  return root ? { current: Number(root.dataset.stepCurrent), count: Number(root.dataset.stepCount) } : null;
}

/** A key for the framed diagram's controller, which listens on its [data-motion-root], not on the document: a keydown
 * that does not bubble, built with the frame's own KeyboardEvent. */
export function sendKey(f: HTMLIFrameElement, key: "Home" | "End" | "ArrowRight" | "ArrowLeft"): void {
  try {
    const root = motionRoot(f);
    root?.dispatchEvent(new (f.contentWindow as typeof window).KeyboardEvent("keydown", { key, bubbles: false, cancelable: true }));
  } catch {
    // a frame that went away between the read and the key: the figure under it stays, and the next press moves the deck
  }
}

/** What a slide's arrival sends its framed diagram (arrivalKey). End shows the whole figure, so with it every animation and transition of the
 * frame's page is finished too: its parts' assembly ends at once and does not play out in front of the room. The first arrival and a page the
 * browser restores from its cache both come through here. An animation that cannot end (an endless one) keeps running, and the rest still finish. */
export function arrive(f: HTMLIFrameElement, key: "Home" | "End"): void {
  sendKey(f, key);
  if (key !== "End") return;
  try {
    f.contentDocument?.getAnimations().forEach((a) => {
      try {
        a.finish();
      } catch {
        // an endless animation cannot finish
      }
    });
  } catch {
    // a frame that went away or cannot be read: the figure under it stays
  }
}

/** A {placeholder}: anything between braces, so a typo cannot pass for plain text. */
const PLACEHOLDER = /\{([^{}]*)\}/g;

/** The strings a layout holds. A table's cells and the checks come from facts.json, not from the slide, so only a table's keys are here, and
 * the agenda's words are the TOPICS'. */
function layoutTexts(n: Native): string[] {
  switch (n.layout) {
    case "statement": return [...n.lines, ...(n.ask ? [n.ask] : [])];
    case "tiles": return n.tiles.flatMap((t) => [t.head, t.body, ...(t.tag ? [t.tag] : [])]);
    case "table": return n.tables;
    case "results": return n.items.flatMap((r) => [r.head, r.body, r.result, ...(r.miss ? [r.miss] : [])]);
    case "close": return n.lines;
    case "demo": return [...(n.demo.kind === "ask" ? [n.demo.question] : []), ...n.lines];
    case "checks":
    case "agenda": return [];
  }
}

/** Every string a slide shows: its title, its byline and what its layout holds. */
function shown(s: Slide): string[] {
  return [s.title, ...(s.byline ?? []), ...(s.native ? layoutTexts(s.native) : [])];
}

/** Every string a slide shows, plus its note: what the content rules read. */
export function texts(s: Slide): string[] {
  return [...shown(s), s.note];
}

/** Whether a slide shows numbers from the data, so its footer says the data is synthetic: a table or the checks, a figure marked as data, or
 * a text that holds one of the facts. A dated fact is a result kept in a file, not a query on the data, and a note is not on the slide. */
export function showsData(s: Slide, facts: Facts): boolean {
  const layout = s.native?.layout;
  return !!s.data || layout === "table" || layout === "checks" || shown(s).flatMap(placeholders).some((k) => Object.hasOwn(facts.facts, k));
}

/** The text with each {key} replaced by that fact's display string, from the facts or the dated facts. An unknown key
 * throws, so a slide never shows a raw placeholder. */
export function fill(text: string, facts: Facts): string {
  return text.replace(PLACEHOLDER, (_, key: string) => {
    const f = Object.hasOwn(facts.facts, key) ? facts.facts[key] : Object.hasOwn(facts.dated, key) ? facts.dated[key] : undefined;
    if (!f) throw new Error(`no fact for {${key}}`);
    return f.display;
  });
}

/** The keys of the placeholders in a text, in order. */
export function placeholders(text: string): string[] {
  return [...text.matchAll(PLACEHOLDER)].map((m) => m[1]);
}

/** The digits a text may show outside a placeholder (Global Constraints): the years 2025 and 2026, the quarters, "figure
 * NN", and the names gpt-5-mini, Qwen3-Next, T-100, Dynamics 365, Microsoft 365 and "6 am". */
const ALLOWED = [/\b202[56]\b/g, /\bQ[1-4]\b/g, /\bfigure \d\d\b/gi, /\bgpt-5-mini\b/g, /\bQwen3-Next\b/g, /\bT-100\b/g, /\b(?:Dynamics|Microsoft) 365\b/g, /\b6 am\b/g];

/** The numbers typed by hand: digits left after removing the placeholders and the allowlist. */
export function bareNumbers(text: string): string[] {
  const rest = ALLOWED.reduce((t, re) => t.replace(re, " "), text.replace(PLACEHOLDER, " "));
  return rest.match(/\d+(?:[.,]\d+)*/g) ?? [];
}

/** The table keys a table slide can draw: the tables facts.json holds columns for (the checks have a layout of their own). An unknown key
 * is left out, because the deck has no error boundary and a slide that throws goes blank; deck.test.ts holds slides.ts to known keys. */
export function knownTables(keys: string[], columns: DeckFacts["columns"]): string[] {
  return keys.filter((k) => Object.hasOwn(columns, k));
}

/** How many words a text has, split on runs of white space. */
export function words(text: string): number {
  return text.split(/\s+/).filter(Boolean).length;
}

/** The fewest monospaced characters a line needs to hold a text in two lines, breaking only at its spaces: the longest word, or more when the
 * words do not share two lines evenly. A table slide sizes its example column by it. */
export function twoLines(text: string): number {
  const words = text.split(/\s+/).filter(Boolean);
  for (let width = Math.max(0, ...words.map((w) => w.length)); width < text.length; width++) {
    let lines = 1;
    let used = 0;
    for (const w of words) {
      if (used === 0) used = w.length;
      else if (used + 1 + w.length <= width) used += 1 + w.length;
      else {
        lines += 1;
        used = w.length;
      }
    }
    if (lines <= 2) return width;
  }
  return text.length;
}

/** What a key does, in the deck or in the notes window. Clickers send Page Up and Page Down. A key held with Command,
 * Control or Option stays the browser's (Command P prints, Control Command F goes full screen). */
export type Action = "next" | "prev" | "first" | "last" | "part" | "notes";
const KEYS_TO_ACTIONS: Record<string, Action> = {
  ArrowRight: "next", " ": "next", PageDown: "next", ArrowLeft: "prev", PageUp: "prev", Home: "first", End: "last", s: "part", p: "notes",
};

/** The action a key press asks for, or null for a key the deck leaves alone. Letters work in either case. */
export function keyAction(e: { key: string; metaKey?: boolean; ctrlKey?: boolean; altKey?: boolean }): Action | null {
  if (e.metaKey || e.ctrlKey || e.altKey) return null;
  const key = e.key.length === 1 ? e.key.toLowerCase() : e.key;
  return Object.hasOwn(KEYS_TO_ACTIONS, key) ? KEYS_TO_ACTIONS[key] : null;
}

/** The first slide of the next part on the path: the first path slide after this one in a later part. It stays put on
 * the last part, and on a backup slide, because the backup slides come after the whole path. An unknown id goes to the
 * first slide. */
export function nextPart(slides: Slide[], path: PathName, id: string): string {
  const line = onPath(slides, path);
  const at = slides.findIndex((s) => s.id === id);
  if (at < 0) return (line[0] ?? slides[0]).id;
  return (line.find((s) => slides.indexOf(s) > at && s.part !== slides[at].part) ?? slides[at]).id;
}

/** Where an action takes the deck: next and prev one press along the path (move), first and last to the ends of the
 * main path, part to the next part. */
export function destination(slides: Slide[], path: PathName, id: string, action: Exclude<Action, "notes">): string {
  if (action === "next" || action === "prev") return move(slides, path, id, action === "next" ? 1 : -1);
  if (action === "part") return nextPart(slides, path, id);
  const main = onPath(slides, "full");
  return (action === "first" ? main[0] : main[main.length - 1]).id;
}

/** A slide's planned minutes on a path: min on the full path, short on the short one. A slide off the path has none. */
function minutes(s: Slide, path: PathName): number {
  return s.part === "backup" ? 0 : path === "full" ? s.min : (s.short ?? 0);
}

/** The minute a slide should start, counted from the start of the talk: the planned minutes of the path slides before it
 * in the deck. A slide off the path starts where the path would be; a backup slide comes after the whole path. */
export function plannedStart(slides: Slide[], path: PathName, id: string): number {
  const at = slides.findIndex((s) => s.id === id);
  return onPath(slides, path)
    .filter((s) => slides.indexOf(s) < at)
    .reduce((m, s) => m + minutes(s, path), 0);
}

/** How far behind plan the talk is on this slide, in minutes: the talk time on the clock less the slide's planned start.
 * Positive is behind, negative ahead. */
export function drift(slides: Slide[], path: PathName, id: string, elapsedMin: number): number {
  return elapsedMin - plannedStart(slides, path, id);
}

/** The drift the notes window shows: drift() when the slide arrived, plus the time spent on it past its planned minutes.
 * drift() at the current time climbs through every slide, so a three-minute slide would read three minutes behind at its
 * planned end; this one stays put while the slide is within its minutes and climbs once it runs over. A slide off the
 * path has no minutes, so all of its time counts. */
export function liveDrift(slides: Slide[], path: PathName, id: string, arrivedMin: number, nowMin: number): number {
  const s = slides.find((x) => x.id === id);
  return drift(slides, path, id, arrivedMin) + Math.max(0, nowMin - arrivedMin - (s ? minutes(s, path) : 0));
}

/** How far behind plan the talk may get, in seconds, before the notes window's drift line turns red. A few seconds behind is
 * normal, and a line that is red from the first second stops meaning anything. */
export const RED_AFTER_SEC = 30;

/** Whether a drift, in minutes, is far enough behind plan for the drift line to turn red. It rounds to the second, as the
 * line does. On time and ahead are never red. */
export function driftIsRed(driftMin: number): boolean {
  return Math.round(driftMin * 60) >= RED_AFTER_SEC;
}

/** When the talk started, for a clock that starts on the first move: that move's time, dated back by the planned start of
 * the slide it lands on, because the talk began before it (the title's half minute, on both paths). A talk on plan then
 * reads on time from its first move. A backup slide has no planned time, so the clock starts at the move itself. */
export function clockStart(slides: Slide[], path: PathName, id: string, now: number): number {
  const s = slides.find((x) => x.id === id);
  return s?.part === "backup" ? now : now - plannedStart(slides, path, id) * 60_000;
}

/** The clock's checkpoints, one for each topic that has a slide on the path: the topic's name, the minute the plan reaches its end (the end
 * of its last slide on the path), and the whole minute it must be reached by. */
export function checkpointPlan(slides: Slide[], path: PathName): { label: string; planned: number; by: number }[] {
  const line = onPath(slides, path);
  return TOPIC_ORDER.flatMap((topic) => {
    const last = line.filter((s) => s.part === topic).at(-1);
    if (!last) return [];
    const planned = plannedStart(slides, path, last.id) + minutes(last, path);
    return [{ label: TOPICS[topic].name, planned, by: Math.ceil(planned) }];
  });
}

/** Minutes as a clock reads them, to the nearest second and without a sign: 1.333 is "1:20", 35.25 is "35:15". */
export function clock(min: number): string {
  const sec = Math.round(Math.abs(min) * 60);
  return `${Math.floor(sec / 60)}:${String(sec % 60).padStart(2, "0")}`;
}

/** The BroadcastChannel between the deck and its notes window. The deck is the one source of truth: the notes window
 * sends keys, outline jumps, the path, a clock reset, demo requests and a hello when it opens, and the deck applies each
 * and answers with its state: the slide on the screen, how many of its items show (step) of how many it has (steps, 0 on a
 * slide with none), the path and the start of the talk. */
export const CHANNEL = "fairshare-deck";
export type Msg =
  | { t: "state"; id: string; path: PathName; startedAt: number | null; step: number; steps: number }
  | { t: "key"; action: Action }
  | { t: "go"; id: string }
  | { t: "demo"; demo: Jump }
  | { t: "path"; path: PathName }
  | { t: "reset" }
  | { t: "hello" };

/** Where the deck keeps what must outlive a demo jump or a reload: the slide to come back to (sessionStorage; the deck sets
 * it as it jumps, the app's link back reads it, and the deck clears it when it opens again), when the talk started by the
 * clock, set on the first move (sessionStorage, clockStart), and the path (localStorage). */
export const KEYS = { ret: "fairshare.deck.return", started: "fairshare.deck.startedAt", path: "fairshare.deck.path" };

/** After a click, the clicked button or link gives up the focus, so a Space press after it moves the deck once instead of
 * pressing the button again. Returns the cleanup for an effect. */
export function blurAfterClick(): () => void {
  const onClick = (e: MouseEvent) => {
    if (e.target instanceof Element) e.target.closest<HTMLElement>("button, a")?.blur();
  };
  addEventListener("click", onClick);
  return () => removeEventListener("click", onClick);
}
