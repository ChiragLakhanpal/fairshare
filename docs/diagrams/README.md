# Diagrams for the presentation

American Airlines colors and fonts from the app's own theme, with the official AA logo in the corner of every image. Each
diagram is a live HTML page, and every figure's slide image is in `export/` (2560 by 1440, 16:9). Twelve of them also come as an
animated page that steps forward one idea at a time. The deck at `/present` (the app's presentation mode, in
`web/src/deck/`) shows the figures as slides and steps the animated pages with its arrow keys. Two other PNGs sit in
`export/`: the stills, which are screenshots of the running app, not figures (see "The two stills").

## The figures in the order of the talk

The talk is five topics between a welcome and a thanks, and this is the order the deck shows the figures in. `web/src/deck/slides.ts`
has the slide ids and what the speaker says on each. An opener is a hairline page that plays on its own. A figure with an animated
page takes one press for each of its steps (the table under "The animated pages" says what each press brings in). The slides in
between, the live demos and the text slides, are native to the deck and not drawn here.

| Topic | Slide | Opener or figure | Steps |
|---|---|---|---|
| Welcome | `welcome` | `hairline/title-b-airliner.html`, the chosen title (A and C stay as alternates) | |
| Ask and Delegate | `query-opener` | `hairline/opener-query.html` | |
| | `director` | `04-journey-sales-director.html`: what ran behind the Harbor answer, from the sales director's side | 7 |
| | `riffle-opener` | `hairline/opener-riffle.html` | |
| | `delegate` | `03-delegate.html`: agents draft and a person decides, then the CRM stand-in and Outlook | 6 |
| Where the numbers come from | `stack-opener` | `hairline/stack.html` | |
| | `system` | `01-system-exploded.html`: five layers and where each one lives (Databricks, AI Foundry, Microsoft) | 5 |
| | `elevator-opener` | `hairline/opener-elevator.html` | |
| | `pipeline` | `06-data-pipeline.html`: where the numbers come from | 7 |
| | `revenue` | `11-revenue-by-month.html`: AA revenue by month | 4 |
| | `numbers` | `09a-numbers-share.html`: AA revenue, AA share and fair share, each with how it is calculated | 4 |
| | `gaps` | `09b-numbers-gaps.html`: the other four numbers, the same way | 5 |
| | `share-fair` | `12-share-vs-fair.html`: AA share against fair share for each agency | 5 |
| | `moved` | `08-why-it-moved.html`: why a number moved | 5 |
| Checks and misses | `sieve-opener` | `hairline/opener-sieve.html` | |
| | `checked` | `02-answer-checked.html`: what the account manager sees, and the checks behind the screen | 4 |
| Starting at AA | `at-aa` | `15-at-aa.html`: the five layers of `01`, each piece marked by what runs today, what is built but not deployed, and what waits on AA's Microsoft account, with every table beside the AA feed that would replace it | 7 |
| Backup | `manager` | `05-journey-account-manager.html`: an account manager's Monday before agency calls | 7 |
| | `fair` | `07-fair-share.html`: what fair share means (its PNG) | |
| | `planted` | `14-what-was-planted.html`: what was planted in the data and what cleaning did (its PNG) | |
| | `ask-still`, `precall-still` | the two stills | |

`09-definitions.html` (the seven numbers on one page) and `10-coverage.html` (every agency by every month) are on no slide now: the
first became `09a` and `09b`, and the second left the deck. There is no figure 13. `hairline/png/title-b.png` is the title slide
image, and its caption is the talk title, set in `hairline/src/pages.mjs`; `hairline/png/titles-abc.png` shows the three that were
compared. Each opener's caption in `pages.mjs` is the title of its slide, and `web/src/lib/deck.test.ts` keeps the two equal, in the
pages the builder wrote as well as in `pages.mjs`.

## The animated pages

`01`, `02`, `03`, `04`, `05`, `06`, `08`, `09a`, `09b`, `11`, `12` and `15` also come as `<name>-animated.html`: the same figure as its
static page, in diagram-design's reveal mode (`aa.animated()` in `src/aa.py`). On its own a page plays once when it opens and then
stays complete. Each step brings in one idea: on `01` each layer lifts clear, and on the other eleven the marks only fade in.

A page's structure shows from the start, so the room knows what kind of picture it is looking at: the headers, the lane labels or
actors, the lifelines, the axes, the tier cards, a chart's lines and the legend. What gives the point away waits for its step: the
legend key that names the focal item or the check, a caption, a payoff line and a chart's notes. On `15` the legend does not show
on arrival: it comes in an entry at a time, each with the pieces it marks, and the first brings the legend's rule and its heading too.

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
| `11-revenue-by-month-animated.html` | 4 | the band over March and April 2026 with each month's net change against 2025, then one note a press beside it: Sunbelt sent nothing, Harbor's AA revenue fell, the other agencies grew in total (the title, the axes and the source line show from the start, and both lines draw in with their dots and their years) |
| `12-share-vs-fair-animated.html` | 5 | fair share's hollow dots with their name, the note under the chart that says why fair share barely moves (every agency spreads its sales over the same twelve routes in similar proportions) and where the seat shares come from (T-100, with August and September 2026 repeating 2025), AA share's solid dots with their name and connectors and the subtitle's second sentence, which says the rows run from furthest above fair share to furthest below, then one callout a press: the agency furthest above fair share (the top row) and the one furthest below (the bottom row), each with its two values (the title, the subtitle's first sentence, the agencies' names, the axis and the source line show from the start) |
| `15-at-aa-animated.html` | 7 | presses 1 to 3 bring one kind of piece each under the layers' names, with its entry in the legend: what runs today (seven pieces, with the legend's rule and its heading), what is built but not deployed (one) and what waits on AA's Microsoft account (four); presses 4 to 7 bring the AA feed beside each table in the demo, hardest first: the agency's sales with the note on why they are the hardest, the seat capacity, the bookings with the agreements, and the CRM with the goals (on arrival the five layers at rest as on `01`'s static page, their names, the headings and the demo's tables show, and no piece, legend entry or feed does) |

