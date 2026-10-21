// The frame every slide but a still sits in, on the 1280 by 720 stage. Along the top, a white strip (y 0 to 64) with the AA logo at the left
// and the five topics as a tracker (x 300 to 1240): each topic has an equal column with its name, the lit one navy and heavier, and at y 44 a
// 3px segment for each of its slides on the path that is on, navy for the slides already shown, blue for this one and light for the ones to
// come. Along the bottom, a white strip (y 690 to 720) with the label at the left, the talk's title or "Synthetic data", and at the right the
// slide's number on the path, or Backup. frameInfo (lib/deck.ts) says which parts a slide gets: the first and last slides of the path the logo
// alone, the agenda no tracker, a still nothing. The strips are drawn over the slide, so a figure, which fills the stage, keeps its own logo
// band under the top strip.
import type { ReactNode } from "react";
import { copy } from "../copy";
import { PARTS, TOPIC_ORDER, TOPICS, type FrameInfo, type Segment } from "../lib/deck";
import { MONO, MUTED } from "./ramp";

const SEGMENT: Record<Segment, string> = { passed: "bg-navy", current: "bg-blue", later: "bg-line-2" };
// a cap-to-baseline box, so a strip's text sits on its baseline wherever the font puts its ascent
const TRIM = "[text-box:trim-both_cap_alphabetic]";

export function DeckFrame({ info, label, children }: { info: FrameInfo; label: string; children: ReactNode }) {
  if (info.bare) return <>{children}</>;
  const right = info.backup ? PARTS.backup : info.number ? `${info.number.at} / ${info.number.of}` : null;
  return (
    <>
      {children}
      <div data-frame="header" className="absolute inset-x-0 top-0 h-[64px] bg-white">
        <img src="/aa-logo.svg" alt="" className="absolute left-[40px] top-[22px] h-[22px] w-auto" draggable={false} />
        {info.tracker && <Tracker info={info} />}
      </div>
      {info.footer && (
        <div
          data-frame="footer"
          className="absolute inset-x-0 bottom-0 h-[30px] bg-white text-[11px] font-medium uppercase leading-none tracking-[0.14em]"
          style={{ fontFamily: MONO, color: MUTED }}
        >
          {/* baselines at y 708; the right one hangs its trailing letter-space past x 1240, so its last letter ends there */}
          <span className={`absolute bottom-[12px] left-[40px] whitespace-nowrap ${TRIM}`}>{label}</span>
          {right && <span className={`absolute bottom-[12px] right-[40px] mr-[-0.14em] whitespace-nowrap ${TRIM}`}>{right}</span>}
        </div>
      )}
    </>
  );
}

/** The five topics in order. A name sits on a baseline at y 36, 8px above its segments, and is as wide as its words but never wider than
 * its column, so a name too long for its column shows as one whose scrollWidth passes its clientWidth (present.spec.ts checks every name,
 * each one lit, at a small and a large window). The names are set a touch tight, -0.02em: in Inter the longest, lit, is 180px untracked
 * against a 178px column, and tracked it is 174px; in Helvetica Neue or Arial it is narrower still. */
function Tracker({ info }: { info: FrameInfo }) {
  return (
    <ol data-tracker aria-label={copy.deckTopics} className="absolute left-[300px] top-0 grid h-full w-[940px] grid-cols-5 gap-x-[12px]">
      {TOPIC_ORDER.map((t) => {
        const lit = info.topic === t;
        return (
          <li key={t} data-topic={t} className="relative">
            <span
              data-topic-name
              aria-current={lit ? "step" : undefined}
              className={`absolute bottom-[28px] left-0 w-fit max-w-full whitespace-nowrap text-[12px] leading-none tracking-[-0.02em] ${TRIM} ${lit ? "font-semibold text-navy" : "font-medium"}`}
              style={lit ? undefined : { color: MUTED }}
            >
              {TOPICS[t].name}
            </span>
            <span aria-hidden="true" className="absolute inset-x-0 top-[44px] flex h-[3px] gap-[3px]">
              {info.segments[t].map((state, i) => (
                <span key={i} data-segment={state} className={`h-full min-w-0 flex-1 ${SEGMENT[state]}`} />
              ))}
            </span>
          </li>
        );
      })}
    </ol>
  );
}
