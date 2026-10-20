// One slide on the 1280 by 720 stage. An image slide is its PNG. An animated slide is its static PNG with the diagram's
// motion page in a frame on top, hidden until the page's controller is ready; then the frame switches to embed mode (only
// the figure, fitted to the frame), gets Home or End (arrivalKey), and shows. A frame that never gets ready, slow or
// blocked, leaves the PNG, and the deck counts it as zero steps. A frame never takes the pointer or the focus, so the
// deck keeps every key press.
import { useReducedMotion } from "motion/react";
import { useEffect, useState, type RefObject } from "react";
import { arrivalKey, sendKey, type Slide } from "../lib/deck";
import { images, pages } from "./assets";

const POLL_MS = 50;

export function SlideView({ slide, backward, frameRef }: { slide: Slide; backward: boolean; frameRef: RefObject<HTMLIFrameElement | null> }) {
  const reduced = useReducedMotion();
  const [ready, setReady] = useState(false);

  // Once per slide (Present keys SlideView by slide id, so a new slide is a new mount): poll the frame for as long as the
  // slide is up, until its controller has run.
  useEffect(() => {
    if (slide.kind !== "animated") return;
    const mounted = performance.now();
    const poll = setInterval(() => {
      const frame = frameRef.current;
      if (!frame) return;
      let doc: Document | null = null;
      try {
        doc = frame.contentDocument;
      } catch {
        return; // a blocked frame cannot be read; the PNG stays
      }
      if (!doc?.querySelector("[data-motion-root]")?.classList.contains("motion-ready")) return;
      clearInterval(poll);
      doc.documentElement.setAttribute("data-embed", "");
      sendKey(frame, arrivalKey(backward, performance.now() - mounted, !!reduced));
      setReady(true);
    }, POLL_MS);
    return () => clearInterval(poll);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const fill = "absolute inset-0 h-full w-full";
  return (
    <div data-slide={slide.id} className="absolute inset-0">
      {slide.kind === "image" && <img src={images[slide.asset!]} alt={slide.title} className={`${fill} object-contain`} draggable={false} />}
      {slide.kind === "animated" && (
        <>
          <img src={images[slide.thumb!]} alt={slide.title} className={`${fill} object-contain`} draggable={false} />
          <iframe
            data-slide-frame
            data-ready={ready ? "1" : undefined}
            ref={frameRef}
            src={pages[slide.asset!]}
            title={slide.title}
            tabIndex={-1}
            className={`${fill} border-0`}
            style={{ pointerEvents: "none", visibility: ready ? "visible" : "hidden" }}
          />
        </>
      )}
    </div>
  );
}
