# fairshare: the /present deck, retold

## Why

Chirag presents fairshare at the American Airlines on-site in the week of 2026-11-02. The room holds a sales director and
a data lead, and the talk has one job: the room leaves wanting to hire him. He walked the current deck at `/present`
(built from `docs/superpowers/specs/2026-10-19-present-design.md`, merged as PR #1) and found three problems.

- The story front-loads detail. The data part runs ten slides before the room sees the system, and the second slow step
  (pre-call packs) is fixed long after the first.
- Nothing is disclosed progressively. Every text slide shows all its points at once. The animated diagrams hold every
  step that has not come yet at 12% opacity (the reveal mode of the diagram-design plugin sets
  `.motion-ready [data-motion-item] { opacity: .12 }`), and `SlideView.tsx` shows the finished figure as a thumb until the
  frame is ready. The room sees the end before he gets there.
- The type hierarchy is all over the place. On `revenue`, three large italic lines under the chart pull as much weight as
  the chart. Text slides hug the top and leave the bottom third empty, and on `problem` the points are larger than the
  title. Some slides, like `planted`, put six things in front of the room at once.

He calls storytelling and progressive disclosure the key quality bar. Everything below serves that.

## What stays

- The deck stays at `/present` in the React app, with the live demo jumps into Ask and Delegate, the notes window, the
  short path, the clock, the 1280 by 720 stage and the hash URLs. The frontend-slides plugin was tried and removed; do
  not use it.
- The diagrams keep their content, except where this document changes it. Their builders stay in `docs/diagrams/src`,
  and every number still comes from `docs/diagrams/src/deck_facts.py` through `web/src/deck/facts.json`.
- The hairline openers keep playing on their own.
- The content rules in `web/src/lib/deck.test.ts` stay, updated for the new topics.

## Goals

1. Tell the talk as five topics between three bookends, in the order a hiring panel would ask its questions.
2. Show nothing before it is introduced, on every kind of slide.
3. Move every visual in: charts draw when the slide opens, and annotations and points arrive one per press.
4. Give every slide one dominant element and one consistent type ramp, in the AA colors and fonts.
5. Disclose one thing per press, and cap what a finished slide holds.
6. Put a frame on every slide: the AA logo, a topic tracker and a slide number.
7. Replace `measured` with guardrails and evals that explain themselves.
8. Fix the explainability gaps he named: units on `row`, why each check matters, how each of the seven numbers is
   calculated, what route mix means.

## Non-goals

- No app features, no changes to data, definitions or calculations, and no new data.
- No new fonts, frameworks or plugins.
- No PDF or PowerPoint export, no report, no public repo.

## Anti-goals

The redesign fails, even if every test passes, if any of these happen:

- The room sees a later point, step or annotation before he introduces it, faded or not.
- A number appears that no query or dated fact backs.
- A slide uses a color or font outside the app's theme and the diagram profile's darkened text colors.
- A title could sit unchanged in someone else's deck.
- Motion draws attention to itself: bounces, long transitions, or anything that moves after it has arrived.
- A live demo jump breaks.
- An interviewer's name appears anywhere, or any copy carries an em or en dash.

## Constraints

- Ready for rehearsal by Friday 2026-10-30, deployed to the Databricks App. The App stops a day after each deploy or
  start, so he restarts it the day before the talk and that morning.
- Work on branch `deck-redesign`, cut from the merged `main` (2e10e85). Commit only with his approval; for the last plan he
  approved one commit per task.
- Colors and fonts come from `web/src/styles.css`: ink `#36495a`, ink-2 `#627a88`, line `#d0dae0`, line-2 `#e6ebef`,
  surface `#f2f5f8`, blue `#0078d2`, navy `#00467f`, red `#c30019`, tint `#e6f1fb`, grey `#9da6ab`, and the
  `--font-sans` stack (American Sans, falling back to Inter). Geist Mono stays for labels. The figures use darker
  versions for text, set in `~/.diagram-design/profiles/american-airlines.md` so text clears 4.5:1 contrast: `#006cbf`
  for blue text, `#5a7181` and `#566d7b` for muted text. Those count as the AA theme. The new frame and the native
  slides use the same text colors as the figures, and the lighter values stay for fills and large type.
- Numbers only from queries: slides and notes write `{placeholders}` that `facts.json` fills. A value that lives only
  on Databricks or in a results file goes in the dated section with its source.
- Made-up data stays labeled as made up.
- Roles only, never names. The blocklist lives in `.env` as `FAIRSHARE_DECK_BLOCKLIST` and is never printed.
- The gate stays green: pytest, vitest, Playwright and the ground-truth check (`evals/run_benchmark.py --check`).

## The talk

Five topics, each with a name the tracker shows and a line the agenda shows. Chirag approved these words verbatim:

1. **Two slow steps.** What I heard in round one about share questions and pre-call packs.
2. **Ask and Delegate.** The app answers a share question and drafts a pre-call pack, live.
3. **Where the numbers come from.** The data behind the seven numbers, and why Harbor fell in September.
4. **Checks and misses.** How the app checks each number, what the tests found, and what it can't do yet.
5. **Starting at AA.** The same layers on AA's own data, and the first four steps.

The order answers a hiring panel's questions in turn: does he understand our problem, can he build something that works,
does he know our data, can we trust it, can he do this here. Those questions never appear on screen.

The main path, at about 35.5 minutes. "Stepped" means the slide discloses one step per press.

| Id | Topic | On screen | Kind | Min |
|---|---|---|---|---|
| welcome | bookend | The airliner animation and the talk title, with his name, the role he is interviewing for, and one line that every number comes from made-up data | live page | 0.5 |
| agenda | bookend | The five topic names with their lines, one per press | native, stepped | 0.5 |
| problem | 1 | The two slow steps, one per press, then the question to the room | native, stepped | 1 |
| what | 2 | Ask, then Delegate, one per press | native, stepped | 0.5 |
| query-opener | 2 | The query opener | live page | 0.25 |
| ask | 2 | Live Ask, the Harbor question | demo | 3.5 |
| director | 2 | 04, what happened behind that answer | animated | 1.25 |
| riffle-opener | 2 | The riffle opener | live page | 0.25 |
| delegate | 2 | 03, agents draft and people decide | animated (new) | 1.25 |
| precall | 2 | Live Delegate, the pre-call pack | demo | 3 |
| stack-opener | 3 | The stack opener | live page | 0.25 |
| system | 3 | 01, the five layers | animated | 2.25 |
| elevator-opener | 3 | The elevator opener | live page | 0.25 |
| pipeline | 3 | 06, where the numbers come from | animated | 1.5 |
| row | 3 | One row of each fact table, with units | native, stepped | 1.75 |
| revenue | 3 | 11, AA revenue by month | animated (new) | 0.75 |
| checks | 3 | The four basic data checks that matter most, each with what it guards against | native, stepped | 1 |
| numbers | 3 | 09, part one: AA revenue, AA share and fair share, each with how it is calculated | animated (new) | 1 |
| gaps | 3 | 09, part two: the share gap in points and in dollars, year over year, and pace | animated (new) | 1 |
| share-fair | 3 | 12, AA share against fair share, decluttered | animated (new) | 1 |
| moved | 3 | 08, why Harbor moved, with route mix explained | animated | 1.5 |
| sieve-opener | 4 | The sieve opener | live page | 0.25 |
| checked | 4 | 02, how an answer gets checked | animated | 2 |
| guardrails | 4 | Four guardrails, one per press | native, stepped (new) | 1.5 |
| evals | 4 | The answers: Genie and the whole app, one per press | native, stepped (new) | 1 |
| evals-more | 4 | Foundry's evaluators, the nightly comparison and the commit check, one per press | native, stepped (new) | 1 |
| limits | 4 | What it can't do yet | native, stepped | 1 |
| at-aa | 5 | 15, the same layers at AA | animated (new) | 1.5 |
| azure | 5 | Possibilities on Azure, each tagged Possibility | native, stepped | 0.75 |
| start | 5 | The first four steps at AA | native, stepped | 1 |
| know | 5 | How they would know it worked | native, stepped | 1 |
| thanks | bookend | Thank you, his name, his email, and an invitation to ask questions | native | 0.25 |

`coverage` and `built-how` leave the deck. `planted` moves to the backups. `measured` is replaced by `guardrails` and
`evals`. The point of `built-how` that survives is the commit check, which becomes one of the evals.

**The short path**, at about 11 minutes: `welcome` (0.5), `agenda` (0.5), `problem` (1), `what` (0.5), `ask` (2.5),
`precall` (2), `system` (1.5), `evals` (1.5), `start` (1), `thanks` (0.25).

## Checks and misses

Chirag approved this content. Every number in it is a placeholder.

- `checked` keeps diagram 02, with each step hidden until he presses for it. Every number in an answer is matched to a
  row a query returned. A sentence with an unmatched number is cut, and the app shows the cut in red.
- `guardrails`, one per press, each with what it stops:
  - Every query runs with the viewer's own login, so Databricks applies that person's permissions.
  - SQL does all the arithmetic, and the model only writes the sentences.
  - The Delegate writers get a fact sheet and no tools. A writer ignored an instruction planted in a CRM note.
  - Nothing is recorded in the CRM until a person approves, and the app never sends an email itself.
- `evals`, one per press, each with what it tests, who grades it, the result and the miss:
  - Genie on 20 questions with known answers: 20 of 20 on Oct 19, after five questions were reworded to name their
    columns. Two earlier runs that day got 17 (a new dated fact; the source is the Oct 19 results in `evals/results/`).
  - The whole app on the same 20, graded by gpt-5-mini: 15 right, 3 partly right and 2 wrong on Oct 13. One answer gave
    up and still passed the verifier, because it had no numbers to check.
  - Foundry's evaluators on 23 Delegate pages: groundedness failed on one, and the prompt shield wrongly refused two
    until the rules moved into the agents.
  - Every night the six numbers with a Power BI version are compared with a SQL copy of it: 5 scheduled runs, 0
    differences.
  - Before every commit, the known-answer queries and the tests run, and a failure stops the commit.
- `limits` keeps today's content, redesigned and stepped.

The evals take two slides, because each eval carries four parts. The short path shows the first.

## Disclosure and motion

- A step that has not come yet is invisible, not faded. In the deck's embed mode (`EMBED_CSS` in
  `docs/diagrams/src/aa.py`), an item the controller has not reached has opacity 0. A standalone page may keep the
  plugin's own reveal look.
