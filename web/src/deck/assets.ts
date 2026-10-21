// Every figure the deck can show, as URLs Vite serves in dev and writes into dist/assets with a hash: the PNGs (image
// slides, and the thumbs under frames) and the HTML pages that go in frames. Keys are paths under docs/diagrams/, such as
// "export/08-why-it-moved.png" or "01-system-exploded-animated.html". A glob that matches nothing returns an empty map
// without an error, so a wrong key shows up only as a missing figure.
const PREFIX = "../../../docs/diagrams/";
const cut = (m: Record<string, string>) => Object.fromEntries(Object.entries(m).map(([k, v]) => [k.slice(PREFIX.length), v]));

// less the PNGs that no slide shows: the glossary and coverage figures that left the deck, the two title pages that were not chosen, and the
// picture of all three titles (deck.test.ts holds the build to the images the slides show)
export const images: Record<string, string> = cut(
  import.meta.glob<string>(
    [
      "../../../docs/diagrams/export/*.png",
      "!../../../docs/diagrams/export/{09-definitions,10-coverage}.png",
      "../../../docs/diagrams/hairline/png/*.png",
      "!../../../docs/diagrams/hairline/png/{title-a,title-c,titles-abc}.png",
    ],
    { query: "?url", import: "default", eager: true },
  ),
);

// the hairline pages by name: hairline/*.html would also ship the hairline-* bench pages
export const pages: Record<string, string> = cut(
  import.meta.glob<string>(["../../../docs/diagrams/*-animated.html", "../../../docs/diagrams/hairline/{title-b-airliner,stack,opener-*}.html"], {
    query: "?url",
    import: "default",
    eager: true,
  }),
);
