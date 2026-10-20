// The /present deck's rules: which slide a press reaches on the full or the short path, which slide a URL hash names, and
// the handoff on an animated slide, where a press steps the framed diagram until its last step and then moves the deck.
// frameState and sendKey are the only two that touch a frame, and both read it inside try and catch, because an aborted
// or blocked frame cannot be read. The text helpers fill a slide's {placeholders} from facts.json and read its words for
// the content rules. The keys, the parts, the clock and the messages between the deck and its notes window are at the
// end. The pure parts are tested in deck.test.ts.

export type Part = "first" | "data" | "built" | "proof" | "backup";
export type Kind = "image" | "live" | "animated" | "native";
export type PathName = "full" | "short";
/** still: a screenshot of the app itself, drawn edge to edge. The app has its own top bar, so a still gets no part label over it. */
export type Slide = { id: string; part: Part; kind: Kind; title: string; min: number; short?: number; asset?: string; thumb?: string; still?: boolean; native?: Native; note: string };
export type Demo = { kind: "ask"; question: string } | { kind: "precall" } | { kind: "dashboard" };
/** The demos the deck jumps into the app for. The dashboard only opens in a new tab, so it needs no jump. */
export type Jump = Exclude<Demo["kind"], "dashboard">;
export type Tile = { head: string; body: string; tag?: "Possibility" };
export type Native =
  | { layout: "statement"; lines: string[] }
  | { layout: "tiles"; tiles: Tile[] }
  | { layout: "table"; tables: string[] } // keys of facts.columns, or "checks"
  | { layout: "demo"; demo: Demo; lines: string[] };
/** What fill() reads from facts.json: the display string of every fact and every dated fact. */
export type Facts = { facts: Record<string, { display: string }>; dated: Record<string, { display: string }> };
/** All of facts.json that a slide shows: the facts, plus the columns of each table and the basic checks. */
export type DeckFacts = Facts & {
  columns: Record<string, { name: string; meaning: string; example: string }[]>;
  checks: { name: string; expected: unknown; actual: unknown; ok: boolean }[];
};

export const PARTS: Record<Part, string> = {
  first: "The first answer",
  data: "The data",
  built: "What I built",
  proof: "Proof and next",
  backup: "Backup",
};

/** Whether SlideView draws the part's name at the top right of a slide. A still is a screenshot of the app, whose own top bar sits under
 * that corner, so it gets none. */
export function showEyebrow(s: Slide): boolean {
  return !s.still;
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

/** Whether a press on an animated slide steps the diagram or moves the deck: forward steps the diagram until its last
 * step, back until step 0. A frame with no steps, or steps it could not read (NaN), counts as zero steps. */
export function pressTarget(current: number, count: number, dir: 1 | -1): "diagram" | "deck" {
  const steps = count > 0 ? count : 0; // NaN > 0 is false
  const at = current > 0 ? Math.min(current, steps) : 0;
  return (dir === 1 ? at < steps : at > 0) ? "diagram" : "deck";
}

/** A frame that becomes ready this long after its slide arrived started late: the presenter has been talking over the
 * whole figure (the PNG under the frame), so it stays whole. */
const LATE_MS = 2000;

/** The key a framed diagram gets when its slide arrives: Home (step 0, which also stops the reveal from playing on its
 * own) going forward, and End (the whole figure) going back, after a late start, and under reduced motion, where Home
 * would still hide most of the figure because the controller's keys ignore reduced motion. */
export function arrivalKey(backward: boolean, elapsedMs: number, reduced: boolean): "Home" | "End" {
  return backward || reduced || elapsedMs > LATE_MS ? "End" : "Home";
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

/** A {placeholder}: anything between braces, so a typo cannot pass for plain text. */
const PLACEHOLDER = /\{([^{}]*)\}/g;

/** Every string a slide shows, plus its note: what the content rules read. A table's cells come from facts.json, not from
 * the slide, so only its table keys are here. */
export function texts(s: Slide): string[] {
  const n = s.native;
  const shown = !n
    ? []
    : n.layout === "statement"
      ? n.lines
      : n.layout === "tiles"
        ? n.tiles.flatMap((t) => [t.head, t.body, ...(t.tag ? [t.tag] : [])])
        : n.layout === "table"
          ? n.tables
          : [...(n.demo.kind === "ask" ? [n.demo.question] : []), ...n.lines];
  return [s.title, ...shown, s.note];
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

/** The table keys a table slide can draw: the basic checks, and the tables facts.json holds columns for. An unknown key is left
 * out, because the deck has no error boundary and a slide that throws goes blank; deck.test.ts holds slides.ts to known keys. */
export function knownTables(keys: string[], columns: DeckFacts["columns"]): string[] {
  return keys.filter((k) => k === "checks" || Object.hasOwn(columns, k));
}

/** How many words a text has, split on runs of white space. */
export function words(text: string): number {
  return text.split(/\s+/).filter(Boolean).length;
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

/** When the talk started, for a clock that starts on the first move: that move's time, dated back by the planned start of
 * the slide it lands on, because the talk began before it (the title's half minute, on both paths). A talk on plan then
 * reads on time from its first move. A backup slide has no planned time, so the clock starts at the move itself. */
export function clockStart(slides: Slide[], path: PathName, id: string, now: number): number {
  const s = slides.find((x) => x.id === id);
  return s?.part === "backup" ? now : now - plannedStart(slides, path, id) * 60_000;
}

/** The clock's checkpoints (Global Constraints): a slide done by a minute, or a slide started by one. */
const CHECKPOINTS: Record<PathName, { id: string; done: boolean; by: number }[]> = {
  full: [{ id: "precall", done: true, by: 29 }, { id: "start", done: false, by: 36 }],
  short: [{ id: "ask", done: true, by: 5 }, { id: "start", done: false, by: 11 }],
};

/** Each checkpoint with the minute the plan reaches it: the slide's planned end for a "done" checkpoint, its planned
 * start otherwise, and the minute it must be reached by. */
export function checkpointPlan(slides: Slide[], path: PathName): { label: string; planned: number; by: number }[] {
  return CHECKPOINTS[path].map(({ id, done, by }) => {
    const s = slides.find((x) => x.id === id);
    const start = plannedStart(slides, path, id);
    return { label: done ? `${id} done` : id, planned: done && s ? start + minutes(s, path) : start, by };
  });
}

/** Minutes as a clock reads them, to the nearest second and without a sign: 1.333 is "1:20", 35.25 is "35:15". */
export function clock(min: number): string {
  const sec = Math.round(Math.abs(min) * 60);
  return `${Math.floor(sec / 60)}:${String(sec % 60).padStart(2, "0")}`;
}

/** The BroadcastChannel between the deck and its notes window. The deck is the one source of truth: the notes window
 * sends keys, outline jumps, the path, a clock reset, demo requests and a hello when it opens, and the deck applies each
 * and answers with its state. */
export const CHANNEL = "fairshare-deck";
export type Msg =
  | { t: "state"; id: string; path: PathName; startedAt: number | null }
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
