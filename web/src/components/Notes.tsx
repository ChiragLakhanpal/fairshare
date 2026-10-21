// The presenter's window, /present?notes, which P on the deck opens. It follows the deck and keeps no place of its own:
// when it opens it says hello on the channel, the deck answers with its state, and it shows whatever state the deck
// posts. Every key, outline click, path switch, clock reset and demo request goes to the deck, which applies it as if it
// were pressed there and posts its state back; this window never posts a state, so nothing echoes. It shows the slide on
// the screen at its step, with the point it is on ("Point 2 of 3" on a native slide with steps), and the next one complete
// (native and image slides drawn small, live and animated ones as their thumbs), the note in large type, the talk time
// with the drift and the checkpoints, and the outline of every slide, grouped by part, backup included (a part with no
// slide gets no heading). A click in the outline sends the deck to that slide, which lands a backup slide complete and a
// slide of the path on its first step (outlineArrival in lib/deck.ts). It also calls api.agencies() when it opens and
// every eight minutes: one small query, never cached, that keeps the SQL warehouse awake, because the warehouse stops
// after ten idle minutes. Under the demo buttons it says when the last ping got through.
import { useEffect, useRef, useState } from "react";
import { copy } from "../copy";
import { images } from "../deck/assets";
import facts from "../deck/facts.json";
import { NativeSlide } from "../deck/layouts";
import { slides } from "../deck/slides";
import { api } from "../lib/api";
import {
  blurAfterClick, CHANNEL, checkpointPlan, clock, driftIsRed, fill, fromHash, keyAction, KEYS, liveDrift, move, onPath, outlineParts, PARTS,
  plannedStart, stepCount, type Msg, type PathName, type Slide,
} from "../lib/deck";
import { Check } from "./Icons";

const PING_MS = 8 * 60_000;
const TICK_MS = 500;

/** What the deck last posted, and when its slide arrived here (the drift is measured from the arrival). */
type View = { id: string; path: PathName; startedAt: number | null; arrivedAt: number; step: number; steps: number };

/** The keep-warm ping: when one last got through, and whether the latest one failed. */
type Warm = { at: number | null; missed: boolean };

const clockTime = (t: number) => new Date(t).toLocaleTimeString("en-US", { hour: "numeric", minute: "2-digit" });

function warmLine({ at, missed }: Warm): string {
  if (missed) return copy.notesWarmMissed(at === null ? null : clockTime(at));
  return at === null ? copy.notesWarmWaking : copy.notesWarm(clockTime(at));
}

function savedPath(): PathName {
  try {
    return localStorage.getItem(KEYS.path) === "short" ? "short" : "full";
  } catch {
    return "full";
  }
}

