# The /present deck, retold: implementation plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Retell the `/present` deck as five topics between three bookends, show nothing before it is introduced, give every slide one dominant element inside a frame with the AA logo, a topic tracker and slide numbers, and replace `measured` with guardrails and evals.

**Architecture:** The deck model in `web/src/lib/deck.ts` gains topics, a frame description and native steps. A new `web/src/deck/Frame.tsx` draws the header and footer, and `layouts.tsx` draws stepped native layouts on one type ramp. `Present.tsx` steps native slides the way it already steps framed diagrams. In `docs/diagrams/src`, five figures gain animated pages, give-away legends and captions move into steps, and the embed CSS in `aa.py` hides unreached items and the figure's own logo band inside the deck.

**Tech Stack:** React 19, TypeScript, Tailwind v4, Vitest and Playwright in `web/` (bun, no npm); Python figure builders on the diagram-design plugin's reveal mode, with numbers from DuckDB through `docs/diagrams/src/deck_facts.py`.

**Spec:** `docs/superpowers/specs/2026-10-20-deck-redesign-design.md`. Read it before any task. It holds the approved content (topic names, guardrails, evals, bookends, the seven definitions) that tasks below cite instead of repeating.

## Global Constraints

- Repo root R = `/Users/chiraglakhanpal/Downloads/Chirag Lakhanpal/Chirag Lakhanpal/Explore/fairshare`, branch `deck-redesign`. One commit per task, ending with the line `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`. Never push, never touch `main`.
- Never open, print or log `.env`. The interviewer blocklist lives there as `FAIRSHARE_DECK_BLOCKLIST`; `deck.test.ts` reads it. Roles only ("the sales director", "the data lead"), never names.
- The five topics, verbatim, name then line:
  1. Two slow steps. What I heard in round one about share questions and pre-call packs.
  2. Ask and Delegate. The app answers a share question and drafts a pre-call pack, live.
  3. Where the numbers come from. The data behind the seven numbers, and why Harbor fell in September.
  4. Checks and misses. How the app checks each number, what the tests found, and what it can't do yet.
  5. Starting at AA. The same layers on AA's own data, and the first four steps.
- Colors: the tokens in `web/src/styles.css` (ink `#36495a`, ink-2 `#627a88`, line `#d0dae0`, line-2 `#e6ebef`, surface `#f2f5f8`, blue `#0078d2`, navy `#00467f`, red `#c30019`, tint `#e6f1fb`, tint-line `#b9d6ef`, grey `#9da6ab`) plus the figure profile's text colors `#006cbf` (blue text), `#5a7181` (muted text), `#566d7b` (soft text). Blue text uses `#006cbf`, muted text `#5a7181`; the lighter values are for fills, rules and large type only. Red only for a cut or a miss. No other colors, no gradients, no shadows on slides.
- Fonts: `--font-sans` (American Sans, falling back to Inter) for everything but labels; Geist Mono for labels, the footer and figure tags.
- The type ramp for native slides at the 1280 by 720 stage (one module, `web/src/deck/ramp.ts`, every native layout reads it):
  - title 40px, weight 600, line-height 1.15, letter-spacing -0.01em, navy, at most two lines
  - body 28px, weight 400, line-height 1.35, ink (heads of tiles and results: 28px, weight 600)
  - note 20px, weight 400, line-height 1.45, `#5a7181`
  - display 56px, weight 600, line-height 1, `#006cbf`
  - label 12px Geist Mono, weight 500, uppercase, letter-spacing 0.14em, `#5a7181`
  - miss 20px, weight 400, line-height 1.45, red
  - receded: an earlier step's text turns `#5a7181` and keeps its size
  - spacing only from 8, 16, 24, 32, 48, 64 px
- The frame on the 1280 by 720 stage:
  - header strip y 0 to 64, white. AA logo (`/aa-logo.svg`) at x 40, y 22, height 22. Tracker from x 300 to x 1240: five equal columns, 12px apart. Each column holds its topic name (12px sans, weight 500, sentence case, one line, never truncated) and, at y 44, one 3px-high segment per slide of that topic on the path that is on, 3px apart. Lit topic name navy weight 600, others `#5a7181`. Segments: slides already passed navy, the current slide blue, later slides line-2.
  - footer strip y 690 to 720, white. Left at x 40, right-aligned at x 1240, both 11px Geist Mono weight 500 uppercase letter-spacing 0.14em `#5a7181`, baseline y 708. Left: "Synthetic data" on a slide that shows data, else the talk title "Fairshare: sales answers you can check". Right: "n / N" on the path that is on, or "Backup" on a backup slide.
  - `welcome` and `thanks` (the first and last slide of either path): logo only, no tracker, no footer. `agenda` and the other bookend-part slides: footer, no tracker. Stills: no frame at all.
  - native content box x 64 to 1216, y 88 to 664, content centered vertically in it.
  - figures (image, animated, live) fill the stage under the strips. Every figure the deck shows keeps its content between y 64 and y 680 of its view box.
