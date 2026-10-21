# Diagrams for the presentation

American Airlines colors and fonts from the app's own theme, with the official AA logo in the corner of every image. Each
diagram is a live HTML page, and every figure's slide image is in `export/` (2560 by 1440, 16:9). Eleven of them also come as an
animated page that steps forward one idea at a time. The deck at `/present` (the app's presentation mode, in
`web/src/deck/`) shows the figures as slides and steps the animated pages with its arrow keys. Two other PNGs sit in
`export/`: the stills, which are screenshots of the running app, not figures (see "The two stills").

## In the order they could be shown

| Section | Opener (hairline) | Diagram |
|---|---|---|
| Title | `hairline/title-b-airliner.html` (the chosen one; A and C stay as alternates) | |
| The system | `hairline/stack.html` | `01-system-exploded.html`: five layers and where each one lives (Databricks, AI Foundry, Microsoft). `01-system-exploded-animated.html` lifts one layer per arrow key. |
| The data | `hairline/opener-elevator.html` | `06-data-pipeline.html` where the numbers come from, `10-coverage.html` every agency by every month, `11-revenue-by-month.html` AA revenue by month, `14-what-was-planted.html` what was planted in the data and what cleaning did, `09-definitions.html` the seven numbers on one page, `09a-numbers-share.html` and `09b-numbers-gaps.html` the same seven over two slides, each with how it is calculated, `07-fair-share.html` what fair share means, `12-share-vs-fair.html` AA share against fair share for each agency, `08-why-it-moved.html` why a number moved |
| Trust | `hairline/opener-sieve.html` | `02-answer-checked.html`: what the account manager sees, and the checks behind the screen |
| Delegate | `hairline/opener-riffle.html` | `03-delegate.html`: agents draft, a person decides, then the CRM stand-in and Outlook; `03-delegate-animated.html` runs the flow one stage a press |
| The value | `hairline/opener-query.html` | `04-journey-sales-director.html` and `05-journey-account-manager.html`: each step of the process as a sequence, with the real tools and tables |
| Proof | | `15-at-aa.html`: the five layers of `01`, each piece marked by what runs today, what is built but not deployed, and what waits on AA's Microsoft account, with every table beside the AA feed that would replace it |

There is no figure 13. `hairline/png/title-b.png` is the title slide image, and its caption is the talk title, set in
`hairline/src/pages.mjs`; `hairline/png/titles-abc.png` shows the three that were compared.

## The animated pages

`01`, `02`, `03`, `04`, `05`, `06`, `08`, `09a`, `09b`, `11` and `12` also come as `<name>-animated.html`: the same figure as its
static page, in diagram-design's reveal mode (`aa.animated()` in `src/aa.py`). The page plays once when it opens and then stays
complete. Each step brings in one idea. On `01` each layer lifts clear; on the other ten the marks only fade in, and nothing
moves. The logo band, the headers, lane labels or actors, the lifelines, axes or tier cards, a chart's lines, and the legend
stay in place, except what gives the point away: the legend key that names the focal item or the check, a caption, a payoff
line and a chart's notes come in with the step they belong to.

