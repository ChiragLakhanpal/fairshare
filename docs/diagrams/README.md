# Diagrams for the presentation

American Airlines colors and fonts from the app's own theme, with the official AA logo in the corner of every image. Each
diagram is a live HTML page, and every slide image is in `export/` (2560 by 1440, 16:9).

## In the order they could be shown

| Section | Opener (hairline) | Diagram |
|---|---|---|
| Title | `hairline/title-b-airliner.html` (the chosen one; A and C stay as alternates) | |
| The system | `hairline/stack.html` | `01-system-exploded.html`: five layers and where each one lives (Databricks, AI Foundry, Microsoft). `01-system-exploded-animated.html` lifts one layer per arrow key. |
| The data | `hairline/opener-elevator.html` | `06-data-pipeline.html` where the numbers come from, `09-definitions.html` the seven numbers, `07-fair-share.html` what fair share means, `08-why-it-moved.html` why a number moved |
| Trust | `hairline/opener-sieve.html` | `02-answer-checked.html`: what the account manager sees, and the checks behind the screen |
| Delegate | `hairline/opener-riffle.html` | `03-delegate.html`: agents draft, a person decides, then Dynamics 365 and Outlook |
| The value | `hairline/opener-query.html` | `04-journey-sales-director.html` and `05-journey-account-manager.html`: each step of the process as a sequence, with the real tools and tables |

`hairline/png/title-b.png` is the title slide image; `hairline/png/titles-abc.png` shows the three that were compared.

## Presenting

- On a slide, use the PNGs in `export/` and `hairline/png/`. The fonts are baked in. The SVGs in `export/` stay sharp at
  any size, but PowerPoint and Keynote draw their text in the right fonts only when Inter and Geist Mono are installed.
- Live, open the HTML in Chrome. On the animated stack, the arrow keys lift one layer per press; Space plays and pauses,
  R replays. The hairline pages play on their own until the pointer arrives; add `?still=1` to stop them at rest.

## Honest notes

- The CRM in the demo is a synthetic stand-in shaped like Dynamics 365 Sales, and every diagram that names it says so.
- The "today" line under each sequence is how the role was described in round one. Nothing shows hours saved, because none were measured.
- Every number on the data diagrams comes from a query; `src/data_numbers.py` and `src/data_numbers_2.py` print them again.
- The Flight Symbol in title figure A is American Airlines' own mark.

## Rebuilding

The builders in `src/` write every file here, using the diagram-design plugin's own projection code and the
`american-airlines` profile that `.diagram-design` at the repo root points to.

```
python3 docs/diagrams/src/exploded.py        # 01, both versions
python3 docs/diagrams/src/blueprint.py       # 02
python3 docs/diagrams/src/swimlane.py        # 03
python3 docs/diagrams/src/journeys.py        # 04, 05
python3 docs/diagrams/src/data_diagrams.py   # 06, 07
python3 docs/diagrams/src/waterfall.py       # 08
python3 docs/diagrams/src/definitions.py     # 09
node docs/diagrams/hairline/src/pages.mjs    # the hairline pages
python3 docs/diagrams/src/lint.py docs/diagrams/0*.html   # the skin lint; only the AA logo's own colors may differ
```

Exports, one file at a time (the PNG step uses the Playwright that `web/` already has):

```
python3 ~/.claude/plugins/cache/diagram-design/diagram-design/*/skills/diagram-design/scripts/export_svg.py docs/diagrams/02-answer-checked.html docs/diagrams/export/02-answer-checked.svg
NODE_PATH=web/node_modules node docs/diagrams/src/export_png.cjs docs/diagrams/02-answer-checked.html docs/diagrams/export/02-answer-checked.png
```

`pages.mjs` reads the hairline package from `web/node_modules` and the custom figures from the `hairline-*.html` bench
pages. Changing a figure in `hairline/src/` needs hairline's own builder (`bunx skills add lucasmarkes/hairline`, then its
`build.mjs`).
