// The /present deck: a 1280 by 720 stage on white, scaled to the window with CSS zoom, one slide at a time, in the frame
// (Frame.tsx) that frameInfo gives it on the path that is on. The slide's id is the URL hash, so a reload keeps the place.
// Keys go through keyAction: Right arrow, Space and Page Down go forward, Left arrow and Page Up go back, Home and End go
// to the ends of the main path, S to the next part, and P opens the notes window (Notes.tsx, the same page with ?notes).
// A slide with steps takes a press for each one before the deck moves. A native slide shows its title on arrival and
// brings in an item a press (its step is kept in a ref as well as in state, so a press applied in the same tick as the one
// before it reads the step that one left); on an animated slide a press steps the framed diagram. Going forward a press
// steps until the last step, and going back until step 0, and only then moves the deck. A slide arrives on step 0 going
// forward and complete going back, after a reload, and on the way back from a demo. Under reduced motion the diagram shows
// whole and counts as zero steps. The deck is the one source of truth for the notes window: it applies each message the
// notes window sends as if it were pressed here, and posts its state (the slide, its step and its number of steps, the
// path and the start of the talk) on mount, after every move and step, and after every message it applies. The path
// (localStorage) and the start of the talk, set on the first move and dated back to the plan (sessionStorage), outlive a
// reload and a demo jump. A demo button on a slide, or in the notes window, jumps into the app in this tab (jump): the
// slide to come back to waits in sessionStorage for the app's link, and the deck clears it when it opens again, or when
// the browser restores it from its cache.
import { useReducedMotion } from "motion/react";
import { useEffect, useEffectEvent, useRef, useState } from "react";
import { flushSync } from "react-dom";
import facts from "../deck/facts.json";
import { SlideView } from "../deck/SlideView";
import { slides } from "../deck/slides";
import {
  arrivalStep, askQuestion, blurAfterClick, CHANNEL, clockStart, destination, fill, frameInfo, frameState, fromHash, keyAction, KEYS,
  pressTarget, sendKey, stepCount, type Action, type Jump, type Msg, type PathName,
} from "../lib/deck";
import { store } from "../lib/store";
import { Notes } from "./Notes";

const fit = () => Math.min(innerWidth / 1280, innerHeight / 720);
const slideOf = (id: string) => slides.find((s) => s.id === id) ?? slides[0];
/** Where the talk stands: the slide on the screen, and how many of its items show (0 on a slide with no steps). */
type Place = { id: string; step: number };
/** The actions the notes window may send. Only a key press here may open a window. */
const REMOTE = new Set<string>(["next", "prev", "first", "last", "part"]);

// Storage that is blocked or full keeps nothing, and the deck runs on without it.
const local = () => localStorage;
const session = () => sessionStorage;
function read(storage: () => Storage, key: string): string | null {
  try {
    return storage().getItem(key);
  } catch {
    return null;
  }
}
function write(storage: () => Storage, key: string, value: string | null): void {
  try {
    if (value === null) storage().removeItem(key);
    else storage().setItem(key, value);
  } catch {
    // the value lives only in this page
  }
}

export function Present() {
  return new URLSearchParams(location.search).has("notes") ? <Notes /> : <Deck />;
}

