# fairshare

"How did Summit do on DFW to Chicago last quarter versus last year, are they ahead of fair share, and what does their
contract say if they drop under 45%?" Today that question is a Power BI hunt or a ticket to the sales BI team and a few
days. This is a small version of the agent that should answer it in ten seconds, with the SQL attached, built on public
airline data in a couple of weekends.

It is one system with five screens, told as an account manager's Monday. It opens on the sales director's dashboard (an
AI/BI dashboard on the same metric view, standing in for Power BI: pace, share against fair share, what moved), which can say
*what* and *where* and stops there. The five screens are what happens next:

1. **Monday**: the month's summary for a region. Every number carries a green badge that links to its query; a sentence the
   model wrote that no query supports is quarantined in a "removed before sending" box; a person presses send.
2. **Why**: an agency is down 15%. The change is decomposed into volume, mix and share, with a fair-share diagnostic
   (how much AA's own capacity explains). The parts sum to the total by construction; the model only writes.
3. **Ask**: share versus last year versus fair share; what the agreement says (quoted, with file and page); and a question
   it refuses to guess at ("which agencies will churn": no churn model in the data, here is a labeled proxy instead).
4. **Definitions and parity**: each KPI written once in English, implemented in a Databricks metric view and as a Power BI
   twin, with a nightly check that shows where they disagree. The run that caught a passenger-based "share" is on record.
5. **Under the hood**: the architecture, where each piece lives at an airline, benchmarks, traces, limits met.

## Data

Real: BTS T-100 Domestic Segment seats by carrier, route and month, filtered to twelve markets, giving AA's seat share
(the "fair share" denominator). AA network = AA plus the wholly owned Eagle carriers (Envoy, PSA, Piedmont); Republic
and SkyWest fly for several brands and are left out, so fair share is slightly understated. Months BTS has not published
yet carry the prior year's month and are flagged `is_projected`.

Made up: twelve travel agencies, ten corporate accounts, their monthly sales, goals, ticket-level bookings and four
agreements. Deterministic (`data/make_data.py`, seed 88201) with data-quality traps planted on purpose: dirty channel
labels, duplicate tickets, a gap, a collapse, a zero month. Nothing here is confidential and nothing is any airline's.

## Shape

```
BTS T-100 + synthetic agency layer + 4 agreements
  -> Unity Catalog volume -> bronze -> silver -> gold            (Databricks Free Edition, catalog aa_demo)
  -> metric view gold.sales_metrics (one definition per KPI)      ops.kpi_definitions, ops.kpi_parity, ops.decomposition
  -> Genie Agent over the metric view
  -> harness (Microsoft Agent Framework): ask_metrics | run_sql | explain_change | search_contracts
     three rules (numbers only from tools; cite the SQL; "Could not verify" for the rest), a deterministic verifier
     on every answer, OpenTelemetry traces to MLflow, 20 benchmark questions in a pre-commit hook
  -> AI/BI dashboard on the metric view (lakehouse/dashboard.py, the leadership view; Ask Genie goes to the same Genie Agent)
  -> Streamlit app: on the laptop with the Foundry model, and as a Databricks App with the viewer's own identity and a
     Databricks-hosted model (app.yaml, lakehouse/app_deploy.py); at an airline: Teams via Copilot Studio, Power BI via
     the mirrored catalog, the agency portal, the harness hosted in Microsoft Foundry
```

`docs/architecture.svg` is the picture; `docs/walkthrough.md` is the ten-minute version.

## Run it

```
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
.venv/bin/python data/make_data.py            # CSVs (synthetic fair share until data/t100/aa_seat_share.csv exists; see data/t100.py)
.venv/bin/python lakehouse/run.py             # local DuckDB lakehouse: silver, gold, definitions, decomposition
.venv/bin/pytest evals -q                     # identity of the decomposition, the silver traps, the verifier, the contracts
.venv/bin/streamlit run app/app.py            # the five screens, offline (template writer, no model)
```

With Databricks and a model (`cp .env.example .env`, fill it in):

```
FAIRSHARE_BACKEND=databricks .venv/bin/python lakehouse/run.py        # bronze from the volume, metric view, everything else
FAIRSHARE_BACKEND=databricks .venv/bin/python lakehouse/parity.py     # metric view vs twins; --retired reproduces the red run
.venv/bin/python evals/run_benchmark.py --genie --harness             # Genie alone, then the full harness with the verifier and a judge
.venv/bin/python -m harness.agent "Which agencies are behind pace?"   # one question from the command line
.venv/bin/python -m harness.cache                                     # record the scripted answers for the offline fallback
.venv/bin/python lakehouse/dashboard.py push                          # the dashboard from lakehouse/dashboard.lvdash.json (build regenerates it, pull captures UI edits)
.venv/bin/python lakehouse/app_deploy.py create && .venv/bin/python lakehouse/app_deploy.py deploy   # the app inside the workspace; start before a demo
```

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
