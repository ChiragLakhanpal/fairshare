// One slide on the 1280 by 720 stage, inside the frame (Frame.tsx) that frameInfo gives it: the logo and the topics along
// the top, the label and the slide's number along the bottom, and nothing at all around a still, a screenshot of the app
// with its own top bar. An image slide is its PNG. A live slide is its thumb with the hairline page in a frame on top,
// shown once the page has loaded (without its live readout or its logo, since the deck's frame draws one), so its motion
// starts on arrival; a live slide with a byline also hides the page's caption, and draws its title and the byline at the
// bottom instead. An animated slide is the diagram's motion page in a frame, hidden until the page's controller is ready;
// then the frame switches to embed mode (only the figure, fitted to the frame, with every step it has not reached hidden
// and without its own logo band), gets Home or End (arrivalKey), and shows. Until then the slide shows nothing of the
// figure, so no step shows before its press. A frame that is still not ready after FRAME_FALLBACK_MS, slow or blocked,
// gives way to the thumb under it, the finished figure, and the deck counts it as zero steps. A frame never takes the
// pointer or the focus, so the deck keeps every key press, and it exists only while its slide shows. Figures fill the
// stage under the frame's strips; native slides are drawn in layouts.tsx, in the frame's content box, at the step the deck
// hands down (the complete slide when it hands none). Every string goes through fill().
import { useEffect, useState, type RefObject } from "react";
import { copy } from "../copy";
import {
  arrivalKey, arrive, fill, FRAME_FALLBACK_MS, showsData, type Arrival, type DeckFacts, type FrameInfo, type Jump, type Slide,
} from "../lib/deck";
import { images, pages } from "./assets";
import { DeckFrame } from "./Frame";
import { NativeSlide } from "./layouts";
import { MUTED } from "./ramp";

const POLL_MS = 50;

/** Whether a live frame shows its hairline page, which then loses its live readout (#read), as the thumb under it does,
 * and its logo (.brand), since the deck's frame draws one; on a slide with a byline it also loses its caption, which the
 * title and the byline replace. A blocked frame cannot be read, and a failed one holds another page: both keep the thumb.
 * The page opened on its own keeps all three. */
export function showPage(f: { readonly contentDocument: Document | null }, byline: boolean): boolean {
  try {
    const doc = f.contentDocument;
    if (!doc?.querySelector(".frame")) return false;
    const hide = ["#read", ".brand", ...(byline ? [".caption"] : [])];
    for (const part of hide) doc.querySelector<HTMLElement>(part)?.style.setProperty("display", "none");
    return true;
  } catch {
    return false;
  }
}

export function SlideView({ slide, frame, arrival, frameRef, facts, onDemo, onReady, step }: {
  slide: Slide;
  frame: FrameInfo;
  /** How the slide came on: an animated slide's diagram starts on its first step going forward, and whole going back or after a load. */
  arrival: Arrival;
  frameRef: RefObject<HTMLIFrameElement | null>;
  facts: DeckFacts;
  onDemo: (demo: Jump) => void;
  /** Called once an animated slide's frame is ready and has had its key, so the deck can say where its diagram stands. */
  onReady?: () => void;
  /** How many of a native slide's items show; none shows them all. */
  step?: number;
}) {
  const [ready, setReady] = useState(false); // the animated frame's controller is ready
  const [fallback, setFallback] = useState(false); // the animated frame missed FRAME_FALLBACK_MS, so the finished figure stands in
  const [shown, setShown] = useState(false); // the live frame's page has loaded
  const title = fill(slide.title, facts);
  const hasByline = slide.kind === "live" && !!slide.byline?.length;
  const finishedFigure = fallback && !ready; // the frame missed FRAME_FALLBACK_MS and is still not ready: its thumb stands in

  // Once per slide (Present keys SlideView by slide id, so a new slide is a new mount): poll the frame for as long as the
  // slide is up, until its controller has run, and let the finished figure stand in once FRAME_FALLBACK_MS has passed
  // without it.
  useEffect(() => {
    if (slide.kind !== "animated") return;
    const mounted = performance.now();
    const late = setTimeout(() => setFallback(true), FRAME_FALLBACK_MS);
    const poll = setInterval(() => {
      const iframe = frameRef.current;
      if (!iframe) return;
      try {
        const doc = iframe.contentDocument;
        if (!doc?.querySelector("[data-motion-root]")?.classList.contains("motion-ready")) return;
        clearInterval(poll);
        doc.documentElement.setAttribute("data-embed", "");
        arrive(iframe, arrivalKey(arrival, performance.now() - mounted));
      } catch {
        return; // a blocked frame cannot be read, or the frame went away: it never gets ready, and after FRAME_FALLBACK_MS the finished figure stands in
      }
      setReady(true);
      onReady?.();
    }, POLL_MS);
    return () => {
      clearInterval(poll);
      clearTimeout(late);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const cover = "absolute inset-0 h-full w-full";
  const noPointer = { pointerEvents: "none" as const };
  return (
    <div data-slide={slide.id} className="absolute inset-0">
      <DeckFrame info={frame} label={showsData(slide, facts) ? copy.deckFooterData : copy.deckFooter}>
        {slide.kind === "image" && <img src={images[slide.asset!]} alt={title} className={`${cover} object-contain`} draggable={false} />}
        {(slide.kind === "animated" || slide.kind === "live") && (
          <img
            data-thumb=""
            src={images[slide.thumb!]}
            alt={title}
            className={`${cover} object-contain`}
            draggable={false}
            // an animated slide's thumb is its finished figure: out of sight unless it stands in for a frame that is late
            style={slide.kind === "animated" && !finishedFigure ? { visibility: "hidden" } : undefined}
          />
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
            style={{ ...noPointer, visibility: ready ? "visible" : "hidden" }}
          />
        )}
        {slide.kind === "live" && (
          <iframe
            data-live-frame
            data-shown={shown ? "1" : undefined}
            src={pages[slide.asset!]}
            title={title}
            tabIndex={-1}
            onLoad={(e) => setShown(showPage(e.currentTarget, hasByline))}
            className={`${cover} border-0`}
            style={{ ...noPointer, visibility: shown ? "visible" : "hidden" }}
          />
        )}
        {hasByline && <Byline title={title} lines={slide.byline!.map((l) => fill(l, facts))} />}
        {slide.kind === "native" && slide.native && <NativeSlide slide={slide} facts={facts} onDemo={onDemo} step={step} />}
      </DeckFrame>
    </div>
  );
}

/** A live slide's title and byline, centered at the bottom of the stage where the page's caption sat, ending where the
 * content box ends (y 664), so it clears the footer. It is white behind, so the caption in the thumb under it never shows
 * through while the page loads. */
function Byline({ title, lines }: { title: string; lines: string[] }) {
  return (
    <div data-byline className="absolute inset-x-0 bottom-[56px] flex flex-col items-center bg-white px-[64px] text-center">
      <h1 className="text-[32px] font-semibold leading-[1.2] tracking-[-0.01em] text-navy">{title}</h1>
      <div className="mt-3 text-[20px] leading-[1.4]" style={{ color: MUTED }}>
        {lines.map((l, i) => <p key={i}>{l}</p>)}
      </div>
    </div>
  );
}
