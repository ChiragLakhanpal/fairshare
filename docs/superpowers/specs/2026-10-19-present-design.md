# fairshare: the presentation inside the app

## Context

Chirag presents fairshare to the hiring team at American Airlines: a sales director and a technical data lead, on site,
as a project walkthrough. His round-one notes say the director's session holds behavioral questions too, and the panel
will interrupt. The deck lives in the deployed Databricks App, so nothing depends on his laptop. This spec covers the
deck. The report that explains the whole project is the next spec, and the deck's last slide links to it.

Decisions taken with Chirag on October 19:

- A `/present` page in the app, opened from the sidebar, with a second window for speaker notes.
- The main path runs 35 to 40 minutes. A short path of about 11 minutes is ready too, because his round-one plan
  budgets ten minutes for the walkthrough with the director (section 8.4 of the debrief). The notes window picks the
  path. Everything else is backup.
- The first live answer comes by minute 2: the Harbor question in Ask, right after the intro. The data and the build then
  explain why that answer can be trusted.
- All five hairline section openers stay, at about 15 seconds each.
- The data part shows what is in the data, what it shows, what was planted in it and what cleaning did, the basic checks,
  and what each column means.
- The system diagram and the diagrams where order matters (02, 04, 05, 06, 08) step forward with the deck's arrow keys.
- Examples from the data on screen. Analogies are spoken, and only for the technical ideas; the report carries the full set.
  A number that neither DuckDB nor the Databricks CLI can reach gets fetched by Chirag with SQL written for him.
- The seat data stays synthetic, and every claim that it is real gets corrected first ("Fixes first").
- Pace gets fixed in gold so a missing month is not counted as a zero.
- Foundry is built: the four writer agents write the Delegate pages in the nightly job and in the App
  (`FAIRSHARE_APP_THINKER=foundry`). Only the harness as a Foundry hosted agent was never deployed (no `azd`).
- The live demo runs on the App's own model, with the laptop on gpt-5-mini as the fallback.
- Speaker notes name roles, such as "the sales director", and never people. Nothing on screen names an interviewer.
- Four advisors reviewed the first draft (a sales leader, a data lead, a presentation coach, an engineer). What they
  changed is listed at the end.

Everything below follows CLAUDE.md: numbers come from queries, definitions live in one place, copy is plain words at a
10th-grade level with no em dashes, nothing destructive, and dummy data stays dummy and says so.

## Fixes first

These land before any slide work, each with its own check.

**The seats are made up.** The BTS T-100 files were never downloaded, so `data/make_data.py` wrote one seat share per
route, moved by about a point each month, with 150,000 total seats in every market-month and `is_projected` never true.
In DuckDB and on Databricks, all 252 rows of `gold.fact_market_capacity` have `source = synthetic`. Every place that calls
the seats real gets the label "made-up seat shares, one per route; the T-100 loader (`data/t100.py`) has never run":

- `README.md` line 44 and the caption on line 56
- `CLAUDE.md` rule 8
- `docs/architecture.svg` line 28 ("BTS T-100 (real)")
- `harness/signals.py` line 207, which tells users BTS has not published a month yet
- `lakehouse/genie.py`, the space description and instructions, then the Genie space is updated on Databricks
- `lakehouse/03_metric_view.sql` comments and the fair_share text in `lakehouse/04_definitions.sql`, then both rerun on
  Databricks and in DuckDB, so the app's definition window shows the corrected text
- `docs/walkthrough.md` line 103
- `docs/diagrams/src/exploded.py`, `data_diagrams.py` and `data_numbers.py`, then 01, 06 and 07 rebuilt and re-exported

**Figure 01 names the right model.** Its Agents sublabel says "Agent Framework · Foundry gpt-5-mini" (`exploded.py`
line 107), but Ask in the App runs Qwen3-Next and the Foundry agents write the Delegate pages. It becomes "Agent
Framework · Qwen3-Next · Foundry writers".

The check: a search of the repo finds no place that calls the seat data real, other than `data/t100.py` and
`data/make_data.py` describing what happens when real files exist.

**QSI comes out.** `lakehouse/03_metric_view.sql` line 100 lists QSI as a synonym for fair share. QSI is a
schedule-quality model, not seat share.

