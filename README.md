# fairshare

"How did Summit do on DFW to Chicago last quarter versus last year, are they ahead of fair share, and what does their
contract say if they drop under 45%?" Today that question is a Power BI hunt or a ticket to the sales BI team and a few
days. This is a small version of the agent that should answer it in ten seconds, with the SQL attached, built on made-up
airline sales data in a couple of weekends.

It is one system, told as an account manager's Monday. It opens on the sales director's dashboard (an AI/BI dashboard on
the same metric view, standing in for Power BI: pace, share against fair share, what moved), which can say *what* and
*where* and stops there. The app is what happens next: one screen that opens on the month's summary, with a chat bar over
it, built for people who do not write SQL.

1. **The summary**: one sentence, five numbers, the three agencies that moved, who is behind pace. Under them, what is worth
   knowing this month before anyone asks: the clauses close to their line with the dollars at stake, a deal the CRM calls
   healthy while share fell, a share streak, the largest capacity move (or, for a month the DOT has not published yet, a note
   that its seats are last year's), last week's corporate bookings. Each line is template
   prose from a fixed query (`harness/signals.py`), checked by the verifier like every other sentence, with one action (ask,
   open the Delegate page, open the definition); the suggested questions under the chat bar follow these lines, and an answer
   about an agency carries the line about that agency. No model runs on this page. Every KPI word opens its definition,
   and six of the seven open their check against a SQL copy of the Power BI measure. "Write my Monday brief" turns it
   into prose: every number is checked against its query, a sentence the model wrote that no query supports is removed
   and shown, and a person approves and sends.
2. **Why**: ask why an agency is down. The change is decomposed into volume, mix and share, with a fair-share diagnostic
   (how much AA's own capacity explains). The parts sum to the total by construction; the model only writes.
3. **Ask**: share versus last year versus fair share, with the query one click away; what the agreement says (quoted, with
   file and page); and a question it refuses to guess at ("which agencies will churn": no churn model in the data, here is a
   labeled proxy instead). Follow-up questions continue the same Genie conversation.
4. **Definitions and parity**: each KPI written once in English, implemented in a Databricks metric view and, for six of
   the seven, as a SQL copy of the Power BI measure that a nightly check compares with the metric view to show where
   they disagree. In the app they are a hover and a click away, never a page.
5. **How this app gets an answer**: one window with the path a question takes, the benchmark scores, and the links to the
   Genie space, the dashboard, the traces and the code.
6. **Delegate**: the second mode. Four agents on one runtime, each a set of fixed queries, a tool-less writer (the frontier
   model when one is named), the same verifier on every sentence, and a person's approval before anything is sent or
   recorded: the Monday pre-call pack (one page per agency an account manager owns, with a drafted email), Agreement watch
   (every measurable clause in the agreements checked against the month, with a drafted notice or upsell), Prospect research
   (where the headroom is on a market, and what public sources say about the route, quoted with links), and CRM versus
   reality (open opportunities whose CRM health disagrees with the data, with a drafted correction). The unit a person
   decides on is a page (an agency, a clause, a market, a deal), not a run: the nightly job and Run now write the pages
   again, the older waiting version is retired, every refresh needs a fresh approval, and each page keeps its versions
   with who decided what and when; several pages can be approved or rejected at once. Every checked number explains itself
   on hover in plain words (what it is, which query returned it) and opens its rows on a click. The CRM is a synthetic
   stand-in shaped like Dynamics 365 Sales.

## Data

Real: the seats. `gold.fact_market_capacity` is public US DOT data, the T-100 Domestic Segment (All Carriers) file that BTS
publishes: scheduled passenger service on the twelve routes, both directions, January 2025 to September 2026 (`data/t100.py`
turns the BTS files into `data/t100/aa_seat_share.csv`, which `data/make_data.py` reads, so every row says `source = t100`).
AA's seats are AA's network: AA plus its own regional airlines Envoy (MQ), PSA (OH) and Piedmont (PT). Republic and SkyWest fly
for several airlines, American Eagle among them, and T-100 cannot tell which of their flights are AA's, so they count as other
airlines and AA's share is low. It is lowest on DCA-BOS, where Republic and SkyWest fly about a third of the seats (17.7% on
PHX-LAX and 8.5% on CLT-LGA, Jan 2025 to Jul 2026). BTS publishes about three months late: on
Oct 21, 2026 July was the newest month, so August and September 2026 repeat the same months of 2025 and say
`is_projected = true` (the metric view's `capacity_is_projected`; the home page and the deck say so too). Two routes where AA
flies almost nothing in T-100, PHX-SEA and SEA-DEN, became PHX-LAX and SEA-ORD with the same ids, regions and hub flags, so no
made-up sales number changed.

Made up: twelve travel agencies, ten corporate accounts, their monthly sales, goals, ticket-level bookings and four
agreements. Deterministic (`data/make_data.py`, seed 88201) with data-quality traps planted on purpose: dirty channel
labels, duplicate tickets, a gap, a collapse, a zero month. Nothing here is confidential and nothing is any airline's.

## Shape

```
T-100 seats (US DOT) + synthetic agency layer + 4 agreements
  -> Unity Catalog volume -> bronze -> silver -> gold            (Databricks Free Edition, catalog aa_demo)
  -> metric view gold.sales_metrics (one definition per KPI)      ops.kpi_definitions, ops.kpi_parity, ops.decomposition
  -> Genie Agent over the metric view
  -> harness (Microsoft Agent Framework): ask_metrics | run_sql | explain_change | search_contracts
     three rules (numbers only from tools; cite the SQL; "Could not verify" for the rest), a deterministic verifier
     on every answer, MLflow traces on laptop runs (FAIRSHARE_TRACES; the App runs without them), 20 benchmark questions in a pre-commit hook
  -> the agreements read once by the thinking model into gold.contract_clauses (page citations), checked monthly by SQL
     into ops.agreement_checks; a CRM stand-in (contacts, opportunities, activities) in gold; the app's own writes in ops
  -> Delegate (harness/agents.py): precall | watch | prospect | mismatch, each facts (SQL) -> prose (a writer with no tools,
     FAIRSHARE_THINKER for the frontier model) -> the verifier -> a person's approval (an email draft, a CRM row); runs in ops.agent_runs
  -> Lakeflow job (databricks.yml, a Databricks Asset Bundle): nightly bronze to gold, metric view, definitions, decomposition,
     the agreement checks, parity as tasks; on Mondays a task drafts and verifies the summaries; every night the agents
     write their runs, which wait for approval in the app
  -> AI/BI dashboard on the metric view (lakehouse/dashboard.py, the leadership view; Ask Genie goes to the same Genie Agent)
  -> the app (web/ React + server/ FastAPI, one process with the harness): on the laptop with the Foundry model, and as a
     Databricks App with the viewer's own identity and a Databricks-hosted model (app.yaml, lakehouse/app_deploy.py);
     at an airline: Teams via Copilot Studio, Power BI via
     the mirrored catalog, the agency portal, the harness hosted in Microsoft Foundry
```

`docs/architecture.svg` is the picture; `docs/walkthrough.md` is the ten-minute version. `docs/diagrams/` holds the presentation diagrams,
American Airlines branded, with slide images in `docs/diagrams/export/`.

## Run it

```
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
.venv/bin/python data/make_data.py            # CSVs; the seats come from data/t100/aa_seat_share.csv (data/t100.py makes it from the BTS files)
.venv/bin/python lakehouse/run.py             # local DuckDB lakehouse: silver, gold, definitions, decomposition
.venv/bin/pytest evals -q                     # identity of the decomposition, the silver traps, the verifier, the contracts
.venv/bin/uvicorn server.main:app --port 8000  # the API, offline (cached answers, template brief); then in web/: npm install && npm run dev
```

The app is `web/` (Vite, React, TypeScript, Tailwind; `npm run build` writes `web/dist`) served by `server/` (FastAPI, same
process as the harness). Conversations stay in the browser; only approved briefs are written to the lakehouse.

With Databricks and a model (`cp .env.example .env`, fill it in):

```
FAIRSHARE_BACKEND=databricks .venv/bin/python lakehouse/run.py        # bronze from the volume, metric view, everything else
FAIRSHARE_BACKEND=databricks .venv/bin/python lakehouse/parity.py     # metric view vs twins; --retired reproduces the red run
.venv/bin/python evals/run_benchmark.py --genie --harness             # Genie alone, then the full harness with the verifier and a judge
FAIRSHARE_BACKEND=databricks .venv/bin/python lakehouse/genie.py update && FAIRSHARE_BACKEND=databricks .venv/bin/python lakehouse/genie.py eval   # the space from code (instructions, trusted SQL, the same twenty benchmarks), then Genie's own evaluation of them
.venv/bin/python -m harness.agent "Which agencies are behind pace?"   # one question from the command line
.venv/bin/python -m harness.cache                                     # record the scripted answers for the offline fallback
.venv/bin/python lakehouse/dashboard.py push                          # the dashboard from lakehouse/dashboard.lvdash.json (build regenerates it, pull captures UI edits)
.venv/bin/python lakehouse/app_deploy.py create && .venv/bin/python lakehouse/app_deploy.py deploy   # the app inside the workspace; start before a demo
databricks bundle deploy && databricks bundle run fairshare_nightly   # the nightly job (databricks.yml): bronze to parity as tasks, the Monday drafts on Mondays, the agents every night
FAIRSHARE_MODEL=azure .venv/bin/python lakehouse/clauses.py extract   # the agreements -> data/out/contract_clauses.csv (reviewed, committed); `review` re-checks the quotes
FAIRSHARE_SEARCH=brave SEARCH_API_KEY=... .venv/bin/python -m harness.research fetch CLT-LGA   # public sources for a market into data/research
FAIRSHARE_BACKEND=duckdb .venv/bin/python lakehouse/job_tasks.py agents none   # every agent's run for the latest month, offline, waiting in the app
```

Delegate runs on the laptop against DuckDB with the template writers (`FAIRSHARE_MODEL=none`) or with a model; `FAIRSHARE_THINKER`
names the backend the writers use when it should differ from the chat loop's (azure for gpt-5-mini while the loop stays on a
cheaper model). Approving an item re-verifies any edit, writes a row in `ops.crm_activities` (the CRM stand-in) and opens the
mail draft; the app itself sends nothing.

The four writers are also agents the Foundry project owns (Build > Agents in the portal: `fairshare-precall-pack`,
`fairshare-agreement-watch`, `fairshare-prospect-research`, `fairshare-crm-vs-reality`). `lakehouse/foundry.py sync` pushes each
agent's instructions as a new version when they change, with the account's content filter policy as the guardrail
(`FOUNDRY_RAI_POLICY`, the policy's full resource id). With `FAIRSHARE_THINKER=foundry` the app calls the agent by name through
the project's Responses API and sends the FACTS block only (data, no rule sentences: those live in the agent, where the prompt
shield cannot mistake them for a jailbreak); the verifier then checks every number as before, and the run records which agent
version wrote it. When the guardrail refuses a page's facts, the template writes that page and says so in its note. `lakehouse/foundry.py eval` builds a dataset from local template runs (every page plus two
adversarial rows) and runs Foundry's quality and safety evaluators against each agent. It needs a one-time sign-in (`login`),
because the evaluation API wants a person's identity, not a key. First full run (Oct 15, 2026, agent version 3, 23 real pages
and 8 adversarial rows): every real page passed relevance, coherence, fluency and the four content harms; groundedness passed
on all but one page; the jailbreak rows were refused by the guardrail before the model ran; the indirect attack evaluator
flagged the planted rows and two normal pages, since it reads any "change this record" as manipulated content.

## Why these choices

- A metric view, not a table of shares: share is a ratio, and a table of pre-computed shares is wrong the moment someone groups differently.
- Genie inside a harness, not alone: Genie answers numbers; the harness adds documents, the decomposition, the refusal, and the verifier.
- The verifier before the human: the Monday-morning failure is a number nobody queried. Matching numbers to query results is deterministic and cheap, so it runs on every answer.
- Decomposition in SQL, prose in the model: arithmetic that must reconcile belongs in the warehouse.
- Genie as the user, not a service principal: per-user identity is how an agency portal shows each agency only itself, and it is also what keeps Genie free on a Free Edition workspace.
- Benchmarks in a pre-commit hook: twenty questions with known answers, rerun on every prompt or definition change.

## Status

Built with Claude Code under the rules in `CLAUDE.md`. Scores and limits are recorded as they are measured
(`evals/results/README.md`, `docs/limits.md`); nothing in this README is a number that was not measured.
