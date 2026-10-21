// The type ramp of the deck's native slides at the 1280 by 720 stage, written once: every native layout (layouts.tsx) takes its type
// from here, and the frame (Frame.tsx) its mono face and muted color. Six kinds of text: the title (40px), the body (28px; the heads of
// tiles, results, checks and topics are the body at weight 600), a secondary note (20px), a display number (56px), the mono label (12px)
// and a miss (20px). The other entries are these sizes at another weight or color. Titles are navy, the body ink, notes and labels the
// figures' muted text, display numbers the figures' blue text, and red is only for a miss. Spacing comes only from 8, 16, 24, 32, 48
// and 64 px.
//
// The steps: a native slide shows its title on arrival, and each item comes in on a press. An item not reached yet keeps its place,
// invisible to the eye and to assistive tech (UNREACHED). It arrives with a 320ms fade from 8px below (SHOWN), and when the next one
// arrives its text recedes to the muted color at the same size, a 320ms change of color, so the newest item leads (STEP). Under reduced
// motion nothing moves or fades: the items still step, at once.

/** The figures' mono face, muted text and blue text (MONO, MUTED and ACCENT in docs/diagrams/src/aa.py), for inline styles. */
export const MONO = "'Geist Mono', ui-monospace, monospace";
export const MUTED = "#5a7181";
export const BLUE_TEXT = "#006cbf";

// each class names its own size, so Tailwind finds it in this file
const SIZE = {
  title: "text-[40px] leading-[1.15] tracking-[-0.01em]",
  body: "text-[28px] leading-[1.35]",
  note: "text-[20px] leading-[1.45]",
  display: "text-[56px] leading-none",
};

/** The slide's title: at most two lines, balanced when it takes two. */
export const TITLE = `${SIZE.title} font-semibold text-navy text-balance`;
/** A point, a line of a demo or of the close. */
export const BODY = `${SIZE.body} font-normal text-ink`;
/** The head of a tile, a result, a check or a topic. */
export const HEAD = `${SIZE.body} font-semibold text-ink`;
/** The question to the room, in the body's size, set apart in navy. */
export const ASK = `${SIZE.body} font-semibold text-navy`;
/** A secondary note: what a tile, a result, a check or a topic says under its head. */
export const NOTE = `${SIZE.note} font-normal text-[#5a7181]`;
/** A result's number. */
export const DISPLAY = `${SIZE.display} font-semibold text-[#006cbf]`;
/** The figures' mono face, for labels and for the names and examples in a table. */
export const MONO_FACE = "font-['Geist_Mono',ui-monospace,monospace]";
/** A label in the figures' mono face: a tag, a table's column headings. */
export const LABEL = `${MONO_FACE} text-[12px] font-medium uppercase tracking-[0.14em] text-[#5a7181]`;
/** A result's miss, the one red text. */
export const MISS = `${SIZE.note} font-normal text-red`;
/** A topic's number on the agenda, in the body's size: blue on the newest topic, like a point's dot. */
export const NUMBER = `${SIZE.body} font-semibold text-[#006cbf] tabular-nums`;
/** A table's text: the note's size in ink, set as tight as the body (a row is not running prose). A table too tall for the slide zooms out
 * as a whole. */
export const TABLE = "text-[20px] leading-[1.35] font-normal text-ink";
/** A demo button's words, at the note's size. */
export const ACTION = `${SIZE.note} font-semibold`;
/** A point's or a check's marker box: one body line tall, so the mark in it centers on the first line beside it. */
export const MARKER = "flex h-[1.35em] shrink-0 items-center text-[28px]";

/** An item a press brings in. Its state is in its attributes: aria-hidden until its step, data-current on its step, and data-receded
 * after it, when every text in it takes the muted color (a rule more specific than the text's own color, so a display number or a miss
 * recedes too). It moves in with an opacity, a rise and a visibility change, and its texts change color, each over 320ms. */
export const STEP = [
  "transition-[opacity,translate,visibility,color,background-color,border-color] duration-[320ms] ease-out motion-reduce:transition-none",
  "[&_*]:transition-colors [&_*]:duration-[320ms] [&_*]:ease-out motion-reduce:[&_*]:transition-none",
  "[&[data-receded]]:text-[#5a7181] [&[data-receded]_*]:text-[#5a7181]",
].join(" ");
/** An item that has arrived. */
export const SHOWN = "visible opacity-100 translate-none";
/** An item still to come: in its place, invisible, and 8px low, so it rises as it fades in. */
export const UNREACHED = "invisible opacity-0 translate-y-[8px] motion-reduce:translate-none";
