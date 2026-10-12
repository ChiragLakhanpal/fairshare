# Day 0: what only you can do (about ninety minutes)

Everything else in the repo already runs offline. These four things need your identity.

1. **Databricks Free Edition** (no card): sign up at databricks.com/learn/free-edition with a personal email. In the workspace:
   user settings, developer, access tokens: create a PAT. SQL warehouses: open the starter warehouse, copy the server hostname and
   HTTP path from Connection details. Put all three in `.env` (`DATABRICKS_HOST`, `DATABRICKS_SERVER_HOSTNAME`, `DATABRICKS_HTTP_PATH`,
   `DATABRICKS_TOKEN`). Verify your identity with LinkedIn if the workspace offers it (raises some limits).
   Then: `FAIRSHARE_BACKEND=databricks .venv/bin/python lakehouse/run.py` after uploading `data/out/*.csv` to the landing volume
   (`00_bronze.sql` creates the catalog and volume on the first statements; upload through Catalog Explorer, then rerun).
   Smoke test: run the commented query at the bottom of `lakehouse/03_metric_view.sql` in the SQL editor.

2. **Genie Agent**: in the workspace, Genie, new agent over `aa_demo.gold.sales_metrics`, `aa_demo.gold.dim_agency`,
   `aa_demo.gold.dim_market`, `aa_demo.gold.agency_pace`. Copy the space id from the URL into `GENIE_SPACE_ID`.
   Smoke test from the laptop: `.venv/bin/python -c "from harness.tools import _genie_ask; print(_genie_ask('total AA revenue by region in 2026')[0:2])"`.
   Then the benchmark: `.venv/bin/python evals/run_benchmark.py --genie --label "first run"`. Record the pass rate as it is.

3. **Azure free account** ($200 for 30 days; a card for identity, nothing charged): portal.azure.com, then Foundry (ai.azure.com):
   new project, deploy `gpt-4.1-mini`. Open the quota page and read the TPM for it. If it is above zero: endpoint, key and deployment
   name into `.env`, `FAIRSHARE_MODEL=azure`. If it is zero: `FAIRSHARE_MODEL=databricks` with a Free Edition serving endpoint
   (Serving, pay-per-token endpoints; copy the endpoint name into `DATABRICKS_MODEL`). Smoke test:
   `.venv/bin/python -m harness.agent "Which agencies are behind pace in September 2026?"`

4. **T-100** (free, no account): the form at https://www.transtats.bts.gov/DL_SelectFields.aspx?gnoyr_VQ=GEE&QO_fu146_anzr=Nv4+Pn44vr45 ,
   tick UNIQUE_CARRIER, ORIGIN, DEST, YEAR, MONTH, PASSENGERS, SEATS, CLASS, choose 2025, tick Prezipped File, download; repeat
   for 2026. Drop both zips into `data/t100/raw/`, then `.venv/bin/python data/t100.py && .venv/bin/python data/make_data.py`
   and rebuild (`lakehouse/run.py`, locally and on Databricks). Read the warnings: a market with zero AA seats gets swapped.

Write every quota or limit you meet into `docs/limits.md` with the date.