**The parity story gets told as it happened.** There is no Power BI run: the twin is a SQL copy of the Power BI measure.
On October 12 the retired v1 of the aa_share twin, which counted passengers, ran once between two green runs, and all
250 agency-months came back red; the other five twins stayed on v1 and green throughout (`app/cache/kpi_parity.csv`). The nightly job checks six of the seven numbers; pace has no twin. Figure 09's
header and bottom strip, 01's Definitions sublabel ("Power BI twin, checked every night") and every note say exactly that:
"My first SQL twin for AA share counted passengers, and all 250 agency-months came back red. The run on record replays it. The nightly
job checks six of the seven numbers."

**The elevator opener matches figure 06.** Its caption's fourth floor, "the app's own records", becomes "defined once".

**Pace stops counting a missing month as zero.** `gold.agency_pace` adds up the months an agency reported but grows the
goal every calendar month, so Sunbelt Vacations' missing March and April 2026 count as $0 and its pace falls from 117.6 in
February to 74.2 in May. The fix: a `months_reported` column (months with rows so far in the year) and a year-to-date goal of
`revenue_goal_usd * months_reported / 12`, in portable SQL. The definition lives in six places, and all six change
together: `lakehouse/02_gold.sql` line 25; `lakehouse/04_definitions.sql` lines 64 and 67 (the text and the twin);
`lakehouse/genie.py` lines 34 and 138; `evals/benchmark.yaml` q09 (line 87); the schema hint in `harness/tools.py` line
187; and the months-elapsed projection in `lakehouse/07_agreement_watch.sql` lines 22 and 92, which follows the same
rule (CLAUDE.md rule 2). Everything reruns in DuckDB and on Databricks. Only Sunbelt's rows change, and by a lot: May
2026 goes from 74.2 to 123.6 and Sep 2026 from 106.0 to 136.3. The planted panel shows the before and after. A pytest
pins Sunbelt's May 2026 pace at 123.6, and the ground-truth questions and the Genie benchmark rerun afterward.

## The talk

About 36 minutes on the main path. Openers are the hairline figures in `docs/diagrams/hairline`; numbered figures are in
`docs/diagrams`. Every data figure carries "synthetic data" in its logo band.

| Id | On screen | Kind | Min |
|---|---|---|---|
| **1. The first answer** | | | **7** |
| title | The airliner, live, captioned with the talk title (draft: "Fairshare: sales answers you can check") | live page | 0.5 |
| problem | The two slow steps today: a share question becomes a ticket to sales BI, and a pre-call pack is built by hand. He asks the room how long a pack takes them now | native | 1 |
| what | What I built, in one line, and its two modes, Ask and Delegate | native | 0.5 |
| query-opener | The query opener | live page | 0.25 |
| ask | Live Ask: "Why is Harbor Business Travel down in September?" He clicks the share effect to show its rows | demo | 3.5 |
| director | 04, what just happened behind that answer | animated | 1.25 |
| **2. The data** | | | **11.75** |
| elevator-opener | The elevator opener | live page | 0.25 |
| pipeline | 06, where the numbers come from | animated | 1.5 |
| row | What is in a row: `fact_agency_sales_monthly` and `fact_market_capacity`, each column in plain words next to one row from the data | native table | 1.75 |
| coverage | 10, every agency by every month | image | 0.75 |
| revenue | 11, AA revenue by month, 2025 against 2026 | image | 0.75 |
| planted | 14, what I planted in the data and what cleaning did | image | 2 |
| checks | The basic checks: what each should be and what it is | native table | 0.75 |
| numbers | 09, the seven numbers | image | 1.5 |
| share-fair | 12, AA share against fair share for each agency, sorted by the gap | image | 1 |
| moved | 08, why Harbor moved | animated | 1.5 |
| **3. What I built** | | | **10.5** |
| stack-opener | The stack opener | live page | 0.25 |
| system | 01, the system | animated | 2.25 |
| sieve-opener | The sieve opener | live page | 0.25 |
| checked | 02, how an answer gets checked, with the benchmark result said here | animated | 2 |
| riffle-opener | The riffle opener | live page | 0.25 |
| delegate | 03, agents draft and people decide | image | 1.25 |
| precall | Live Delegate: open the pre-call pack the 6 am job wrote and approve it | demo | 3 |
| built-how | How I built it: Claude Code, the rules file, the commit check, and the hook that blocks destructive commands | native | 1.25 |
| **4. Proof and next** | | | **7** |
| measured | What I measured, in plain words, including the misses | native | 1.75 |
| limits | What it does not do yet | native | 1 |
| know | How we would know it worked | native | 1 |
| at-aa | 15, the same layers at AA, each table next to the AA feed that would replace it | image | 1.5 |
| azure | Possibilities on Azure, each one tagged "Possibility" | native | 0.75 |
| start | How I would start at AA, with the report link. It stays up through Q&A | native | 1 |