On its own, a page has Previous, Next, Play, Pause and Replay buttons, and the arrow keys, Home and End step it. With
reduced motion, or with no JavaScript, the whole figure shows at once on its own; in the deck it still steps (see "Under reduced
motion" below). A figure that prints values from the data says "synthetic data" in its logo band, and its animated page says it too.

### In the deck: embed mode

The deck at `/present` loads an animated page in a frame and steps it with its own arrow keys. The page carries no script of its own
for that, because the plugin allows only its own controller. The deck waits until the controller is ready, sets `data-embed` on the
frame's `html` element, then sends Home or End and the arrow keys to the figure. `data-embed` switches on `EMBED_CSS` (`src/aa.py`),
which every animated page carries, so a change to it means rebuilding all twelve. What it does:

- **A step that has not come is invisible.** An item the controller has not reached is at opacity 0, not at the plugin's faded
  look, which would still give the end away. `01`'s five layers are the exception: they stay in place, assembled, and lift on each
  press. A slide arrives on its first step with no fade. Until the frame is ready the slide shows nothing of the figure, and the
  static page's PNG (the animated page's thumbnail) stands in only if the frame is still not ready after `FRAME_FALLBACK_MS`
  (`web/src/lib/deck.ts`).
- **The logo band is hidden**, with the eyebrow, the title and the buttons. The deck's frame draws the one logo, so no figure
  shows a band of its own in the deck. The standalone pages and exports keep theirs.
- **The figure fills the frame, between y 64 and y 680.** The page fits the figure to the frame at its width. The frame's header
  covers y 0 to 64 of the figure's 1280 by 720 view box, where its band sat, and its footer y 690 to 720, so every figure the deck
  shows keeps its content between y 64 and y 680, in both the animated page and the static one. `evals/test_figures_in_deck.py`
  holds it to that.
- **Charts draw in once,** when the frame shows, through two classes. `draw-line`, on a path with `pathLength="1"`, traces it left
  to right over 900ms. `draw-dot` fades a mark in over 300ms, after a 900ms delay, so it follows the line. `11` uses both: each line
  traces itself, and its dots and its years come in after it. On a backward arrival, after a load and after the browser restores the
  deck from its cache, a chart shows drawn: the deck sends End and finishes every animation and transition in the page (`arrive` in
  `web/src/lib/deck.ts`), so nothing plays out in front of the room. Under reduced motion a chart shows drawn on every arrival.
- **Under reduced motion the steps still step,** as a native slide's do, with nothing moving. The plugin's own rule for reduced motion
  shows every item and stands `01`'s layers where their lift takes them. In the deck an item not reached yet stays unseen over that
  rule, a press brings its step whole and at once, with no fade, and on `01` the layers stand still while each press brings the next
  layer's name. The deck sends Home or End as it does with motion on (`arrivalKey` in `web/src/lib/deck.ts`).
- **The newest item leads.** An item marked `data-recede` (the notes on `11`, the cards on `09a` and `09b`, the note under the chart
  and the two callouts on `12`, every step on `15`) has its words in ink while its press is the current one, and in the muted text
  once the next press comes. A mark in it marked `data-lead` (a card's outline on `09a` and `09b`) is outlined in blue only while its
  item is current, as a native slide's newest tile is. A text marked `data-keep` keeps the color it is drawn in, so AA share's
  values on `12` stay blue.

Which slide uses which page is in `web/src/deck/slides.ts`.

## The two stills

`export/ask-still.png` and `export/precall-still.png` are not built from HTML. They are screenshots of a good run on the
Databricks App, kept for the two backup slides `ask-still` and `precall-still` (flagged `still: true` in
`web/src/deck/slides.ts`, which the deck draws full bleed with no frame, since each already carries the app's own top bar), for
when a live demo stalls:

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
- The seat shares behind fair share are the DOT's T-100 data (August and September 2026 repeat 2025 until the DOT publishes
  them), and the agency sales are synthetic. Every figure that prints values from
  the data says "synthetic data" in its logo band, through `aa.brand(tag=...)`, and `evals/test_labels.py` keeps the list. In the
  deck the band is hidden, and the frame's footer says "Synthetic data" on every slide that shows numbers from the made-up data;
  the two table slides that show only the T-100 seats (`seats` and `dict-seats`) keep the talk's title there (`showsData` in
  `web/src/lib/deck.ts`).
- The Flight Symbol in title figure A is American Airlines' own mark.

## Rebuilding

The builders in `src/` write every file here, using the diagram-design plugin's own projection code and the
`american-airlines` profile that `.diagram-design` at the repo root points to. The builders that print numbers (`exploded.py`,
`blueprint.py`, `journeys.py`, `data_diagrams.py`, `waterfall.py`, `definitions.py`, `coverage.py`, `revenue.py`, `share_fair.py` and
`planted.py`) read them from `deck_facts.py`, so they run in the repo's virtual environment (`.venv/bin/python`) on the local DuckDB build;
`deck_facts.py` sets `FAIRSHARE_BACKEND=duckdb` itself, so the laptop's `.env` pointing at Databricks does not matter.

```
FAIRSHARE_BACKEND=duckdb .venv/bin/python docs/diagrams/src/deck_facts.py   # every number: writes web/src/deck/facts.json
.venv/bin/python docs/diagrams/src/exploded.py        # 01 and 15 (both versions each)
.venv/bin/python docs/diagrams/src/blueprint.py       # 02 (both versions)
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
