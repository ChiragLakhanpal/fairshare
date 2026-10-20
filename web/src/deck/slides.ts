// The deck's slides in the order a talk walks them. For now two: the animated system diagram, then an image. They prove
// on the App that a press steps the framed diagram from outside its frame and then moves the deck. Assets are keys of
// images and pages in assets.ts.
import type { Slide } from "../lib/deck";

export const slides: Slide[] = [
  {
    id: "system", part: "built", kind: "animated", title: "The system", min: 2.25, short: 1.5,
    asset: "01-system-exploded-animated.html", thumb: "export/01-system-exploded.png",
    note: "Five layers sit under every answer. The blue one is the checks. Before anyone sees a number, the app matches it to the rows of a query.",
  },
  {
    id: "numbers", part: "data", kind: "image", title: "The seven numbers", min: 1.5,
    asset: "export/09-definitions.png",
    note: "These are the seven numbers the app answers with. Each one is defined in one place.",
  },
];