Backup slides come after `start` and are reachable from the notes window's outline: `ask-still` and `precall-still` (a
still of a good run, for when a demo stalls), `manager` (05, animated), `fair` (07), `words` (booking, seat, share, fair
share, pace), `dashboard` (the AI/BI dashboard, opened from a link on the slide), `choices` (the design choices and what
I chose against), `dict-agencies`, `dict-goals`, `dict-agreements`, `dict-crm`, `dict-bookings`, `dict-ops` (the other
tables, column by column), `security`, `foundry-eval`, `agents` (the four agents), `platform` (Free Edition limits).

Clock checkpoints on the notes window: `precall` done by minute 29, `start` by minute 36.

**The short path.** Eight slides tagged for a ten-minute slot, each with its own minutes: `title` (0.5), `problem` (1),
`what` (0.5), `ask` (2.5), `system` (1.5), `precall` (2), `measured` (1.75), `start` (1), about 11 minutes. The notes
window switches between the full and short paths at any point, and the arrow keys follow the path that is on. Its
checkpoints: `ask` done by minute 5, `start` by minute 11.

## The first 90 seconds and the close

The title stays up while he says his name and one line about himself, then the problem in the words he heard in round
one. Before anyone asks, he says the agencies, sales, contracts and seats are made up. "About 35
minutes, stop me anywhere." He presses Enter on the Harbor question by about minute 2.

The last slide is `start`: how he would start at AA, the at-AA figure beside it, and the report link. It stays on the
screen through the questions, so the talk ends on the job.

## Examples and analogies

On screen: the example from the data, never the analogy. Spoken: an analogy only where the idea is technical, and the
three that earn it are marked. The report uses every row, corrected as below. Numbers came from queries on October 19.

| Idea | Analogy | From the data | Where |
|---|---|---|---|
| A ratio is computed at the grain asked | Batting averages: add up hits and at-bats, never average the averages | In Q3 2026 the average of the twelve agencies' AA shares is 39.7%, but AA's share of their combined sales is 38.4% | Spoken on `numbers` |
| The verifier | A newspaper fact-checker holding the source documents | One sentence the verifier cut, found in the harness tests or an MLflow trace when the facts are built; and its limit: on Oct 13 one wrong answer passed it with every number from a query | Spoken on `checked` |
| A gap is not a zero | A missing page in a logbook against a page that says "no flights today" | Sunbelt Vacations has no rows for Mar and Apr 2026 (24 rows). Northstar Leisure has a real $0 of AA on SEA-DEN in Jan 2026, with $13,616 sold on other carriers | Spoken on `planted` |
| Running as the viewer | A hotel key card that opens only your own doors; the app has no master key | Genie and every query run with the viewer's token, never the App's service principal | Report, and `security` |
| Tool-less writers | A writer with a fact sheet and no phone | A planted instruction in a CRM note was ignored (`docs/limits.md`) | Report, and `agents` |
| Fair share | Shelf space: a brand with about 38 of every 100 feet of shelf would expect about 38 of every 100 dollars | AA flies about 38 of every 100 seats on DFW-ORD (made up). In Q3 2026 Summit Travel Partners sent 53.5% of its DFW-ORD sales to AA against a fair share of 37.6%, $88,391 above it. The agreements pay on revenue share. Summit's passenger share on DFW-ORD in Q3 2026 is 52.4% against 53.5% by revenue, and across the twelve agencies the two are never more than 1.7 points apart | Report only |
| Volume, mix, share | A store's sales: fewer shoppers, shoppers moving to aisles where we sell less, or shoppers taking another brand in the same aisle | Harbor's AA revenue fell $64,795 from Sep 2025 to Sep 2026: volume +$32,836, route mix -$140, share -$97,491. The generator holds route weights fixed, so mix is about 1% of a typical move | Report only |
| A slow slide | A regular customer who comes in less each month, with one bad stretch | Harbor's AA share went from 44.3% in Sep 2025 to 34.2% in Sep 2026, dipping to 21.7% in Jun 2026 and back to 35.6% in Jul | Report only |
| Bronze, silver, gold | Groceries as delivered, washed and chopped, then plated | 27,967 booking rows as delivered, 27,961 after cleaning | Report only |
| Duplicate rows | A receipt scanned twice | Removing six duplicate tickets took $4,920.87 out of corporate bookings | Report only |
| Inconsistent labels | A sign-in sheet where people write their names differently | 16 spellings of four channels, from "Direct" (6,613 rows) to " ndc " (2 rows) | Report only |
| Pace | Marathon splits | Only Harbor (96.1) and FareHub Online (97.2) are under 100 in Sep 2026; the made-up goals are flat across the year and soft | Report only |
| A person approves | A pharmacist checks before handing anything over | Nothing lands in `ops.crm_activities` until a person approves | Report only |

