// The /present deck: a 1280 by 720 stage on white, scaled to the window with CSS zoom, one slide at a time. The slide's id
// is the URL hash, so a reload keeps the place. Right arrow, Space and Page Down go forward; Left arrow and Page Up go
// back. On an animated slide a press first steps the framed diagram, until its last step going forward or step 0 going
// back, and only then moves the deck. Under reduced motion the diagram shows whole and counts as zero steps.
import { useReducedMotion } from "motion/react";
import { useEffect, useRef, useState } from "react";
import facts from "../deck/facts.json";
import { SlideView } from "../deck/SlideView";
import { slides } from "../deck/slides";
import { frameState, fromHash, move, pressTarget, sendKey } from "../lib/deck";

const FORWARD = new Set(["ArrowRight", " ", "PageDown"]);
const BACK = new Set(["ArrowLeft", "PageUp"]);
const fit = () => Math.min(innerWidth / 1280, innerHeight / 720);

export function Present() {
  const reduced = useReducedMotion();
  const [id, setId] = useState(() => fromHash(slides, location.hash));
  const [backward, setBackward] = useState(false);
  const [zoom, setZoom] = useState(fit);
  const frameRef = useRef<HTMLIFrameElement>(null);
  const slide = slides.find((s) => s.id === id) ?? slides[0];

  useEffect(() => {
    const onResize = () => setZoom(fit());
    addEventListener("resize", onResize);
    return () => removeEventListener("resize", onResize);
  }, []);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.metaKey || e.ctrlKey || e.altKey) return; // browser shortcuts stay the browser's
      const dir = FORWARD.has(e.key) ? 1 : BACK.has(e.key) ? -1 : 0;
      if (!dir) return;
      e.preventDefault();
      const frame = frameRef.current;
      if (slide.kind === "animated" && frame) {
        const at = reduced ? null : frameState(frame); // null: not ready, unreadable, or reduced motion, so zero steps
        if (pressTarget(at?.current ?? 0, at?.count ?? 0, dir) === "diagram") {
          sendKey(frame, dir === 1 ? "ArrowRight" : "ArrowLeft");
          return;
        }
      }
      const next = move(slides, "full", slide.id, dir);
      if (next === slide.id) return;
      history.replaceState(null, "", `#${next}`);
      setBackward(dir === -1);
      setId(next);
    };
    addEventListener("keydown", onKey);
    return () => removeEventListener("keydown", onKey);
  }, [slide, reduced]);

  return (
    <div className="fixed inset-0 grid place-items-center overflow-hidden bg-white">
      <div className="relative h-[720px] w-[1280px] overflow-hidden bg-white" style={{ zoom }}>
        <SlideView key={slide.id} slide={slide} backward={backward} frameRef={frameRef} facts={facts} />
      </div>
    </div>
  );
}