export function Notes() {
  // until the deck answers: the slide in this window's hash, complete, and the path saved in this browser
  const [view, setView] = useState<View>(() => {
    const id = fromHash(slides, location.hash);
    const steps = stepCount(slides.find((s) => s.id === id) ?? slides[0]);
    return { id, path: savedPath(), startedAt: null, arrivedAt: Date.now(), step: steps, steps };
  });
  const [heard, setHeard] = useState(false);
  const [warm, setWarm] = useState<Warm>({ at: null, missed: false });
  const channel = useRef<BroadcastChannel | null>(null);
  const slide = slides.find((s) => s.id === view.id) ?? slides[0];
  const nextId = move(slides, view.path, slide.id, 1);
  const next = nextId === slide.id ? null : (slides.find((s) => s.id === nextId) ?? null);
  const send = (m: Msg) => channel.current?.postMessage(m);

  useEffect(() => {
    document.title = copy.notesTitle;
  }, []);

  useEffect(() => {
    if (typeof BroadcastChannel === "undefined") return;
    const ch = new BroadcastChannel(CHANNEL);
    ch.onmessage = (e: MessageEvent<Msg>) => {
      const m = e.data;
      if (!m || typeof m !== "object" || m.t !== "state") return;
      const now = Date.now();
      setView((v) => ({ id: m.id, path: m.path, startedAt: m.startedAt, step: m.step, steps: m.steps, arrivedAt: v.id === m.id ? v.arrivedAt : now }));
      setHeard(true);
    };
    channel.current = ch;
    ch.postMessage({ t: "hello" } satisfies Msg);
    return () => {
      ch.close(); // no message, and so no state update, arrives after this
      channel.current = null;
    };
  }, []);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      const action = keyAction(e);
      if (!action || action === "notes") return;
      e.preventDefault();
      channel.current?.postMessage({ t: "key", action } satisfies Msg);
    };
    addEventListener("keydown", onKey);
    return () => removeEventListener("keydown", onKey);
  }, []);

  useEffect(blurAfterClick, []);

  useEffect(() => {
    const ping = () =>
      void api.agencies().then(
        () => setWarm({ at: Date.now(), missed: false }), // only the query matters, not its rows
        () => setWarm((w) => ({ ...w, missed: true })), // the next ping is eight minutes away, so the line says this one failed
      );
    ping();
    const every = setInterval(ping, PING_MS);
    return () => clearInterval(every);
  }, []);

  return (
    <div data-now={slide.id} className="fixed inset-0 grid grid-cols-[minmax(0,1fr)_280px_240px] gap-6 overflow-hidden bg-white px-7 py-6 text-ink">
      <main className="min-h-0 overflow-y-auto">
        {!heard && (
          <p role="status" className="mb-4 rounded-lg bg-tint px-3 py-2 text-[14px] text-navy">
            {copy.notesWaiting}
          </p>
        )}
        <div className="flex items-baseline justify-between gap-3">
          <h2 className="t-label">{copy.notesNow}</h2>
          {heard && view.steps > 0 && <p className="text-[15px] font-semibold tabular-nums text-navy">{copy.notesPoint(view.step, view.steps)}</p>}
        </div>
        <div className="mt-2">
          {/* the deck's step: until the deck posts it with its state, the complete slide */}
          <Preview slide={slide} step={view.step} />
        </div>
        <h1 className="mt-3 text-[17px] font-semibold leading-snug">{fill(slide.title, facts)}</h1>
        <p className="mt-4 text-[26px] leading-[1.4]">{fill(slide.note, facts)}</p>
      </main>

      <aside className="flex min-h-0 flex-col gap-7 overflow-y-auto">
        <Clock view={view} slide={slide} send={send} />
        <section>
          <h2 className="t-label">{copy.notesNext}</h2>
          {next ? (
            <>
              <div className="mt-2">
                <Preview slide={next} />
              </div>
              <p className="mt-2 text-[14px] font-medium leading-snug">{fill(next.title, facts)}</p>
            </>
          ) : (
            <p className="mt-2 text-[14px] text-ink-2">{copy.notesLast}</p>
          )}
        </section>
        <section>
          <h2 className="t-label">{copy.notesDemos}</h2>
          <div className="mt-2 flex flex-col gap-2 text-[14px] font-semibold">
            <button type="button" onClick={() => send({ t: "demo", demo: "ask" })} className="press rounded-lg bg-blue px-4 py-2.5 text-left text-white transition-colors hover:bg-navy">
              {copy.askLive}
            </button>
            <button type="button" onClick={() => send({ t: "demo", demo: "precall" })} className="press rounded-lg bg-blue px-4 py-2.5 text-left text-white transition-colors hover:bg-navy">
              {copy.openPrecall}
            </button>
          </div>
          <p role="status" className={`mt-2.5 text-[13px] leading-snug ${warm.missed ? "font-semibold text-red" : "text-ink-2"}`}>{warmLine(warm)}</p>
        </section>
      </aside>

      <Outline view={view} slide={slide} send={send} />
    </div>
  );
}

/** The talk time, the drift, the checkpoints, the path switch and the reset. The time is worked out from startedAt (which
 * the deck sets on the first move, dated back to the plan) on every tick, never by counting ticks, because Chrome slows
 * the timers of a hidden or covered window. */
function Clock({ view, slide, send }: { view: View; slide: Slide; send: (m: Msg) => void }) {
  const [now, setNow] = useState(() => Date.now());
  useEffect(() => {
    const tick = setInterval(() => setNow(Date.now()), TICK_MS);
    return () => clearInterval(tick);
  }, []);
  const { path, startedAt, arrivedAt } = view;
  const since = (t: number) => (startedAt === null ? 0 : Math.max(0, t - startedAt) / 60_000);
  const elapsed = since(Math.max(now, arrivedAt));
  const backup = slide.part === "backup";
  const at = plannedStart(slides, path, slide.id);
  let line = copy.notesNotStarted;
  let late = false;
  if (startedAt !== null && backup) line = copy.notesNoPlan;
  else if (startedAt !== null) {
    const d = liveDrift(slides, path, slide.id, since(arrivedAt), elapsed);
    const sec = Math.round(d * 60);
    late = driftIsRed(d);
    line = sec > 0 ? copy.notesBehind(clock(d)) : sec < 0 ? copy.notesAhead(clock(d)) : copy.notesOnTime;
  }
  return (
    <section>
      <h2 className="t-label">{copy.notesClock}</h2>
      <p className={`mt-1 text-[46px] font-semibold leading-none tracking-[-0.02em] tabular-nums ${startedAt === null ? "text-grey" : ""}`}>{clock(elapsed)}</p>
      <p className={`mt-2 text-[17px] font-semibold ${late ? "text-red" : "text-ink-2"}`}>{line}</p>
      <h2 className="t-label mt-5">{copy.notesCheckpoints}</h2>
      <ul className="mt-1.5 flex flex-col gap-1 text-[15px]">
        {checkpointPlan(slides, path).map((c) => {
          const reached = !backup && at >= c.planned;
          const overdue = !reached && !backup && startedAt !== null && elapsed > c.by;
          return (
            <li key={c.label} className="flex items-center justify-between gap-3">
              <span className={`flex items-center gap-1.5 ${reached ? "text-ink-2" : ""}`}>
                {c.label}
                {reached && (
                  <>
                    <Check width={15} height={15} className="text-blue" />
                    <span className="sr-only">{copy.notesReached}</span>
                  </>
                )}
              </span>
              <span className={`whitespace-nowrap tabular-nums ${overdue ? "font-semibold text-red" : "text-ink-2"}`}>{copy.notesBy(clock(c.by))}</span>
            </li>
          );
        })}
      </ul>
      <div className="mt-4 flex items-center justify-between gap-3 text-[14px] font-semibold">
        <div role="group" aria-label={copy.notesPath} className="inline-flex rounded-lg border border-line p-0.5">
          {(["full", "short"] as const).map((p) => (
            <button
              key={p}
              type="button"
              aria-pressed={path === p}
              onClick={() => send({ t: "path", path: p })}
              className={`rounded-md px-3.5 py-1.5 transition-colors ${path === p ? "bg-blue text-white" : "text-ink hover:bg-surface"}`}
            >
              {p === "full" ? copy.notesFull : copy.notesShort}
            </button>
          ))}
        </div>
        <button type="button" onClick={() => send({ t: "reset" })} className="press rounded-lg border border-line px-3 py-1.5 text-ink transition-colors hover:border-blue hover:text-blue">
          {copy.notesReset}
        </button>
      </div>
    </section>
  );
}