- Disclosure: on a native slide the title shows on arrival and each point, tile, table, check, result or agenda topic arrives on a press. Unreached items keep their space (the layout never shifts as items arrive) and are invisible to the eye and to assistive tech. Earlier items recede. A press after the last step moves the deck. Arriving backward, after a reload or on return from a demo, the slide shows complete. A diagram's structure (axes, column headings, actors, frame) shows on arrival; anything that gives the point away (a legend or label naming the focal item, a value, a verdict, a caption, a payoff line) waits for its step. 01 keeps its assembled stack. Inside the deck an unreached figure item has opacity 0.
- Density: a thing is one point, tile, table row, panel or chart annotation. A finished slide holds at most five short lines, or at most four things that carry their own detail.
- Motion: native arrivals fade in from 8px below over 320ms ease-out; receding is a 320ms color change. Chart lines draw left to right over 900ms ease-out when the frame shows, dots fade in after their line, bars grow from their baseline over 600ms. Figure steps keep the plugin's 600ms. Nothing loops, bounces or moves after it arrives. Under `prefers-reduced-motion` nothing moves, but native steps still step. A figure page stays inside the plugin's budget: at most 8 steps, 12 marked items, 2 at once; a figure that needs more becomes two slides.
- Numbers: only as `{placeholders}` filled from `web/src/deck/facts.json`, which `docs/diagrams/src/deck_facts.py` writes. A value that lives only on Databricks or in a results file goes in `DATED` with its source and date. Figure builders read numbers through `deck_facts.fact()` and `display()`. No bare data numbers in slide text (the `bareNumbers` rule).
- Copy: no em or en dashes anywhere. Made-up data stays labeled made up. Every Azure possibility tagged "Possibility" and nothing built tagged. Speaker notes under 40 words. Text must not match the `REAL` or `POWER_BI` patterns in `evals/test_labels.py`.
- No new dependencies, no data or calculation changes, no frontend-slides, no changes under `lakehouse/` or `harness/`.
- The gate, from R: `FAIRSHARE_BACKEND=duckdb .venv/bin/pytest evals -q`; from `R/web`: `bun run test`, `bun run build`, and `bunx playwright test` with a dev server on 5173 (`bunx vite --port 5173 --strictPort` in the background, stopped afterwards; never touch the server on 8010).
- Figure rebuild commands are in `docs/diagrams/README.md` ("Rebuilding"); PNG export is `NODE_PATH=web/node_modules node docs/diagrams/src/export_png.cjs <in.html> <out.png>` from R.

## Review Focus

1. Returning to the deck from a live demo, or reloading mid-talk, lands on the same slide shown complete, with the clock kept. Pinned in Task 5.
2. A slow or blocked frame never flashes the finished figure; after the timeout the finished figure shows as a fallback and a press moves the deck. Pinned in Task 7.
3. A burst of clicker presses across native steps and framed steps applies in order with no skipped or doubled step, and the notes window shows the same step. Pinned in Task 5.
4. Going backward into a stepped slide or a figure lands on its last step, and a forward press from there moves on. Pinned in Tasks 5 and 7.
5. At window sizes 1024 by 768 and 1920 by 1080 the tracker's five names never overlap or truncate and the footer stays inside the stage. Pinned in Task 3.

## Working notes for every task

- Visual checks: start the dev server, then walk slides with the controller's screenshot helper at `<workspace>/shoot.cjs` (the dispatch gives the path): `NODE_PATH=web/node_modules node <workspace>/shoot.cjs <outdir> <startId> <presses>` loads `/present#<startId>`, captures it, then presses ArrowRight `<presses>` times and captures after each press. Read the PNGs and look. A UI task's report lists the screenshot paths it checked.
- Copy written in any task follows the unslop rules quoted in Task 13 and the spec's Copy section; Task 13 polishes everything once more.
- Keep `deck.test.ts`'s `NativeSlide` render through `renderToStaticMarkup` working: layouts stay SSR-safe.

---

### Task 1: Topics, frame info and native steps in the deck model

**Files:**
- Modify: `web/src/lib/deck.ts`, `web/src/lib/deck.test.ts`, `web/src/deck/slides.ts` (the `part` values only)
- Modify only as far as compiling needs: `web/src/components/Notes.tsx`, `web/src/deck/SlideView.tsx`