On `numbers`, he shows how fairshare computes fair share and asks the room where AA's own version differs. It lives once,
in the metric view, so swapping AA's in is one change.

## How the numbers stay honest

- `docs/diagrams/src/deck_facts.py` runs fixed queries against DuckDB and writes `web/src/deck/facts.json`. It absorbs
  `data_numbers.py` and `data_numbers_2.py`. Each fact keeps its SQL and its grain.
- Slides and notes write numbers as placeholders, such as `{summit_q3_gap_usd}`, and the deck fills them in. One vitest
  fails when a placeholder has no fact, and when a digit appears in slide or note text outside a placeholder. An
  allowlist covers years, quarters, figure numbers, and model and product names.
- One pytest in `evals/` fails when `facts.json` is stale against a fresh DuckDB run. Test counts stay out of the facts,
  so a new test never makes them stale.
- Values that live only on Databricks or in result files (the benchmarks, the Foundry evaluation) sit in a dated section
  with their source, which the freshness check skips. If the CLI cannot reach one, Chirag runs the SQL.
- A few facts are also checked against the metric view's own values in `app/cache/kpi_parity.csv`, since DuckDB has no
  metric view.
- The column meanings are written once, in `deck_facts.py`, with each column's type and one example value. A pytest
  checks that every column the deck shows still exists. The report reads the same file.
- The `checks` slide and a pytest run the same checks: 3,000 rows equal 12 agencies by 12 routes by 21 months minus
  Sunbelt's 24; one row per agency, route and month; every sales row has a seats row; no nulls; AA never above the market;
  both facts end in Sep 2026; cleaning removed $4,920.87 of duplicates.
- The charts query DuckDB inside their own builders, as the existing data diagrams do.

## How each kind of slide renders

The deck draws a 1280 by 720 stage scaled to the window with CSS `zoom`, on white. Iframes get `pointer-events: none`, so
a click never moves focus into a frame and a resting cursor never pauses a hairline figure.

- image: a PNG from `docs/diagrams/export` or `docs/diagrams/hairline/png`, imported with `import.meta.glob` from
  `../../../docs/` (relative to `web/src/deck/`) with `?url`. Vite writes it into `web/dist/assets` with a hash, and the
  App serves that folder. Vite serves any imported file in dev, including ones outside `web/`, so there is no config change. A test asserts every slide's asset key is in the map, because a glob
  that matches nothing returns an empty map without an error. The deck adds a small right-aligned eyebrow in the figure's
  logo band naming the part.