function Deck() {
  const reduced = useReducedMotion();
  // the first render after a load shows its slide complete: a reload, and the way back from a demo, which loads the deck
  // again
  const [place, setPlace] = useState<Place>(() => {
    const first = slideOf(fromHash(slides, location.hash));
    return { id: first.id, step: arrivalStep(first, "load") };
  });
  const [backward, setBackward] = useState(false);
  const [path, setPath] = useState<PathName>(() => (read(local, KEYS.path) === "short" ? "short" : "full"));
  const [startedAt, setStartedAt] = useState<number | null>(() => Number(read(session, KEYS.started)) || null);
  const [ready, setReady] = useState(false); // the channel to the notes window is open
  const [applied, setApplied] = useState(0); // counts the messages applied, so each one posts the state even if nothing moved
  const [zoom, setZoom] = useState(fit);
  const frameRef = useRef<HTMLIFrameElement>(null);
  const channel = useRef<BroadcastChannel | null>(null);
  // The place as the last press left it. A press reads this and not the state, which a burst of presses applied one after
  // another may not have rendered yet, so none reads a step or a slide that the one before it has already left.
  const here = useRef(place);
  const slide = slideOf(place.id);

  /** Stands at a place: in the ref at once, for the next press, and in state, for the render. */
  const stand = (p: Place) => {
    here.current = p;
    setPlace(p);
  };

  /** Shows another slide, on the step it arrives on: its title alone going forward, complete going back. The first move
   * starts the clock, dated back by the planned start of the slide it lands on. */
  const go = (next: string) => {
    const from = here.current.id;
    if (next === from) return;
    const back = slides.indexOf(slideOf(next)) < slides.indexOf(slideOf(from));
    history.replaceState(null, "", `#${next}`);
    setBackward(back);
    stand({ id: next, step: arrivalStep(slideOf(next), back ? "backward" : "forward") });
    if (startedAt === null) {
      const start = clockStart(slides, path, next, Date.now());
      write(session, KEYS.started, String(start));
      setStartedAt(start);
    }
  };

  /** One key's action, pressed here or sent by the notes window. */
  const act = (action: Action) => {
    const { id, step } = here.current;
    if (action === "notes") {
      window.open(`/present?notes#${id}`, "fairshare-notes", "popup,width=1100,height=760")?.focus();
      return;
    }
    if (action === "next" || action === "prev") {
      const dir = action === "next" ? 1 : -1;
      const current = slideOf(id);
      if (pressTarget(step, stepCount(current), dir) === "diagram") {
        stand({ id, step: step + dir }); // the slide's own next item, or the one before it
        return;
      }
      const frame = frameRef.current;
      if (current.kind === "animated" && frame) {
        const at = reduced ? null : frameState(frame); // null: not ready, unreadable, or reduced motion, so zero steps
        if (pressTarget(at?.current ?? 0, at?.count ?? 0, dir) === "diagram") {
          sendKey(frame, dir === 1 ? "ArrowRight" : "ArrowLeft");
          return;
        }
      }
    }
    go(destination(slides, path, id, action));
  };

  /** A demo, in the app, in this tab. The slide to come back to waits in sessionStorage. The app opens where its own memory
   * says (the mode and, for Delegate, the agent), so that is set first; Ask also gets its question in the URL, which the
   * app reads once and removes. */
  const jump = (demo: Jump) => {
    write(session, KEYS.ret, here.current.id);
    if (demo === "ask") {
      const question = askQuestion(slides);
      store.setMode("ask");
      location.assign(question ? `/?q=${encodeURIComponent(fill(question, facts))}` : "/");
    } else {
      store.setDelegate({ agent: "precall", runId: null, itemId: null });
      store.setMode("delegate");
      location.assign("/");
    }
  };

  const onKey = useEffectEvent((e: KeyboardEvent) => {
    const action = keyAction(e);
    if (!action) return; // browser shortcuts stay the browser's
    e.preventDefault();
    act(action);
  });

  const onMessage = useEffectEvent((m: Msg) => {
    if (!m || typeof m !== "object") return;
    if (m.t === "key" && REMOTE.has(m.action)) act(m.action);
    else if (m.t === "go" && slides.some((s) => s.id === m.id)) go(m.id);
    else if (m.t === "path" && (m.path === "full" || m.path === "short")) {
      write(local, KEYS.path, m.path);
      setPath(m.path);
    } else if (m.t === "reset") {
      write(session, KEYS.started, null);
      setStartedAt(null);
    } else if (m.t === "demo" && (m.demo === "ask" || m.demo === "precall")) jump(m.demo);
    else if (m.t !== "hello") return; // another deck's state, or a bad message
    setApplied((n) => n + 1);
  });

  useEffect(() => {
    const onResize = () => setZoom(fit());
    addEventListener("resize", onResize);
    return () => removeEventListener("resize", onResize);
  }, []);

  useEffect(() => {
    const onKeyDown = (e: KeyboardEvent) => onKey(e);
    addEventListener("keydown", onKeyDown);
    return () => removeEventListener("keydown", onKeyDown);
  }, []);

  useEffect(blurAfterClick, []);

  // The way back is for one trip: once the deck is open again, by the app's link or by the browser's Back button (which
  // skips the link), it is cleared. A page the browser restores from its back/forward cache mounts nothing again, so that
  // restore clears it too, and shows its slide complete, as a load would.
  useEffect(() => {
    write(session, KEYS.ret, null);
    const onShow = (e: PageTransitionEvent) => {
      if (!e.persisted) return;
      write(session, KEYS.ret, null);
      stand({ id: here.current.id, step: arrivalStep(slideOf(here.current.id), "load") });
    };
    addEventListener("pageshow", onShow);
    return () => removeEventListener("pageshow", onShow);
  }, []);

  // The channel opens once, so no message can fall between two renders. Each message renders at once (flushSync): the
  // next one, which may already be queued, then reads the slide this one reached.
  useEffect(() => {
    if (typeof BroadcastChannel === "undefined") return;
    const ch = new BroadcastChannel(CHANNEL);
    ch.onmessage = (e: MessageEvent<Msg>) => flushSync(() => onMessage(e.data));
    channel.current = ch;
    setReady(true);
    return () => {
      ch.close();
      channel.current = null;
    };
  }, []);

  useEffect(() => {
    channel.current?.postMessage({ t: "state", id: place.id, path, startedAt, step: place.step, steps: stepCount(slide) } satisfies Msg);
  }, [place, path, startedAt, applied]);

  return (
    <div data-deck-ready={ready ? "" : undefined} className="fixed inset-0 grid place-items-center overflow-hidden bg-white">
      <div className="relative h-[720px] w-[1280px] overflow-hidden bg-white" style={{ zoom }}>
        <SlideView key={slide.id} slide={slide} frame={frameInfo(slides, path, slide.id)} backward={backward} frameRef={frameRef} facts={facts} onDemo={jump} step={place.step} />
      </div>
    </div>
  );
}