| Page | Steps | What each step brings in |
|---|---|---|
| `01-system-exploded-animated.html` | 5 | the app lifts clear, then the checks, the agents and the definitions; the last step shows the data, where each layer lives and the caption |
| `02-answer-checked-animated.html` | 4 | the account manager's row, the app's row, the work behind the screen with the verifier, its caption and its legend key, the foundations (each lane's label shows from the start) |
| `03-delegate-animated.html` | 6 | the nightly job, the fixed queries that pull the facts, the AI Foundry writer that drafts from those facts only, the verifier with the page that waits for a decision, the handoff to the account manager who reviews and approves or rejects with the legend keys for the handoff and the decision, then the CRM stand-in and Outlook with the caption (the five lanes with their names and the rest of the legend show from the start) |
| `04-journey-sales-director-animated.html` | 7 | the question, Genie and its rows, the change explained, the model's draft, the verifier with the legend key for the check, the answer with its query, the click on a number and the payoff line |
| `05-journey-account-manager-animated.html` | 7 | the nightly job's request, the fixed SQL, the writer's draft, the verifier with the legend key for the check, the waiting page and Monday's look, the approve branch, the reject branch and the payoff line |
| `06-data-pipeline-animated.html` | 7 | the sources, then what bronze, silver, gold and the definitions hold, the readers, the one sentence on who can see what (the two headings and the four tier cards, each with its name and schema, show from the start) |
| `08-why-it-moved-animated.html` | 5 | September 2025, volume, the shift between routes (mix) with its note, share with the callout and its legend key, September 2026 with the sum, each with the line that carries the total into it |
| `09a-numbers-share-animated.html` | 4 | AA revenue, AA share and fair share, a card a press, each with how it is calculated and its value for Harbor in Sep 2026, then where the seven numbers live and why that matters (the title, the heading over the values, and each card's frame and name show from the start) |
| `09b-numbers-gaps-animated.html` | 5 | the share gap in points, the share gap in dollars, year over year and pace, a card a press in the same way, then the same close |
| `11-revenue-by-month-animated.html` | 4 | the band over March and April 2026 with each month's net change against 2025, then one note a press beside it: Sunbelt sent nothing, Harbor's AA revenue fell, the other agencies grew (the title, the axes, both lines with their years and the source line show from the start) |
| `12-share-vs-fair-animated.html` | 5 | fair share's hollow dots with their name, the note under the chart that says why fair share barely moves (every agency spreads its sales over the same routes in similar proportions) and that the seat shares are made up, AA share's solid dots with their name and connectors, then one callout a press: the agency furthest above fair share (the top row) and the one furthest below (the bottom row), each with its two values (the title, the agencies' names, the axis and the source line show from the start) |

On its own, a page has Previous, Next, Play, Pause and Replay buttons, and the arrow keys, Home and End step it. With
reduced motion, or with no JavaScript, the whole figure shows at once. A figure that prints values from the data says
"synthetic data" in its logo band, and its animated page says it too.

**Embed mode.** The deck at `/present` loads an animated page in a frame and steps it with its own arrow keys. The page
carries no script of its own for that, because the plugin allows only its own controller. The deck waits until the
controller is ready, sets `data-embed` on the frame's `html` element, which hides the title, the note, the buttons and
the logo band, hides every step the controller has not reached (on its own a page keeps the plugin's faded look), and
fits the figure to the frame (`EMBED_CSS` in `src/aa.py`), then sends Home or End and the arrow keys to the figure. A
chart draws in once, when the frame shows: on `11` each line traces itself left to right over 900ms, and its dots and
its year come in after it; under reduced motion, and on a backward arrival or a load, it shows drawn. The newest item
leads: an item marked `data-recede` (the notes on `11`, the cards on `09a` and `09b`, the note under the chart and the
two callouts on `12`) has its words in ink while its press is the current one, and on `09a` and `09b` its card is
outlined in blue, as a native slide's newest tile is; when the next press comes, its words recede to the muted text and
the outline goes. A text in it marked `data-keep` keeps the color it is drawn in, so AA share's values on `12` stay
blue. Which slide uses which page is in `web/src/deck/slides.ts`. An animated page has no PNG of its own: the static
page's export is its thumbnail, which the deck shows only when the frame is still not ready after `FRAME_FALLBACK_MS`
(`web/src/lib/deck.ts`); until then the slide shows nothing of the figure. In the deck a figure keeps its content
between y 64 and y 680, clear of the frame's header and footer, and `evals/test_figures_in_deck.py` holds every figure
the deck shows to that.

## The two stills

`export/ask-still.png` and `export/precall-still.png` are not built from HTML. They are screenshots of a good run on the
Databricks App, kept for the two backup slides `ask-still` and `precall-still` (flagged `still: true` in
`web/src/deck/slides.ts`, which draws no part label over them), for when a live demo stalls:

- `ask-still.png`: the Harbor question answered in Ask, with every number checked.
- `precall-still.png`: a pre-call page that the nightly job wrote, with the pack's list beside it.

Each is 2560 by 1440, like the figures: a 1280 by 720 window at device scale 2, the size of the deck's stage. They show the
signed-in line in the sidebar, as the room would see it. Retake one when the app, its copy or the data changes, or when a
better run turns up:

1. Pick a good run on the App, signed in. For Ask, ask "Why is Harbor Business Travel down in September?" until an answer
   keeps all its sentences (no "I removed one sentence ..." or "I removed 2 sentences ..." note) with exact dollar figures, and
   check its numbers against `web/src/deck/facts.json`. For the pre-call still, open Delegate's pre-call pack and pick a page the
   nightly job wrote, whose paragraphs have every comma and period, and whose possessives keep their apostrophes. The page's
   "Version of" line gives only its day, time and scope, not who ran it. The run behind it does: `GET /api/agents/runs/<run_id>`
   (the page's `run_id` is in `GET /api/agents`) answers `requested_by: "fairshare nightly"` for the job, and the person's email
   for a run started in the app.
2. Frame it at 1280 by 720 and device scale 2: in Chrome's developer tools, switch on the device toolbar, choose Responsive,
   set 1280 by 720 and a device pixel ratio of 2. Scroll so that no line sits half hidden under the Approve bar or the question
   bar, and the list's last row is not cut. Keep the pointer off the numbers, so no tooltip shows.
3. Capture the whole viewport ("Capture screenshot" in the developer tools' command menu) and save it over the file in
   `export/`. A tool that caps screenshot size can take four overlapping tiles of the window instead, at native pixels, and
   join them where they match exactly.
4. From the repo root, run `(cd web && bun run test && bun run build)` (the asset check finds both files), then compare each
   built copy with the file (`cmp web/dist/assets/ask-still-*.png docs/diagrams/export/ask-still.png`, and the same for the
   pre-call one), deploy with `.venv/bin/python lakehouse/app_deploy.py deploy`, and look at both slides on the App.

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
python3 docs/diagrams/src/swimlane.py                 # 03 (both versions)
.venv/bin/python docs/diagrams/src/journeys.py        # 04, 05 (both versions)
.venv/bin/python docs/diagrams/src/data_diagrams.py   # 06 (both versions), 07
.venv/bin/python docs/diagrams/src/waterfall.py       # 08 (both versions)
.venv/bin/python docs/diagrams/src/definitions.py     # 09, and 09a and 09b (both versions)
.venv/bin/python docs/diagrams/src/coverage.py        # 10
.venv/bin/python docs/diagrams/src/revenue.py         # 11 (both versions)
.venv/bin/python docs/diagrams/src/share_fair.py      # 12 (both versions)
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