- A diagram's structure shows on arrival: its column headings, its actors, its axes and its frame, so the room knows what
  kind of picture it is looking at. Anything that gives the point away waits for its step: a legend or label naming the
  focal item, a value, a verdict, a caption. Today 02's legend says "Focal: the verifier" and 08's says "Focal: AA's
  share" on arrival; those move into the step that brings in their item. 01 keeps its assembled stack, since lifting
  the layers is its reveal, so the opacity rule above does not apply to its parts.
- A slide opens on its first step. Before an animated frame is ready, the deck shows nothing of the figure's later steps:
  no finished-figure thumb.
- Native slides get steps. The title shows on arrival, and each point, tile, table group or line arrives on a press. A
  press after the last step moves the deck. Arriving backward shows the slide complete, as animated slides already do.
- The figures that are images today become stepped pages, built in the plugin's reveal mode like 02, 04, 05, 06 and 08:
  `delegate` (03), `revenue` (11), `numbers` (09), `share-fair` (12) and `at-aa` (15). Each stays inside the plugin's
  motion budget (at most eight steps, twelve marked items, two at once); a figure that needs more becomes two slides.
- On a chart, the marks draw on arrival: lines trace left to right, bars grow from their baseline, dots follow their
  line. Annotations wait for presses.
- Motion is short and settles. Points fade in with a small rise. Nothing loops, bounces or moves after it arrives. The
  hairline openers are the exception and keep playing.

