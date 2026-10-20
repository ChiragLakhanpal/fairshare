// Every figure the deck can show, as URLs Vite serves in dev and writes into dist/assets with a hash: the PNGs (image
// slides, and the thumbs under frames) and the HTML pages that go in frames. Keys are paths under docs/diagrams/, such as
// "export/09-definitions.png" or "01-system-exploded-animated.html". A glob that matches nothing returns an empty map
// without an error, so a wrong key shows up only as a missing figure.
const PREFIX = "../../../docs/diagrams/";
const cut = (m: Record<string, string>) => Object.fromEntries(Object.entries(m).map(([k, v]) => [k.slice(PREFIX.length), v]));

export const images: Record<string, string> = cut(
  import.meta.glob<string>(["../../../docs/diagrams/export/*.png", "../../../docs/diagrams/hairline/png/*.png"], { query: "?url", import: "default", eager: true }),
);

// the hairline pages by name: hairline/*.html would also ship the hairline-* bench pages
export const pages: Record<string, string> = cut(
  import.meta.glob<string>(["../../../docs/diagrams/*-animated.html", "../../../docs/diagrams/hairline/{title-b-airliner,stack,opener-*}.html"], {
    query: "?url",
    import: "default",
    eager: true,
  }),
);
