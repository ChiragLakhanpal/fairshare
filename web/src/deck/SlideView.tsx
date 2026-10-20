// One slide on the 1280 by 720 stage, with a small eyebrow naming its part at the right end of the logo band. An image
// slide is its PNG. A live slide is its thumb with the hairline page in a frame on top, shown once the page has loaded
// (without its live readout), so its motion starts on arrival. An animated slide is its thumb with the diagram's motion page in a frame on top,
// hidden until the page's controller is ready; then the frame switches to embed mode (only the figure, fitted to the
// frame), gets Home or End (arrivalKey), and shows. A frame that never gets ready, slow or blocked, leaves the thumb, and
// the deck counts it as zero steps. A frame never takes the pointer or the focus, so the deck keeps every key press, and
// it exists only while its slide shows. Native slides are drawn in layouts.tsx. Every string goes through fill().
import { useReducedMotion } from "motion/react";
import { useEffect, useState, type RefObject } from "react";
import { arrivalKey, fill, PARTS, sendKey, type DeckFacts, type Jump, type Slide } from "../lib/deck";
import { images, pages } from "./assets";
import { MONO, MUTED, NativeSlide } from "./layouts";

const POLL_MS = 50;

/** Whether a live frame shows its hairline page, which then loses its live readout (#read), as the thumb under it does.
 * A blocked frame cannot be read, and a failed one holds another page: both keep the thumb. The page opened on its own
 * keeps its readout. */
function showPage(f: HTMLIFrameElement): boolean {
  try {
    const doc = f.contentDocument;
    if (!doc?.querySelector(".frame")) return false;
    doc.getElementById("read")?.style.setProperty("display", "none");
    return true;
  } catch {
    return false;
  }
}

export function SlideView({ slide, backward, frameRef, facts, onDemo }: {
  slide: Slide;
  backward: boolean;
  frameRef: RefObject<HTMLIFrameElement | null>;
  facts: DeckFacts;
  onDemo: (demo: Jump) => void;
}) {
  const reduced = useReducedMotion();
  const [ready, setReady] = useState(false); // the animated frame's controller is ready
  const [shown, setShown] = useState(false); // the live frame's page has loaded
  const title = fill(slide.title, facts);

  // Once per slide (Present keys SlideView by slide id, so a new slide is a new mount): poll the frame for as long as the
  // slide is up, until its controller has run.
  useEffect(() => {
    if (slide.kind !== "animated") return;
    const mounted = performance.now();
    const poll = setInterval(() => {
      const frame = frameRef.current;
      if (!frame) return;
      try {
        const doc = frame.contentDocument;
        if (!doc?.querySelector("[data-motion-root]")?.classList.contains("motion-ready")) return;
        clearInterval(poll);
        doc.documentElement.setAttribute("data-embed", "");
        const key = arrivalKey(backward, performance.now() - mounted, !!reduced);
        sendKey(frame, key);
        // End shows the whole figure: finish its parts' assembly, so the end state shows at once instead of replaying
        if (key === "End") {
          doc.getAnimations().forEach((a) => {
            try {
              a.finish();
            } catch {
              // an endless animation cannot finish; it keeps running
            }
          });
        }
      } catch {
        return; // a blocked frame cannot be read, or the frame went away: the thumb stays
      }
      setReady(true);
    }, POLL_MS);
    return () => clearInterval(poll);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const cover = "absolute inset-0 h-full w-full";
  const frame = { pointerEvents: "none" as const };
  return (
    <div data-slide={slide.id} className="absolute inset-0">
      {slide.kind === "image" && <img src={images[slide.asset!]} alt={title} className={`${cover} object-contain`} draggable={false} />}
      {(slide.kind === "animated" || slide.kind === "live") && (
        <img src={images[slide.thumb!]} alt={title} className={`${cover} object-contain`} draggable={false} />
      )}
      {slide.kind === "animated" && (
        <iframe
          data-slide-frame
          data-ready={ready ? "1" : undefined}
          ref={frameRef}
          src={pages[slide.asset!]}
          title={title}
          tabIndex={-1}
          className={`${cover} border-0`}
          style={{ ...frame, visibility: ready ? "visible" : "hidden" }}
        />
      )}
      {slide.kind === "live" && (
        <iframe
          data-live-frame
          data-shown={shown ? "1" : undefined}
          src={pages[slide.asset!]}
          title={title}
          tabIndex={-1}
          onLoad={(e) => setShown(showPage(e.currentTarget))}
          className={`${cover} border-0`}
          style={{ ...frame, visibility: shown ? "visible" : "hidden" }}
        />
      )}
      {slide.kind === "native" && slide.native && <NativeSlide slide={slide} facts={facts} onDemo={onDemo} />}
      <span
        className="pointer-events-none absolute right-[40px] top-[24px] flex h-[22px] items-center text-[8px] font-medium uppercase tracking-[0.18em]"
        style={{ fontFamily: MONO, color: MUTED }}
      >
        {PARTS[slide.part]}
      </span>
    </div>
  );
}