## Type and density

- One element leads on every slide. On a text slide it is the title. On a figure slide it is the visual, with the title
  second. Then come short notes beside the part they explain, and last the source line, smallest and grey.
- One type ramp for the native slides, written once as tokens: display numbers, title, body, a secondary note, the mono
  label and the source line. Titles in navy, body in ink, secondary text in ink-2, blue for the one focal element per
  slide, and red only for a cut or a miss.
- The figures follow the same order of weight. On `revenue`, the three italic lines become small notes beside the
  March and April band, one per press, and the legend goes, since both lines carry their year at the end.
- Content sits balanced in the space under the header. No slide leaves its bottom third empty because the content hugs
  the top.
- A thing is one point, tile, table row, panel or chart annotation. A stepped slide adds one thing per press. Earlier
  things stay on screen but recede to the secondary color, so the newest one leads. A finished slide holds at most five
  short lines, or at most four things that carry their own detail; past that it splits, as `numbers` and `evals` do.
  Arriving backward lands on the last step.
- The demo slides (`ask`, `precall`) follow the same ramp and spacing. The demo button shows from the start.

## The frame

- Top: the AA logo at the left, then the five topic names as a tracker, the current topic lit and a mark for which
  slide of the topic is showing.
- Bottom: the slide number at the right. At the left, the talk title, or "Synthetic data" on slides that show numbers
  from the data.