/** A slide drawn small: native and image slides as the deck draws them, a native one at a step (complete when it gets
 * none), live and animated ones as the PNG under their frame. It takes no focus and no clicks (inert), and it is hidden
 * from screen readers and from Playwright's roles, which do not read inert, so a demo slide's button here is never
 * mistaken for this window's own. */
function Preview({ slide, step }: { slide: Slide; step?: number }) {
  const box = useRef<HTMLDivElement>(null);
  const [width, setWidth] = useState(0);
  useEffect(() => {
    const el = box.current;
    if (!el) return;
    const ro = new ResizeObserver(() => setWidth(el.clientWidth));
    ro.observe(el);
    return () => ro.disconnect();
  }, []);
  const png = slide.kind === "image" ? slide.asset : slide.kind === "native" ? undefined : slide.thumb;
  return (
    <div ref={box} inert aria-hidden="true" className="relative aspect-video w-full overflow-hidden rounded-lg border border-line bg-white">
      {png ? (
        <img src={images[png]} alt="" className="absolute inset-0 h-full w-full object-contain" draggable={false} />
      ) : (
        width > 0 && (
          <div className="absolute left-0 top-0 h-[720px] w-[1280px] origin-top-left" style={{ transform: `scale(${width / 1280})` }}>
            <NativeSlide key={slide.id} slide={slide} facts={facts} step={step} />
          </div>
        )
      )}
    </div>
  );
}

/** Every part that has a slide, and every slide, backup included. A click sends the deck there; a slide off the path is greyed. Each
 * button names its slide in data-outline, so a test finds it whatever its title says. */
function Outline({ view, slide, send }: { view: View; slide: Slide; send: (m: Msg) => void }) {
  const current = useRef<HTMLButtonElement>(null);
  useEffect(() => {
    current.current?.scrollIntoView({ block: "nearest" }); // a block body: in newer Chrome it returns a promise, which an effect must not
  }, [slide.id]);
  const line = new Set(onPath(slides, view.path).map((s) => s.id));
  return (
    <nav aria-label={copy.notesOutline} className="min-h-0 overflow-y-auto pr-1">
      <h2 className="t-label">{copy.notesOutline}</h2>
      {outlineParts(slides).map((part) => (
        <section key={part} className="mt-4">
          <h3 className="mb-1 px-2 text-[12.5px] font-semibold text-ink-2">{PARTS[part]}</h3>
          <ol className="text-[13.5px] leading-snug">
            {slides
              .filter((s) => s.part === part)
              .map((s) => {
                const here = s.id === slide.id;
                const off = part !== "backup" && !line.has(s.id);
                return (
                  <li key={s.id}>
                    <button
                      ref={here ? current : undefined}
                      type="button"
                      aria-current={here ? "true" : undefined}
                      data-outline={s.id}
                      onClick={() => send({ t: "go", id: s.id })}
                      className={`w-full rounded-md px-2 py-1 text-left transition-colors ${here ? "bg-tint text-navy" : off ? "text-grey hover:bg-surface" : "text-ink hover:bg-surface"}`}
                    >
                      <span className={here ? "font-semibold" : undefined}>{fill(s.title, facts)}</span>
                      {off && <span className="sr-only"> {copy.notesOffPath}</span>}
                    </button>
                  </li>
                );
              })}
          </ol>
        </section>
      ))}
    </nav>
  );
}
