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
8. Dummy data stays dummy. Agencies, corporates and contracts are fictional; only the BTS T-100 seat data is real. Do not add anything that looks like a real customer, price list, or airline-internal figure.

## Layout

- `data/` generator, T-100 filter, contracts; `data/out/` the CSVs (committed) and the local DuckDB file (ignored)
- `lakehouse/` SQL in run order, `run.py` (local or Databricks), `parity.py`
- `harness/` agent, tools, verifier, summary, tracing, `foundry/` hosting
- `evals/` benchmark questions with ground truth, runner, tests
- `app/` Streamlit pages; `docs/` architecture, walkthrough, failure modes, limits

## Commands

```
.venv/bin/python data/make_data.py && .venv/bin/python lakehouse/run.py     # rebuild locally (stop the app first)
.venv/bin/pytest evals -q                                                 # checks
.venv/bin/python evals/run_benchmark.py --check                           # ground-truth SQL runs
.venv/bin/streamlit run app/Home.py                                        # the app
FAIRSHARE_BACKEND=databricks .venv/bin/python lakehouse/run.py            # build on Databricks (needs .env)
```