- In the deck a figure drops its own logo band, so every slide has one logo. The standalone exports in
  `docs/diagrams/export` keep their bands, and `evals/test_labels.py` keeps checking them.
- A figure fills the stage under the frame. The header covers the strip where the figure's own band sat, so every
  figure the deck shows keeps its content between y 64 and y 680 of its 1280 by 720 view box.
- `welcome` and `thanks` show the logo only: no tracker and no footer. `agenda` shows the footer but no tracker.
- The slide number counts the path that is on, so the short path reads 1 to 10.

## Bookends

- `welcome`: the airliner animation stays. Under the talk title: his name (Chirag Lakhanpal), the role as AA's posting
  names it (Analyst/Sr Analyst, Sales AI & Innovation), and one line that every number in the talk comes from made-up
  data.
- `agenda`: the five topic names with their lines, one per press. The tracker starts on the next slide.
- `thanks`: thank you, his name, his email (chirag.lakhanpal.cl@gmail.com), and an invitation to ask questions. No app link, since the App needs a login
  to his workspace, and no repo link, since the repo is private.

## Explainability fixes

- `row`: every example carries its unit. Dollars as `$80,582.47`, shares as percents, counts with separators, months as
  `Sep 2026`, and true or false in words. The two tables arrive as two steps.
- `checks`: the four checks that matter most to the room, each saying what it guards against in plain words, one per
  press. All eight stay in a backup table. Its title must not reuse "checks", which now names topic 4.
- `numbers` and `gaps`: the seven numbers over two slides, one per press, each with how it is calculated:
  - AA revenue is AA's revenue on the rows in question.
  - AA share is AA revenue divided by everything the agency sold on the same routes, all airlines together.
  - Fair share is AA's share of the seats on each route, weighted by how much the agency sold there. The seat shares are
    made up.
  - The share gap in points is AA share minus fair share.
  - The share gap in dollars is AA revenue minus what fair share would have brought in.
  - Year over year compares AA revenue with the same month last year.
  - Pace is revenue so far this year divided by the goal so far, counting only the months the agency reported. The pace
    card also says the goals are made up, so the label travels with the value it affects.

  The slide says where they live: six are measures in the metric view `gold.sales_metrics`, worked out from the gold
  tables when a query runs, so a share comes out right at any grouping; pace is stored in `gold.agency_pace`, because its
  goal is set per agency and year. It also says why they matter: Genie, the dashboard and Ask read the six from that one
  metric view, so their numbers agree.
- `share-fair`: fewer things at once, stepped. The builder picks which agencies carry the story.
- `moved`: route mix in plain words, the change from selling more on some routes and less on others, valued at last
  year's AA share on each route. For Harbor in September it barely moved, and the slide says so.

