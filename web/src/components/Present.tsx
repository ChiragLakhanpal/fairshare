// The /present deck: a 1280 by 720 stage on white, scaled to the window with CSS zoom, one slide at a time. The slide's id
// is the URL hash, so a reload keeps the place. Keys go through keyAction: Right arrow, Space and Page Down go forward,
// Left arrow and Page Up go back, Home and End go to the ends of the main path, S to the next part, and P opens the notes
// window (Notes.tsx, the same page with ?notes). On an animated slide a press first steps the framed diagram, until its
// last step going forward or step 0 going back, and only then moves the deck. Under reduced motion the diagram shows whole
// and counts as zero steps. The deck is the one source of truth for the notes window: it applies each message the notes
// window sends as if it were pressed here, and posts its state on mount, after every move and after every message it
// applies. The path (localStorage) and the start of the talk, set on the first move and dated back to the plan
// (sessionStorage), outlive a reload and a demo jump.
import { useReducedMotion } from "motion/react";
import { useEffect, useEffectEvent, useRef, useState } from "react";
import { flushSync } from "react-dom";
import facts from "../deck/facts.json";
import { SlideView } from "../deck/SlideView";
import { slides } from "../deck/slides";
import { blurAfterClick, CHANNEL, clockStart, destination, frameState, fromHash, keyAction, KEYS, pressTarget, sendKey, type Action, type Msg, type PathName } from "../lib/deck";
import { Notes } from "./Notes";

const fit = () => Math.min(innerWidth / 1280, innerHeight / 720);
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
  const [id, setId] = useState(() => fromHash(slides, location.hash));
  const [backward, setBackward] = useState(false);
  const [path, setPath] = useState<PathName>(() => (read(local, KEYS.path) === "short" ? "short" : "full"));
  const [startedAt, setStartedAt] = useState<number | null>(() => Number(read(session, KEYS.started)) || null);
  const [ready, setReady] = useState(false); // the channel to the notes window is open
  const [applied, setApplied] = useState(0); // counts the messages applied, so each one posts the state even if nothing moved
  const [zoom, setZoom] = useState(fit);
  const frameRef = useRef<HTMLIFrameElement>(null);
  const channel = useRef<BroadcastChannel | null>(null);
  const slide = slides.find((s) => s.id === id) ?? slides[0];

  /** Shows another slide. The first move starts the clock, dated back by the planned start of the slide it lands on. */
  const go = (next: string) => {
    if (next === slide.id) return;
    history.replaceState(null, "", `#${next}`);
    setBackward(slides.findIndex((s) => s.id === next) < slides.indexOf(slide));
    setId(next);
    if (startedAt === null) {
      const start = clockStart(slides, path, next, Date.now());
      write(session, KEYS.started, String(start));
      setStartedAt(start);
    }
  };

  /** One key's action, pressed here or sent by the notes window. */
  const act = (action: Action) => {
    if (action === "notes") {
      window.open(`/present?notes#${slide.id}`, "fairshare-notes", "popup,width=1100,height=760")?.focus();
      return;
    }
    const frame = frameRef.current;
    if ((action === "next" || action === "prev") && slide.kind === "animated" && frame) {
      const dir = action === "next" ? 1 : -1;
      const at = reduced ? null : frameState(frame); // null: not ready, unreadable, or reduced motion, so zero steps
      if (pressTarget(at?.current ?? 0, at?.count ?? 0, dir) === "diagram") {
        sendKey(frame, dir === 1 ? "ArrowRight" : "ArrowLeft");
        return;
      }
    }
    go(destination(slides, path, slide.id, action));
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
    } else if (m.t !== "hello") return; // another deck's state, a demo request (Task 13 wires the jumps), or a bad message
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
    channel.current?.postMessage({ t: "state", id, path, startedAt } satisfies Msg);
  }, [id, path, startedAt, applied]);

  return (
    <div data-deck-ready={ready ? "" : undefined} className="fixed inset-0 grid place-items-center overflow-hidden bg-white">
      <div className="relative h-[720px] w-[1280px] overflow-hidden bg-white" style={{ zoom }}>
        <SlideView key={slide.id} slide={slide} backward={backward} frameRef={frameRef} facts={facts} />
      </div>
    </div>
  );
}
