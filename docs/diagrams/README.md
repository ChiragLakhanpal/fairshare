# Diagrams for the presentation

American Airlines colors and fonts from the app's own theme, with the official AA logo in the corner of every image. Each
diagram is a live HTML page, and every slide image is in `export/` (2560 by 1440, 16:9). Six of them also come as an animated
page that steps forward one idea at a time. The deck at `/present` (the app's presentation mode, in `web/src/deck/`) shows
the figures as slides and steps the animated pages with its arrow keys.

## In the order they could be shown

| Section | Opener (hairline) | Diagram |
|---|---|---|
| Title | `hairline/title-b-airliner.html` (the chosen one; A and C stay as alternates) | |
| The system | `hairline/stack.html` | `01-system-exploded.html`: five layers and where each one lives (Databricks, AI Foundry, Microsoft). `01-system-exploded-animated.html` lifts one layer per arrow key. |
| The data | `hairline/opener-elevator.html` | `06-data-pipeline.html` where the numbers come from, `10-coverage.html` every agency by every month, `11-revenue-by-month.html` AA revenue by month, `14-what-was-planted.html` what was planted in the data and what cleaning did, `09-definitions.html` the seven numbers, `07-fair-share.html` what fair share means, `12-share-vs-fair.html` AA share against fair share for each agency, `08-why-it-moved.html` why a number moved |
| Trust | `hairline/opener-sieve.html` | `02-answer-checked.html`: what the account manager sees, and the checks behind the screen |
| Delegate | `hairline/opener-riffle.html` | `03-delegate.html`: agents draft, a person decides, then Dynamics 365 and Outlook |
| The value | `hairline/opener-query.html` | `04-journey-sales-director.html` and `05-journey-account-manager.html`: each step of the process as a sequence, with the real tools and tables |
| Proof | | `15-at-aa.html`: the five layers of `01`, each piece marked by what runs today, what is built but not deployed, and what waits on AA's Microsoft account, with every table beside the AA feed that would replace it |

There is no figure 13. `hairline/png/title-b.png` is the title slide image, and its caption is the talk title, set in
`hairline/src/pages.mjs`; `hairline/png/titles-abc.png` shows the three that were compared.

## The animated pages

`01`, `02`, `04`, `05`, `06` and `08` also come as `<name>-animated.html`: the same figure as its static page, in
diagram-design's reveal mode (`aa.animated()` in `src/aa.py`). The page plays once when it opens and then stays complete.
Each step brings in one idea. On `01` each layer lifts clear; on the other five the marks only fade in, and nothing
moves. The logo band, the headers or actors, the lifelines or axes, and the legend stay in place.

| Page | Steps | What each step brings in |
|---|---|---|
| `01-system-exploded-animated.html` | 5 | the app lifts clear, then the checks, the agents and the definitions; the last step shows the data and where each layer lives |
| `02-answer-checked-animated.html` | 4 | the account manager's row, the app's row, the work behind the screen with the verifier, the foundations |
| `04-journey-sales-director-animated.html` | 7 | the question, Genie and its rows, the change explained, the model's draft, the verifier, the answer with its query, the click on a number |
| `05-journey-account-manager-animated.html` | 7 | the nightly job's request, the fixed SQL, the writer's draft, the verifier, the waiting page and Monday's look, the approve branch, the reject branch |
| `06-data-pipeline-animated.html` | 7 | the sources, bronze, silver, gold, the numbers defined once, the readers, the one sentence on who can see what |
| `08-why-it-moved-animated.html` | 5 | September 2025, volume, mix, share, September 2026, each with the line that carries the total into it |

On its own, a page has Previous, Next, Play, Pause and Replay buttons, and the arrow keys, Home and End step it. With
reduced motion, or with no JavaScript, the whole figure shows at once. A figure that prints values from the data says
"synthetic data" in its logo band, and its animated page says it too.

**Embed mode.** The deck at `/present` loads an animated page in a frame and steps it with its own arrow keys. The page
carries no script of its own for that, because the plugin allows only its own controller. The deck waits until the
controller is ready, sets `data-embed` on the frame's `html` element, which hides the title, the note and the buttons and
fits the figure to the frame (`EMBED_CSS` in `src/aa.py`), then sends Home or End and the arrow keys to the figure. Which
slide uses which page is in `web/src/deck/slides.ts`. An animated page has no PNG of its own: the static page's export is
its thumbnail, which the deck shows until the frame is ready.

## Presenting

- On a slide, use the PNGs in `export/` and `hairline/png/`. The fonts are baked in. The SVGs in `export/` stay sharp at
  any size, but PowerPoint and Keynote draw their text in the right fonts only when Inter and Geist Mono are installed.
- Live, open the HTML in Chrome. On an animated page, the arrow keys step one idea per press; Space plays and pauses,
  R replays. The hairline pages play on their own until the pointer arrives; add `?still=1` to stop them at rest.

## Honest notes

- The CRM in the demo is a synthetic stand-in shaped like Dynamics 365 Sales, and every diagram that names it says so.
- The "today" line under each sequence is how the role was described in round one. Nothing shows hours saved, because none were measured.
- Every number on the data diagrams comes from a query in `src/deck_facts.py`. The same file writes `web/src/deck/facts.json`
  (each number with its SQL and its grain), which the deck at `/present` uses to fill its slides. A few numbers live only on
  Databricks or in a results file; they sit in that file as dated facts, each with its source and date.
- `deck_facts.py --print` lists every number next to its query, and a test fails when `facts.json` is stale.
- The seat shares behind fair share are made up, and the agency sales are synthetic. Every figure that prints values from
  the data says "synthetic data" in its logo band, through `aa.brand(tag=...)`, and `evals/test_labels.py` keeps the list.
- The Flight Symbol in title figure A is American Airlines' own mark.

## Rebuilding

The builders in `src/` write every file here, using the diagram-design plugin's own projection code and the
`american-airlines` profile that `.diagram-design` at the repo root points to. The builders that print numbers (`journeys.py`,
`data_diagrams.py`, `waterfall.py`, `definitions.py`, `coverage.py`, `revenue.py`, `share_fair.py` and `planted.py`) read them
from `deck_facts.py`, so they run in the repo's virtual environment (`.venv/bin/python`) on the local DuckDB build;
`deck_facts.py` sets `FAIRSHARE_BACKEND=duckdb` itself, so the laptop's `.env` pointing at Databricks does not matter.

```
FAIRSHARE_BACKEND=duckdb .venv/bin/python docs/diagrams/src/deck_facts.py   # every number: writes web/src/deck/facts.json
python3 docs/diagrams/src/exploded.py                 # 01 (both versions) and 15
python3 docs/diagrams/src/blueprint.py                # 02 (both versions)
python3 docs/diagrams/src/swimlane.py                 # 03
.venv/bin/python docs/diagrams/src/journeys.py        # 04, 05 (both versions)
.venv/bin/python docs/diagrams/src/data_diagrams.py   # 06 (both versions), 07
.venv/bin/python docs/diagrams/src/waterfall.py       # 08 (both versions)
.venv/bin/python docs/diagrams/src/definitions.py     # 09
.venv/bin/python docs/diagrams/src/coverage.py        # 10
.venv/bin/python docs/diagrams/src/revenue.py         # 11
.venv/bin/python docs/diagrams/src/share_fair.py      # 12
.venv/bin/python docs/diagrams/src/planted.py         # 14
node docs/diagrams/hairline/src/pages.mjs             # the hairline pages
python3 docs/diagrams/src/lint.py docs/diagrams/[01]*.html   # the skin lint; only the AA logo's own colors may differ
```

Exports, one file at a time (the PNG step uses the Playwright that `web/` already has):

```
python3 ~/.claude/plugins/cache/diagram-design/diagram-design/*/skills/diagram-design/scripts/export_svg.py docs/diagrams/02-answer-checked.html docs/diagrams/export/02-answer-checked.svg
NODE_PATH=web/node_modules node docs/diagrams/src/export_png.cjs docs/diagrams/02-answer-checked.html docs/diagrams/export/02-answer-checked.png
```

The PNGs in `hairline/png/` are screenshots of those pages at 1280 by 720 and scale 2, with `?still=1` and the page's live
readout (`#read`, the small word at the figure's top right) hidden. `pages.mjs` reads the hairline package from
`web/node_modules` and the custom figures from the `hairline-*.html` bench pages. Changing a figure in `hairline/src/` needs
hairline's own builder (`bunx skills add lucasmarkes/hairline`, then its `build.mjs`).