- live page: a hairline page in an iframe, mounted when its slide shows, so its motion starts on arrival.
- animated: a diagram's motion page in an iframe with `?embed=1`. Embed mode lives in `aa_motion()` in
  `docs/diagrams/src/aa.py`: a small script before the controller sets `data-motion-mode="manual"`, so the page opens at
  step 0, paused, instead of playing on load; CSS hides the eyebrow, title and buttons without removing them (the
  controller reads them) and fits the figure to the window. The deck drives the controller through its own key map: a
  non-bubbling keydown, built with the frame's own `KeyboardEvent` and dispatched on the frame's `[data-motion-root]`
  element (the controller listens there, not on the document): Home or End on arrival (End when arriving backward),
  then ArrowRight or ArrowLeft on each press. While `data-step-current` is below `data-step-count`, a press moves the
  diagram; after that, it moves the deck. With reduced motion on, the slide counts as zero steps. In embed mode the Google Fonts stylesheet loads
  without blocking, so a slow font never holds the controller back; the text swaps in when the font arrives. The `animated()` page
  builder moves from `exploded.py` into `aa.py` so the new animated versions share it.
- native: React layouts in the app's AA tokens, with the same logo band as the figures: statement, tiles, table, demo.

The first build step checks embed mode on the deployed App, because nothing in the repo shows whether the Apps proxy
blocks framing. If it does, animated and live slides fall back to their PNGs.

## New figures

All in `docs/diagrams`, made with diagram-design and the american-airlines profile, built by Python builders in
`docs/diagrams/src` that query DuckDB, checked by the plugin's verifiers and `lint.py`, exported to PNG (2560 by 1440)
and SVG, each with "synthetic data" in its logo band:

- `10-coverage.html`: 12 agencies by 21 months, shaded by how many routes each agency reported that month. Sunbelt's two
  empty months show as holes, and the Northstar zero is called out by its route.
- `11-revenue-by-month.html`: a line chart of AA revenue by calendar month, 2025 and 2026 as two lines, with Mar and Apr
  2026 marked because Sunbelt is missing from them.
- `12-share-vs-fair.html`: a dumbbell chart for Q3 2026, one row per agency sorted by the gap, AA share against fair share.
  The caption says fair share barely moves because the seat shares are made up.
- `14-what-was-planted.html`: six small panels. Four are data problems with what cleaning did: the channel spellings (16
  to 4), the duplicate tickets (removed), the Sunbelt gap (left missing, and pace now counts only reported months), and
  the Northstar zero (kept, because it is real). Two are real drops the app should catch: Harbor's share across all 21
  months against fair share, and the two declining corporates, by name.
- `15-at-aa.html`: a version of 01 with three marks. Running today: Databricks, the Foundry writers, MLflow. Built but not
  deployed: the harness as a Foundry hosted agent. Waiting on AA's own Microsoft account: Fabric and OneLake, the
  Dataverse mirror, Teams through Copilot Studio, Entra ID sign-in. Each table sits next to the AA feed that would replace
  it, hardest first: the agency's sales on other airlines.

Animated versions in the plugin's reveal mode, inside its motion budget of at most eight steps: 02, 04, 05, 06 and 08.
The title page's caption changes in `docs/diagrams/hairline/src/pages.mjs`.

## The notes window

P on the deck opens `/present?notes` in a second window. The windows share the slide through a `BroadcastChannel`: the
deck posts its slide when it mounts and on every move, and a window that receives a slide applies it without posting it
back. The notes window shows the current slide, the next slide, the note, the time since the first move, how far ahead or
behind plan he is against the checkpoints, the outline of every part and slide including backup, and the demo buttons.
Outline buttons lose focus after a click, so Space never acts twice. If the room mirrors the laptop instead of extending
it, the notes would show on the big screen; the fix is the macOS display setting.

Keys work in either window. Right arrow, Space and Page Down go forward. Left arrow and Page Up go back (clickers send
Page Up and Page Down). Home and End go to the first and last slide of the main path. S jumps to the next part. The slide
id lives in the URL hash (`/present#share-fair`), so a reload or a return from a demo lands on the same slide.

Full screen uses Chrome's own (Control Command F), which stays on through a demo jump.

## Demo jumps

Every jump runs in the deck's tab. The notes window's demo buttons only post the jump to the deck.

- Ask: the deck saves the slide id in `sessionStorage`, sets the app to Ask through the store, and calls
  `location.assign("/?q=<question>")`. The app reads `q` once, puts it in the input box through the existing `prefill`,
  removes `q` from the URL, and focuses the input the way the agreement prefill already does, so Enter works. No open
  chat comes for free, because `activeId` is never saved.