**Interfaces:**
- Consumes: the existing `Slide`, `Native`, `onPath`, `move`, `nextPart`, `plannedStart`, `checkpointPlan`, `pressTarget`, `texts`.
- Produces:
  - `export type Topic = "steps" | "modes" | "numbers" | "checks" | "aa"`
  - `export type Part = "open" | Topic | "close" | "backup"`
  - `export const TOPIC_ORDER: readonly Topic[]` (that order)
  - `export const TOPICS: Record<Topic, { name: string; line: string }>` (the Global Constraints wording, verbatim)
  - `export const PARTS: Record<Part, string>`: "Welcome", the five topic names, "Thank you", "Backup"
  - `export function isTopic(p: Part): p is Topic`
  - `Slide` gains `data?: boolean` (a figure that prints values from the data) and `byline?: string[]` (lines a live slide shows under its title, replacing the page's caption)
  - `Native` becomes: `statement { lines: string[]; ask?: string }`, `tiles { tiles: Tile[] }`, `table { tables: string[]; columns?: string[] }` (`columns` keeps only those column names, in the table's order), `checks { keys?: string[] }` (keys of `facts.checks`; omitted means all, shown at once), `results { items: Result[] }`, `agenda {}`, `close { lines: string[] }`, `demo { demo: Demo; lines: string[] }`, with `export type Result = { head: string; body: string; result: string; miss?: string }`. The old `{ layout: "table"; tables: ["checks"] }` form goes; `knownTables` keeps working for real table keys.
  - `export type FrameInfo = { bare: boolean; tracker: boolean; topic: Topic | null; inTopic: { at: number; of: number } | null; number: { at: number; of: number } | null; footer: boolean; backup: boolean }`
  - `export function frameInfo(slides: Slide[], path: PathName, id: string): FrameInfo`
  - `export function stepCount(s: Slide): number`
  - `export function arrivalStep(s: Slide, how: "forward" | "backward" | "load"): number`
  - `export function showsData(s: Slide, facts: Facts): boolean`
  - `checkpointPlan(slides, path)` keeps its signature and returns one checkpoint per topic on the path.
  - `texts(s)` also returns `byline`, `statement.ask`, every `Result` field and `close.lines`.

- [ ] **Step 1: Write the failing tests** in `deck.test.ts`:
  - `TOPICS` equals the five Global Constraints entries word for word, in `TOPIC_ORDER`.
  - `frameInfo` on a fixture of open, topic, close and backup slides: a topic slide lights its topic, `inTopic` counts only that topic's slides on the path that is on, `number` is 1-based on the path that is on; the first and last path slides have `number: null`, `footer: false`, `tracker: false`; an `open` slide that is not first has `footer: true`, `tracker: false`; a backup slide has `backup: true`, `number: null`, `footer: true`; a `still` has `bare: true`. On the short path the numbers run 1 to the short path's length.
  - `stepCount`: statement = lines + (ask ? 1 : 0); tiles = tiles; table = tables; checks = keys?.length ?? 0; results = items; agenda = 5; close = 0; demo = lines; image, live and animated = 0.
  - `arrivalStep`: "forward" gives 0, "backward" and "load" give `stepCount(s)`.
  - `showsData`: true for table and checks layouts, for a slide with `data: true`, and for native text holding a `facts.facts` key (dated keys do not count, notes do not count); false otherwise.
  - `checkpointPlan` on the fixture: one entry per topic present on the path, label = the topic name, `planned` = the end of that topic's last slide on the path, `by = Math.ceil(planned)`.
  - The existing tests keep passing with the new parts, except those this task must rewrite: the hard-coded checkpoint minutes and `nextPart` from the title (rewrite them against the new rule and the new parts).
- [ ] **Step 2: Run** `cd web && bun run test`. Expected: the new tests fail.
- [ ] **Step 3: Implement** the interfaces above in `deck.ts`. Map every slide in `slides.ts` to a new part without moving any slide: `title` open; `problem` steps; `what`, `query-opener`, `ask`, `director`, `riffle-opener`, `delegate`, `precall`, `built-how` modes; every slide from `elevator-opener` through `moved`, plus `stack-opener` and `system`, numbers; `sieve-opener`, `checked`, `measured`, `limits` checks; `know`, `at-aa`, `azure`, `start` aa; backups stay backup. Convert the `checks` slide to `{ layout: "checks" }` with no keys for now. Adjust `Notes.tsx` and `SlideView.tsx` only as far as compiling needs.
- [ ] **Step 4: Run** `bun run test` and `bun run build`. Expected: pass. The main path still runs 35 to 40 minutes.
- [ ] **Step 5: Commit** `deck: topics, frame info and native steps in the model`.

### Task 2: Units on the examples, a reason on every check, and Genie's earlier runs

**Files:**
- Modify: `docs/diagrams/src/deck_facts.py`, `web/src/deck/facts.json` (regenerated), `evals/test_deck_facts.py`, `web/src/lib/deck.ts` (the `DeckFacts` checks type)

**Interfaces:**
- Produces: every `facts.json` column entry's `example` carries its unit; every check entry becomes `{ key, name, why, expected, actual, ok }`; a dated fact `genie_benchmark_earlier`.

- [ ] **Step 1: Write the failing pytest tests** in `evals/test_deck_facts.py`:
  - In `facts.json`, `gold.fact_agency_sales_monthly`'s `aa_revenue` and `market_revenue` examples start with `$`, `aa_pax` and `market_pax` read as whole numbers with thousands separators where they have four or more digits, `sales_month` reads `Sep 2026`; `gold.fact_market_capacity`'s `aa_seat_share` ends with `%`, `aa_seats` and `total_seats` carry a thousands separator. Every other money, share, count and month column across all `COLUMNS` tables follows the same rule.
  - Every check has a unique snake_case `key` and a `why` that has no digits and no em or en dash.
  - `DATED["genie_benchmark_earlier"]` has value 17, display "17 of 20", date `2026-10-19`, and a source naming both `evals/results/2026-10-19T211129-genie-eval.json` and `evals/results/2026-10-19T212948-genie-eval.json`.
- [ ] **Step 2: Run** `FAIRSHARE_BACKEND=duckdb .venv/bin/pytest evals/test_deck_facts.py -q`. Expected: the new tests fail.
- [ ] **Step 3: Implement.** A `UNITS` map in `deck_facts.py` (table, then column, then a `FORMATS` name) applied in `_columns()`; check the `pct` format's input scale against `aa_seat_share` (a fraction) before using it. Give each `CHECKS` entry a key and a why: one plain sentence on what the check guards against, written to the unslop rules (Task 13 quotes them). Add `genie_benchmark_earlier` to `DATED`. Regenerate with `FAIRSHARE_BACKEND=duckdb .venv/bin/python docs/diagrams/src/deck_facts.py`. Extend the `DeckFacts` checks type in `deck.ts`.
- [ ] **Step 4: Run** the full pytest gate and `cd web && bun run test`. Expected: pass, including `test_facts_json_is_fresh`.
- [ ] **Step 5: Commit** `facts: units on examples, a reason per check, Genie's earlier runs`.

### Task 3: The frame

**Files:**
- Create: `web/src/deck/Frame.tsx`
- Modify: `web/src/deck/SlideView.tsx`, `web/src/deck/layouts.tsx` (remove `LogoBand` and its tag logic), `web/src/components/Present.tsx` (passes frame info), `web/src/copy.ts` (`deckFooter`, `deckFooterData`), `web/src/lib/deck.test.ts`, `web/e2e/present.spec.ts`

**Interfaces:**
- Consumes: `FrameInfo`, `frameInfo`, `showsData`, `TOPICS`, `TOPIC_ORDER` (Task 1).
- Produces: `export function DeckFrame(props: { info: FrameInfo; label: string; children: ReactNode }): JSX.Element`, drawing the header and footer strips of the Global Constraints over its children; `SlideView` gains the prop `frame: FrameInfo` and wraps every slide that is not `bare` in `DeckFrame`.

- [ ] **Step 1: Write the failing tests.** Vitest, rendering `DeckFrame` with `renderToStaticMarkup`: a topic slide shows all five topic names once, marks the lit one with `aria-current="step"`, draws one segment per slide of each topic with the current one marked, and shows "n / N"; a frame with `tracker: false` draws no names; one with `footer: false` draws no footer; a backup frame says Backup; the label reads "Synthetic data" when `showsData`. Playwright: on `#ask` the tracker lights "Ask and Delegate"; at window sizes 1024 by 768 and 1920 by 1080 no two tracker names overlap (compare their bounding boxes) and no name is clipped (`scrollWidth <= clientWidth`); the stills show no frame. Replace the old part-label test.
- [ ] **Step 2: Run** the vitest and Playwright files. Expected: fail.
- [ ] **Step 3: Implement** `DeckFrame` to the pinned geometry. In `SlideView`: drop the eyebrow; native slides render inside the frame's content box; image, animated and live slides fill the stage under the strips; `showPage()` also hides the hairline page's `.brand`, and its `.caption` when the slide has a `byline`, in which case `SlideView` draws the title and the byline lines in the bottom area (title 32px weight 600 navy, byline 20px `#5a7181`). The hide rule for a figure's own band in embed mode comes in Task 7; until then the header strip covers it.
- [ ] **Step 4: Run** the gate. Take screenshots of `problem`, `ask`, `pipeline`, `checks` and a backup, and look at them.
- [ ] **Step 5: Commit** `deck: a frame with the logo, a topic tracker and slide numbers`.

### Task 4: Native layouts on one type ramp, with steps

**Files:**
- Create: `web/src/deck/ramp.ts`
- Modify: `web/src/deck/layouts.tsx`, `web/src/deck/SlideView.tsx` (passes `step`), `web/src/components/Notes.tsx` (the preview passes a step), `web/src/lib/deck.test.ts`

**Interfaces:**
- Consumes: the `Native` variants, `stepCount`, `TOPICS` (Task 1), the check keys and whys (Task 2), the frame's content box (Task 3).
- Produces: `NativeSlide({ slide, facts, onDemo, step }: { ...; step?: number })`, where `step` is how many items show (default `stepCount(slide)`, the complete slide); `ramp.ts` exports the ramp of the Global Constraints as named class strings.

- [ ] **Step 1: Write the failing tests** (vitest, `renderToStaticMarkup`), one per layout: at `step = k` exactly k items are visible and the rest carry `aria-hidden="true"` and an invisible style while keeping their place; item k is marked current (`data-current`) and items before it are marked receded (`data-receded`); at the full step count nothing is hidden. Also: `statement.ask` renders last, set apart; `table` with `columns` shows only those columns; `checks` with keys shows those checks with their `why`, and without keys shows all eight at once; `results` shows head, body, the result in the display style and the miss in the miss style; `agenda` shows the five topics with their lines; `close` has no steps; `demo` shows its button at step 0.
- [ ] **Step 2: Run** `bun run test`. Expected: fail.
- [ ] **Step 3: Implement** every layout on the ramp, centered in the content box, with arrival and recede motion as pinned. The `statement.ask` callout: tint background, a 4px blue rule on the left, 20px 28px padding, the text in body size weight 600 navy. The Notes preview shows the current slide at the deck's step and the next slide complete (the step arrives through Task 5's message; until then pass the full count).
- [ ] **Step 4: Run** the gate. Screenshot `problem`, `what`, `row`, `checks`, `limits`, `know`, `azure` and `start` at their first and last steps, and look at them.
- [ ] **Step 5: Commit** `deck: native layouts on one type ramp, stepped`.

### Task 5: Present and the notes window step through native slides

**Files:**
- Modify: `web/src/components/Present.tsx`, `web/src/components/Notes.tsx`, `web/src/lib/deck.ts` (`Msg`), `web/src/lib/deck.test.ts`, `web/e2e/present.spec.ts`

**Interfaces:**
- Consumes: `stepCount`, `arrivalStep`, `pressTarget` (Task 1), `NativeSlide`'s `step` (Task 4).
- Produces: the `Msg` variant `{ t: "state"; id; path; startedAt; step: number; steps: number }`.

- [ ] **Step 1: Write the failing tests.** Playwright: on `problem` the first press shows one point and the deck stays; after `stepCount` presses the next press moves the deck; pressing back from the following slide lands on `problem` complete; reloading on a stepped slide lands complete; returning from the Ask demo lands on `ask` complete with the clock kept; a burst of four next keys sent from the notes window applies in order (the deck's step and slide match four single presses); the notes window shows "Point k of n" on a stepped slide and matches the deck after each press. Update the existing burst and short-path tests to the stepped behavior.
- [ ] **Step 2: Run** the Playwright file. Expected: fail.
- [ ] **Step 3: Implement.** A step state in `Present` mirrored in a ref, so a press read under `flushSync` sees the latest step. In `act()`, a native slide with steps routes next and prev through `pressTarget(step, stepCount(slide), dir)`: "diagram" changes the step, "deck" moves on. `go()` sets `arrivalStep(next, backward ? "backward" : "forward")`; the first render after load uses "load". The state message carries `step` and `steps`. The notes outline groups slides by `PARTS` in the order open, the five topics, close, backup.
- [ ] **Step 4: Run** the gate.
- [ ] **Step 5: Commit** `deck: presses step through native slides, in both windows`.

### Task 6: The new order

**Files:**
- Modify: `web/src/deck/slides.ts`, `web/src/lib/deck.test.ts`, `web/e2e/present.spec.ts`, `web/src/copy.ts` (if a label changes)

**Interfaces:**
- Consumes: every layout and the frame (Tasks 1 to 5).
- Produces: the slide ids later tasks use: `welcome`, `agenda`, `problem`, `what`, `query-opener`, `ask`, `director`, `riffle-opener`, `delegate`, `precall`, `stack-opener`, `system`, `elevator-opener`, `pipeline`, `row`, `revenue`, `checks`, `numbers`, `share-fair`, `moved`, `sieve-opener`, `checked`, `guardrails`, `evals`, `evals-more`, `limits`, `at-aa`, `azure`, `start`, `know`, `thanks`, and the backups (with `planted`, `checks-all` and `dict-facts` added).

- [ ] **Step 1: Write the failing tests.** Vitest: the main path's ids run in the order above (without `gaps`, which Task 9 adds after `numbers`); the short path is `welcome`, `agenda`, `problem`, `what`, `ask`, `precall`, `system`, `evals`, `start`, `thanks`; `coverage`, `built-how` and `measured` are gone; `planted`, `checks-all` and `dict-facts` are backups; every main-path slide's `part` matches the spec's table; the main path runs 35 to 40 minutes and the short path 10 to 12.
- [ ] **Step 2: Run** `bun run test`. Expected: fail.
- [ ] **Step 3: Implement** the spec's table, with these specifics:
  - `title` becomes `welcome` (live, the airliner page, `byline`: "Chirag Lakhanpal", "Analyst/Sr Analyst, Sales AI & Innovation", and one line that every number in the talk comes from made-up data). `agenda` is `{ layout: "agenda" }`. `thanks` is `{ layout: "close" }` with a thank-you title, his name, chirag.lakhanpal.cl@gmail.com and an invitation to ask questions; no links.
  - `problem`: the two points as `lines`, the question to the room as `ask`.
  - `row`: `{ layout: "table", tables: ["gold.fact_agency_sales_monthly", "gold.fact_market_capacity"], columns: ["aa_revenue", "market_revenue", "aa_pax", "market_pax", "aa_seats", "total_seats", "aa_seat_share", "source"] }`. `dict-facts` (backup) shows both tables in full.
  - `checks`: `{ layout: "checks", keys: [...] }` with the four checks that matter most to the room (your pick, from Task 2's keys), titled without the word "checks". `checks-all` (backup) is `{ layout: "checks" }`.
  - `guardrails`: tiles, the four guardrails in the spec, each saying what it stops. `evals`: results, Genie and the whole app; `evals-more`: results, Foundry's evaluators, the nightly comparison and the commit check. Results and misses come from dated facts (`genie_benchmark`, `genie_benchmark_earlier`, `genie_benchmark_date`, the `app_model_*`, `foundry_*` and `nightly_parity_*` facts, `twins_checked`).
  - `revenue`, `numbers`, `share-fair`, `delegate` and `at-aa` stay image slides until their tasks; mark every data figure slide `data: true`.
  - Minutes as the spec's table, with `numbers` at 1.75 until Task 9 splits it.
  - Notes: keep or adjust each note so its handoff names the new next slide, under 40 words, in the spoken voice of Task 13.
- [ ] **Step 4: Run** the gate. Walk the whole main path with the screenshot helper and look at every slide.
- [ ] **Step 5: Commit** `deck: the talk in five topics between welcome, agenda and thanks`.

### Task 7: Nothing before its step inside the figures

**Files:**
- Modify: `docs/diagrams/src/aa.py`, `docs/diagrams/src/blueprint.py`, `docs/diagrams/src/waterfall.py`, `docs/diagrams/src/exploded.py`, `docs/diagrams/src/journeys.py`, `docs/diagrams/src/data_diagrams.py` and `docs/diagrams/src/planted.py` (only if 07 or 14 reach below y 680), `web/src/deck/SlideView.tsx`, `web/src/lib/deck.ts` (the timeout constant), regenerated pages and exports for 01, 02, 04, 05, 06 and 08 (the embed CSS is baked into every animated page at build time), a new pytest file `evals/test_figures_in_deck.py`, `web/e2e/present.spec.ts`

**Interfaces:**
- Produces: in `aa.py`, embed CSS that hides unreached items and `[data-brand="aa-logo"]` inside the deck, plus draw-in classes `draw-line` (a path with `pathLength="1"`), `draw-dot` and `draw-bar` that animate when `html[data-embed]` is set. `export const FRAME_FALLBACK_MS = 3000` in `deck.ts`.

- [ ] **Step 1: Write the failing tests.** Pytest over the generated HTML: the embed CSS holds a rule setting unreached `[data-motion-item]` (not 01's `[data-part]` slabs) to opacity 0 and a rule hiding `[data-brand="aa-logo"]`; in 02 the legend entry naming the verifier sits inside the verifier's motion item; in 08 the legend entry naming AA's share sits inside the share bar's step and the words "Route mix" no longer appear; 01's caption sits inside its last step; 04 and 05's payoff line sits inside the last step; no text or shape in 01, 02, 04, 05, 06, 08, or the backup figures 07 and 14, reaches below y 680. Playwright: on `pipeline`, once `data-ready="1"`, an item whose `data-step` is above the frame's `data-step-current` has computed opacity 0; before ready, the finished-figure thumb is not visible; with the frame blocked (route abort) the thumb shows after `FRAME_FALLBACK_MS` and the first press moves the deck; arriving backward on `moved` lands on its last step.
- [ ] **Step 2: Run** them. Expected: fail.
- [ ] **Step 3: Implement.** The embed rules in `EMBED_CSS`; move the give-away legend entries, captions and payoffs into the steps that bring in their items; replace 08's "Route mix" with plain words for the change that comes from selling more on some routes and less on others, and say in that step's note that for Harbor it barely moved; move 08's bottom content up to y 680. In `SlideView`, an animated slide hides its thumb until the frame is ready and shows it only after `FRAME_FALLBACK_MS` without readiness, counting zero steps then. Rebuild and re-export 01, 02, 04, 05, 06 and 08 (static twins and PNGs), and 07 or 14 if their content moved. Run `python3 docs/diagrams/src/lint.py` on the rebuilt pages and the plugin's verifiers the builders already call.
- [ ] **Step 4: Run** the gate. Screenshot `director`, `pipeline`, `system`, `checked` and `moved` at arrival and after each step, and look at them.
- [ ] **Step 5: Commit** `figures: nothing shows before its step inside the deck`.

### Task 8: Revenue by month as a stepped chart

**Files:**
- Modify: `docs/diagrams/src/revenue.py`, `web/src/deck/slides.ts` (`revenue` becomes animated), `evals/test_labels.py` (`DATA_FIGURES` gains the animated slug), `evals/test_figures_in_deck.py`, regenerated `11-revenue-by-month*.html` and exports

- [ ] **Step 1: Write the failing tests:** the animated page `11-revenue-by-month-animated.html` exists with "FAIRSHARE · SYNTHETIC DATA" in its band; its two year lines carry `draw-line`; the March and April band with the net change is step 1 and the three notes (Sunbelt, Harbor, the other agencies) are steps 2 to 4, each a motion item; the page has no legend; both lines end in a direct year label; nothing reaches below y 680; `revenue` is an animated slide with `data: true`.
- [ ] **Step 2: Run** them. Expected: fail.
- [ ] **Step 3: Implement** with `aa.animated()`. The three notes sit beside the band in the note style of the ramp's proportions (smaller and lighter than the title, never italic display size), the band labels itself, and the source line stays smallest and grey. The static twin keeps the same layout, complete.
- [ ] **Step 4: Run** the gate. Screenshot `revenue` at arrival and each step and look at them.
- [ ] **Step 5: Commit** `figures: revenue by month draws on arrival, notes one per press`.

### Task 9: The seven numbers over two slides

**Files:**
- Modify: `docs/diagrams/src/definitions.py`, `web/src/deck/slides.ts` (`numbers` animated at 1 minute, a new `gaps` slide after it at 1 minute), `web/src/lib/deck.test.ts` (the order gains `gaps`), `evals/test_labels.py`, `evals/test_figures_in_deck.py`, new pages `09a-numbers-share*.html` and `09b-numbers-gaps*.html` with exports

- [ ] **Step 1: Write the failing tests:** both animated pages exist with the synthetic data band; 09a's steps are AA revenue, AA share and fair share, 09b's are the share gap in points, the share gap in dollars, year over year and pace, one card per step; each card carries the plain-words definition from the spec's `numbers` section; the slide that closes each page says where the numbers live (six as measures in `gold.sales_metrics` worked out at query time, pace stored in `gold.agency_pace`) and that Genie, the dashboard and Ask read them from that one metric view; nothing reaches below y 680; the main path holds `gaps` right after `numbers` and runs 35 to 40 minutes.
- [ ] **Step 2: Run** them. Expected: fail.
- [ ] **Step 3: Implement.** The drift strip stays on `09-definitions.html` only. Any number a card prints comes from `deck_facts`.
- [ ] **Step 4: Run** the gate. Screenshot both slides at arrival and each step and look at them.
- [ ] **Step 5: Commit** `figures: the seven numbers over two stepped slides, each with how it is calculated`.

### Task 10: AA share against fair share, decluttered

**Files:**
- Modify: `docs/diagrams/src/share_fair.py`, `web/src/deck/slides.ts`, `evals/test_labels.py`, `evals/test_figures_in_deck.py`, regenerated `12-share-vs-fair*.html` and exports

- [ ] **Step 1: Write the failing tests:** the animated page exists with the synthetic data band; it has at most 8 steps and 12 marked items; the agency names and the axis show on arrival; the fair share marks, the AA share marks and the callouts arrive in steps; at most four things are labeled with values on the finished page; nothing reaches below y 680; `share-fair` is an animated slide with `data: true`.
- [ ] **Step 2: Run** them. Expected: fail.
- [ ] **Step 3: Implement.** Pick which agencies carry the story (the current note names Lone Star at the top and FareHub at the bottom). The sentence about the made-up seat shares arrives as its own step. Drop the legend if the marks can be labeled directly.
- [ ] **Step 4: Run** the gate. Screenshot the slide at arrival and each step and look at them.
- [ ] **Step 5: Commit** `figures: share against fair share, stepped and decluttered`.

### Task 11: Agents draft, people decide, stepped

**Files:**
- Modify: `docs/diagrams/src/swimlane.py`, `web/src/deck/slides.ts`, `evals/test_figures_in_deck.py`, regenerated `03-delegate*.html` and exports

- [ ] **Step 1: Write the failing tests:** the animated page exists; the lanes and their names show on arrival; the flow arrives in steps in the order it runs (the nightly job, the fixed queries, the writer, the verifier, the person who approves, then the CRM and Outlook); the legend entry naming the focal node sits inside that node's step; the caption sits inside the last step; at most 8 steps; nothing reaches below y 680; `delegate` is an animated slide.
- [ ] **Step 2: Run** them. Expected: fail.
- [ ] **Step 3: Implement** with `aa.animated()`.
- [ ] **Step 4: Run** the gate. Screenshot the slide at arrival and each step and look at them.
- [ ] **Step 5: Commit** `figures: the Delegate flow, stepped`.

### Task 12: The same layers at AA, stepped

**Files:**
- Modify: `docs/diagrams/src/exploded.py` (`build_at_aa` and what it calls), `web/src/deck/slides.ts`, `evals/test_figures_in_deck.py`, regenerated `15-at-aa*.html` and exports

- [ ] **Step 1: Write the failing tests:** the animated page exists; the five layers show on arrival as structure; what runs today, what is built but not deployed, and what waits on AA's Microsoft account each arrive as a step, then the feeds next to their tables, hardest first; the mark legend arrives with the first marks; at most 8 steps; nothing reaches below y 680; `at-aa` is an animated slide.
- [ ] **Step 2: Run** them. Expected: fail.
- [ ] **Step 3: Implement** with `aa.animated()`, keeping 01's static look for the stack.
- [ ] **Step 4: Run** the gate. Screenshot the slide at arrival and each step and look at them.
- [ ] **Step 5: Commit** `figures: the same layers at AA, stepped`.

### Task 13: Every word, once more

**Files:**
- Modify: `web/src/deck/slides.ts` (every title, line, tile, result, byline, close line and note), `docs/diagrams/src/deck_facts.py` (check whys, if they need it, then regenerate `facts.json`), `web/src/copy.ts` (deck strings)

The copy rules, from the unslop skill, which every slide string and note must pass: no "-ing" tails that fake depth; no vague attributions; none of these words: additionally, crucial, delve, enduring, enhance, fostering, garner, interplay, intricate, landscape, pivotal, showcase, tapestry, testament, underscore, vibrant; "is" and "has" instead of "serves as", "stands as", "boasts", "features"; no "not just X, but Y"; no forced groups of three; no synonym cycling; no false ranges; no em or en dashes; colons only before a list or an example; sentence case; straight quotes; no filler ("in order to", "due to the fact that"); no stacked hedges; no generic closing lines; no abstract metaphor nouns (substrate, wedge, vector, harness as a metaphor, surface as in "API surface", north star, flywheel); say what a thing does, with the mechanism or the number; one idea per sentence; active voice with the actor named; strong verbs instead of adverbs; plain words (use, help, many, if); no figurative verbs or aphorisms; whole sentences with their articles and verbs.

A title passes only if it could not sit unchanged in someone else's deck. The topic names and agenda lines stay exactly as the Global Constraints give them.

Notes are spoken, in his voice: plain and conversational, a little loose, medium sentences with some run-ons, concrete names with an "and so on" tail, no tidy closing lines, no "not X, but Y", no three-beat lists. Each note gives the point, the number he must say as a placeholder, the handoff to the next slide, and on a stepped slide where the presses fall. Under 40 words.

- [ ] **Step 1: Write the failing test:** a vitest that every title, native string and note passes a checker for the mechanical rules above (the banned words, "not just", "serves as", "stands as", "boasts", em and en dashes, curly quotes, "in order to", "due to the fact that").
- [ ] **Step 2: Run** `bun run test`. Expected: fail on today's copy.
- [ ] **Step 3: Rewrite** every string. Trim the `security` and `foundry-eval` backups to what the main path does not already say. Re-check every title against the other-deck test and list any that fail in the report with its replacement.
- [ ] **Step 4: Run** the gate.
- [ ] **Step 5: Commit** `deck: every slide and note rewritten to the unslop rules`.

### Task 14: Browser tests for the whole talk, the docs, and the deploy

**Files:**
- Modify: `web/e2e/present.spec.ts`, `docs/diagrams/README.md`

- [ ] **Step 1: Write** the remaining Playwright tests for the Review Focus items not yet pinned, and a walk of the full main path that presses through every slide and step, asserting the hash order and that the tracker lights the topic of each slide.
- [ ] **Step 2: Run** the gate.
- [ ] **Step 3: Update** `docs/diagrams/README.md`: the new animated pages, the deck's embed rules (hidden unreached items, hidden band, draw-in classes), the content area of y 64 to 680, and the figure list in the order the talk shows them.
- [ ] **Step 4: Deploy** with `cd web && bun run build && cd .. && .venv/bin/python lakehouse/app_deploy.py deploy`, then walk every main-path slide on the App at arrival and at its last step with the screenshot helper against the App URL, and look at them. Report any slide that differs from the dev server.
- [ ] **Step 5: Commit** `deck: tests for the whole talk and the figure docs`.

### Task 15: The speaker notes and demo-day files

**Files (in jobflow, not in this repo; not committed):**
- Rewrite: `/Users/chiraglakhanpal/Downloads/Chirag Lakhanpal/Chirag Lakhanpal/Explore/jobflow/interview-prep/American Airlines/aa-onsite-speaker-notes.md`
- Modify: `/Users/chiraglakhanpal/Downloads/Chirag Lakhanpal/Chirag Lakhanpal/Explore/jobflow/interview-prep/American Airlines/aa-onsite-demo-day.md`

- [ ] **Step 1:** Generate the notes file from `slides.ts` and `facts.json` in deck order: for each slide its id, topic, minutes (full and short), title, and the note with every placeholder filled; then the backups. Zero em or en dashes, zero unfilled braces, roles only.
- [ ] **Step 2:** In the demo-day file, replace every old slide id and part name with the new ones (`title` is now `welcome`, `measured` is gone, the four parts are now five topics), and add one line on the stepped slides: a press reveals the next point before it moves on.
- [ ] **Step 3:** Check both files for dashes, braces and blocklisted names (read the blocklist from `.env` inside a script that prints only counts).
- [ ] **Step 4:** Report the two paths and the counts. No commit.
