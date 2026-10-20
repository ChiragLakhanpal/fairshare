// The /present deck's rules: which slide a press reaches on the full or the short path, which slide a URL hash names, and
// the handoff on an animated slide, where a press steps the framed diagram until its last step and then moves the deck.
// frameState and sendKey are the only two that touch a frame, and both read it inside try and catch, because an aborted
// or blocked frame cannot be read. The pure parts are tested in deck.test.ts.

export type Part = "first" | "data" | "built" | "proof" | "backup";
export type Kind = "image" | "live" | "animated" | "native";
export type PathName = "full" | "short";
export type Slide = { id: string; part: Part; kind: Kind; title: string; min: number; short?: number; asset?: string; thumb?: string; native?: Native; note: string };
export type Native = { layout: "statement"; lines: string[] }; // Task 11 adds the other layouts

export const PARTS: Record<Part, string> = {
  first: "The first answer",
  data: "The data",
  built: "What I built",
  proof: "Proof and next",
  backup: "Backup",
};

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