- Delegate: the same, with the two store calls the app's own `openDelegate` makes, for `precall`, then `/`.
- Dashboard (backup): a link on the slide opens it in a new tab. Closing the tab returns to the deck.
- While the saved slide id is set, the app shows a small "Back to the deck" button in a corner that returns to
  `/present#<id>` and clears it.
- The notes window calls `api.agencies()` when it opens and every eight minutes while open. It runs one small query and
  is never cached, so it keeps the SQL warehouse awake (it stops after ten idle minutes).

## Demo day

- The day before: `apps get`, then start and deploy if needed, log in, run `harness/keepwarm.py`, and ask each demo
  question once on the App.
- In rehearsal, ask the Harbor question ten times on the App. If any run fails, the Ask demo moves to the laptop on
  gpt-5-mini, which serves `/present` too.
- The answer cache (`app/cache/answers.json`, recorded by `harness/cache.py`) is read only when the model is off
  (`FAIRSHARE_MODEL=none`), so it helps only the laptop with no model. The Harbor question goes into it for that case.
  On the App, the still is the fallback.
- Record ten rehearsal times for the Harbor question. On Oct 13 the App's model answered in about 26 seconds at the
  median and 37 at most.
- Open `/present?notes` on the laptop screen first, then move the deck window to the room's screen and make it full
  screen. Rehearse this once with a real second screen.
- Check that fonts.googleapis.com loads on the venue network and on the hotspot.
- Take a still of a good run of each demo for `ask-still` and `precall-still`. Record the run that
  `docs/failure-modes.md` promises as `docs/demo-recording.mp4`; it does not exist yet.
- While an answer runs, talk through the steps on screen. At 60 seconds, go to the still. Never debug live.
- For Delegate, open the page the 6 am job already wrote and approve it live. A fresh run takes about two minutes.
- Find out how the screen connects. Keep the slide PNGs on the laptop and the phone, and bring a hotspot.

## Speaker notes

Each note is under 40 words: the point, the number he must say, the handoff to the next slide, and for demos the clicks
and the fallback. Written the way he talks (the voice sample in memory), roles and never names, numbers as placeholders,
and a humanizer pass on every note.

## Build order

1. The fixes, as their own change: the labels, QSI, the parity text, the six pace edits, the figure rebuilds, the Genie
   update, and the two stale Delegate tests. It needs the gate and Databricks, and it ships with its own commit and
   deploy.
2. A two-slide `/present` (one PNG, one animated iframe), deployed to the App before any other slide, to prove framing
   and the step handoff where the talk will run.
3. The facts, the new figures, and the animated versions.
4. The rest of the deck, the notes window, the short path, and the demo jumps.
5. The notes, then rehearsal.

## Files

- `web/src/components/Present.tsx`: the deck and the notes window
- `web/src/deck/slides.ts`: every slide and its note
- `web/src/deck/facts.json`: generated by `deck_facts.py`
- `web/src/lib/deck.ts` and `deck.test.ts`: navigation, timing, and the content checks
- `web/src/App.tsx`: the `/present` route, the `q` prefill, and the back button
- `web/src/components/Sidebar.tsx`: a Present entry in both sidebar widths
- `web/src/copy.ts`, and `web/index.html` (adds Geist Mono)
- `web/e2e/present.spec.ts`, and `web/e2e/delegate.spec.ts` with its two stale tests fixed
- `docs/diagrams/src`: `deck_facts.py`, the new builders, embed mode and `animated()` in `aa.py`, the animated versions
- `docs/diagrams/hairline/src/pages.mjs`: the title and elevator captions
- `lakehouse/02_gold.sql` (pace), `03_metric_view.sql`, `04_definitions.sql`, `genie.py`: the fixes first
- `evals/test_deck_facts.py`: freshness, the checks, the columns the deck shows, and Sunbelt's pace
- `docs/diagrams/README.md`: the new figures and the deck

There is no server change: `server/static.py` already serves `/present` and the built assets.

## Tests

Each piece starts with a failing test.

- Vitest: navigation (next, back, clamping, skip to the next part, hash to slide); the animated handoff (given a step and
  a count, whether a press moves the diagram or the deck, and arrival at step 0 or at the end); timing against the
  checkpoints; and content rules over `slides.ts`. The content rules: every slide has a note under 40 words; every asset
  key is in the glob map; no em or en dashes; no interviewer names, read from `.env` and never from a list in the repo;
  every Azure possibility is tagged and nothing built is tagged; every placeholder has a fact; no bare data numbers; the
  main path runs 35 to 40 minutes.