## Copy

- Every slide's copy and every speaker note follows the unslop rules (the `anthropic-skills:unslop` skill), on top of
  the existing rules: no em or en dashes, no interviewer names, placeholders for numbers, no bare data numbers, every
  Azure possibility tagged and nothing built tagged, notes under 40 words.
- A title passes when it could not sit unchanged in someone else's deck. "Ask and Delegate" passes; "What I built" does
  not.
- Notes keep his spoken voice (the voice sample in memory) and get rewritten for the new order and steps. A note may say
  where a press brings in the next point.

## Backups

The backups stay reachable from the notes window's outline. `planted` joins them as it is, and so does the full table of
all eight data checks. `measured` and `built-how`
go. `security` and `foundry-eval` keep only what the new main-path slides do not already say. Every backup gets the
frame, labeled Backup in place of a slide number. The two stills stay full bleed without the frame, since they are
screenshots with the app's own top bar.

## After the build

- Regenerate `interview-prep/American Airlines/aa-onsite-speaker-notes.md` (in jobflow) and update the slide ids in
  `aa-onsite-demo-day.md`.
- Update `docs/diagrams/README.md` for the new animated pages and the embed behavior.
- Deploy to the App, step through every slide there, and take screenshots of each topic for him to check.

## Tests to pin

- Native steps: a slide reports its step count, a press reveals the next step until the last and then moves the deck,
  and arriving backward shows the slide complete.
- In embed mode, an item the controller has not reached has opacity 0.
- Before a frame is ready, an animated slide shows none of its later steps.
- The tracker lights the right topic and position, the slide numbers count the path that is on, `welcome` and `thanks`
  show no tracker and no footer, and backups say Backup.
- The topic names and agenda lines match this document word for word.
- The main path runs 35 to 40 minutes and the short path about 11.
- The `row` examples carry their units.

## Decided by Chirag

The five topics, their names and agenda lines; the order, with Delegate next to Ask; the bookends and what each holds;
nothing visible before it is introduced; charts that draw on arrival with annotations per press; one point per press;
one dominant element; at most three things at once; the frame with logo, tracker and slide numbers; the Checks and
misses content; the explainability fixes; the cuts and moves; a diagram's structure showing on arrival while anything
that gives its point away waits for its step; unslop for all copy; titles specific to this talk; the
main path at about 36 minutes and the short path at about 11; the React deck, AA brand only, no frontend-slides.

## My calls

- The slide order inside each topic, the minutes, and the short path above.
- Which hairline opener opens which topic.
- The footer's left text, no tracker or footer on `welcome` and `thanks`, numbers that count the path that is on, and
  Backup in place of a number on backups.
- Figures fill the stage under the frame and keep their content between y 64 and y 680.
- Figures dropping their logo band inside the deck.
- `thanks` stays up through the questions, where the old spec kept `start` up.
- The data checks slide stays in topic 3 under a new title.
- The welcome slide gives the role in AA's own words from the posting, so it picks no level.
- Native steps under reduced motion still step, without the movement.
- What counts as one thing, earlier things receding as the next arrives, and the caps of five short lines or four
  detailed things, which split `numbers` and `evals` into two slides each and leave four checks on the main path.
- The figures' darker text colors count as the AA theme, and the frame uses them too, so nothing gets re-skinned.

## Left to the builder

- The exact type sizes, spacing and motion timings, inside the rules above.
- How the deck avoids the finished-figure thumb before a frame is ready.
- Which agencies `share-fair` keeps on screen, and how each figure splits its steps.
- New facts the copy needs, each from a query or as a dated fact with its source.
- What `security` and `foundry-eval` keep.
- The clock checkpoints for the new order, one per topic.

## Risks

- Five more animated pages mean more frames to load. The deck may need to preload the next slide's frame.
- The plugin's motion budget may force a figure into two slides, which moves the minutes.
- His email on `thanks` is one more place to scrub before the repo ever goes public.
