# fairshare: rules for working in this repo

One sales agent over one semantic layer, every number with its query. Read `README.md` for the shape; this file is the rules.

## Rules

1. Numbers come from tools. The agent (harness/agent.py) states only numbers returned by a tool call, copied at the same rounding. If a derived figure is useful, a tool returns it as a column; the model never computes. The verifier (harness/verifier.py) enforces this on every answer and is never bypassed.
2. Definitions live in one place. A KPI is defined in `lakehouse/03_metric_view.sql` (YAML) and described in `lakehouse/04_definitions.sql`. Changing a definition means: change both, run `python lakehouse/parity.py` on Databricks, and add or update a benchmark question in `evals/benchmark.yaml`. A pull request that changes a definition says so in its title.
3. No new tables outside `gold` and `ops`. Bronze and silver are rebuilt from `data/out` by `lakehouse/run.py`; never hand-edit them.
4. Nothing destructive. No `DROP`, `TRUNCATE`, or `DELETE` without a `WHERE`. `.claude/hooks/block-destructive.py` blocks these in edits and commands; `CREATE OR REPLACE` is the way to change a table.
5. Portable SQL. Everything except `00_bronze.sql` and `03_metric_view.sql` runs on both DuckDB and Databricks SQL: three-part names (`aa_demo.schema.table`), `NULLIF` for every division, `EXTRACT` for date parts, `CAST(x AS STRING)`, `QUALIFY`, `GROUP BY ALL`. Column aliases are case-insensitive: never reuse a name with different case (the `T_now` / `t_now` bug).
6. The gate runs before every commit (`.githooks/pre-commit`): the 20 ground-truth queries must run and `pytest evals` must pass. `FAIRSHARE_FULL_GATE=1` adds the Genie benchmark when Databricks is configured.
7. Secrets stay in `.env` (gitignored). The Databricks token is a personal token: Genie is called as the user, never as a service principal.
   Inside the App the viewer's forwarded token is bound per request (fairshare/dbx.py `bind`); nothing about a viewer lives in a module global.
9. Copy in the app (web/src/copy.ts) is full sentences a 12th grader follows; buttons are short verb phrases; no em dashes.
8. Dummy data stays dummy. Agencies, corporates and contracts are fictional; only the BTS T-100 seat data is real. Do not add anything that looks like a real customer, price list, or airline-internal figure.

## Layout

- `data/` generator (sales, goals, bookings, and the CRM stand-in), T-100 filter, contracts; `data/out/` the CSVs (committed, including `contract_clauses.csv`, the thinking model's extraction, reviewed) and the local DuckDB file (ignored); `data/research/` public sources per market for prospect research, quoted with links
- `lakehouse/` SQL in run order (`07_agreement_watch.sql` checks every clause every month), `run.py` (local or Databricks), `parity.py`, `clauses.py` (extract and review the agreements), `job_tasks.py` (the job's Python tasks: parity, summary, agents); `databricks.yml` at the root is the nightly job as a bundle (every `0*.sql` file is a task, in order; a test checks that)
- `harness/` agent, tools, verifier, summary, tracing, `foundry/` hosting; `agents.py` the Delegate runtime (facts, prose, check, approval; runs in `ops.agent_runs`) and the four agents `precall.py`, `watch.py`, `prospect.py`, `mismatch.py`; `research.py` the public-source providers
- `evals/` benchmark questions with ground truth, runner, tests
- `server/` FastAPI: the viewer's identity per request, the /api routes, the SSE stream for questions, `router.py` (meta, general, data), `agents_api.py` (the Delegate routes), the SPA fallback
- `web/` the React app (Vite, TypeScript, Tailwind v4, Radix, Motion); `web/dist` is the build the App serves; `app/cache/` the offline answers
- `docs/` architecture, walkthrough, failure modes, limits; `docs/superpowers/specs/` the design spec (the canvas link is in it)

## Commands

```
.venv/bin/python data/make_data.py && .venv/bin/python lakehouse/run.py     # rebuild locally (stop the app first)
.venv/bin/pytest evals -q                                                 # checks
.venv/bin/python evals/run_benchmark.py --check                           # ground-truth SQL runs
.venv/bin/uvicorn server.main:app --reload --port 8000                    # the API; then: cd web && npm run dev (proxies /api)
cd web && npm run build && cd .. && .venv/bin/python lakehouse/app_deploy.py deploy   # the Databricks App (deploy refuses without web/dist)
cd web && npm test && npx playwright test                                 # the front-end checks (dev server on 5173 for Playwright)
FAIRSHARE_BACKEND=databricks .venv/bin/python lakehouse/run.py            # build on Databricks (needs .env)
databricks bundle deploy && databricks bundle run fairshare_nightly        # the job (CLI default profile); --params summary_weekday=<today> forces the drafts
FAIRSHARE_BACKEND=duckdb .venv/bin/python lakehouse/job_tasks.py agents none   # every agent's run for the latest month, offline (the app lists them under Delegate)
FAIRSHARE_MODEL=azure .venv/bin/python lakehouse/clauses.py extract        # re-read the agreements into data/out/contract_clauses.csv; `review` re-checks a committed file
```

The laptop's `.env` points at Databricks and Foundry: local builds and tests take `FAIRSHARE_BACKEND=duckdb` on the command line.