- Pytest: `facts.json` is fresh; the basic checks hold; the columns the deck shows exist; Sunbelt's pace counts only
  reported months.
- Playwright: the deck opens on the title; keys move it and the hash follows; an animated slide takes as many presses as
  it has steps before the deck moves; the notes window follows the deck; the Ask jump fills and focuses the box and the
  back button returns to the same slide; the sidebar entry opens the deck. Routes use `context.route`, so the notes
  popup is covered, and Google Fonts requests are aborted, because the font stylesheet holds back the motion controller.
  `present.spec.ts` also runs once against uvicorn serving `web/dist`, through `BASE_URL`, so the production path is
  tested.
- The two stale Delegate tests are fixed first, so the browser suite starts green. Then the gate, a deploy, and
  screenshots of each part from the App.

## Out of scope

The report (the next spec; it reads the same `facts.json` and carries the full set of analogies). Real T-100 seats (they
need a generator rework). A way for an account manager to flag a wrong answer (it goes on the `start` slide as a first
step at AA). A public GitHub repo (`built-how` shows the rules, the gate and the hook without a link). Notes on a phone.
A PDF or PowerPoint export of the deck. Animating the new data charts.

## Risks

- The Apps proxy may block framing. The first build step checks it on the deployed App, and the PNGs are the fallback.
- The App's own model got 15 of 20 right on the benchmark, and answers took up to 37 seconds there. The demo-day steps
  and the laptop fallback cover it.
- The App on Free Edition stops when idle. The demo-day checklist covers it.

## What the advisors changed

Adopted, after checking each claim against the code and data:

- Sales leader: a first live answer within two minutes; "synthetic data" on every data figure; the misses on `measured`
  (Oct 13, the App's model Qwen3-Next: 15 right, 3 partly right, 2 wrong, and one wrong answer passed the verifier; Genie
  alone 20 of 20 on Oct 14); a `know` slide (active account managers, prep time per call, tickets to sales BI, drafts
  approved with light edits); AA feeds on the at-AA figure; `built-how` for the posting's line about building with AI
  tools and GitHub; asking the room how long a pack takes.
- Data lead: the pace bug; the parity story as it happened; the made-up seat label; QSI out; pace as a ranking with soft
  goals said once; the corrected mix analogy and whole dollars; "planted" for the traps; the checks slide and pytest; a
  completeness grid, a dumbbell instead of a scatter, and no seat-share bar chart (it would show twelve generator
  constants).
- Presentation coach: a shorter main path with backup for the rest; analogies spoken, not shown; notes under 40 words;
  the first 90 seconds; closing on `start`; the demo-day checklist; saying the benchmark on `checked`.
- Engineer: embed mode through manual mode and the controller's key map; jumps from the deck's tab; no Vite config change
  and no copy fallback; `pointer-events: none` on iframes; a lighter facts check; the prefill and focus; `context.route`,
  aborted fonts, and one run against the built app; checking framing on the App first; two more mislabeled places.

Fable review, after checking each claim:

- Adopted: the short path for a ten-minute slot; all six pace edits and the size of Sunbelt's change; keys dispatched on
  the frame's `[data-motion-root]`; the answer cache scoped to the laptop and the still as the App's fallback; clicking,
  not hovering, a number to show its rows; fonts that never block the controller; 01's Agents label; the 1.7-point
  wording; the notes window placement; the build order with the fixes first and a two-slide proof; the aa_share wording
  on the parity story.
- Not adopted: a Vite config change for dev (Vite adds every imported file to the files it may serve,
  `web/node_modules/vite/dist/node/chunks/config.js` lines 22754 and 27429); two more seat-label files (in
  `blueprint.py`, "real" means a cell's technical name, and `day0.md` is the download instruction); self-hosted fonts
  (a non-blocking load covers the risk with less); moving the data slides out of the full path (the short path covers a
  tight slot instead).

Not adopted from the first four:

- Cutting the openers. Chirag kept all five, at about 15 seconds each.
- A 30-minute main path. Chirag chose 35 to 40.
- A line about a round-one stumble, which has no record anywhere.
