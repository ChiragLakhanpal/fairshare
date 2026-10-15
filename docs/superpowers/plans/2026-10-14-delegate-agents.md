# Delegate agents implementation plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add the Delegate mode to fairshare: four Sales Ops agents (Monday pre-call pack, Agreement watch, Prospect research, CRM versus reality) on one runtime with approvals, plus the chat router fix.

**Architecture:** Every agent is fixed portable SQL blocks (facts) + a tool-less writer (prose, frontier model when configured) + the verifier + a human approval with a side effect. Runs are persisted in `ops.agent_runs` through the existing state-table path; the nightly job writes runs the same way. The React app gets a second mode that lists agents, runs and items.

**Tech Stack:** Python 3 (FastAPI, Agent Framework 1.21, pandas, DuckDB locally, Databricks SQL / Spark in the lakehouse), React 19 + Vite + TypeScript + Tailwind v4 + Radix + Motion, pytest, vitest, Playwright.

**Spec:** `docs/superpowers/specs/2026-10-14-delegate-agents-design.md`

**Execution note (October 14, night):** Chirag asked for all showcases built while he sleeps and said "commit as you go". The author of this plan executes it natively in the same session, committing locally at each green task; a fork may take the web task against the API in the spec. This plan therefore shows code where a decision lives and names the rest.

## Global Constraints

- CLAUDE.md rules 1 to 9: numbers only from tools and the verifier on every model sentence; definitions untouched; new tables only in `gold` and `ops`; no DROP/TRUNCATE/blanket DELETE (`CREATE OR REPLACE`, `DELETE ... WHERE`); portable SQL (three-part names, `NULLIF`, `EXTRACT`, `CAST(x AS STRING)`, `QUALIFY`, `GROUP BY ALL`, no alias that differs only by case); the gate (`evals/run_benchmark.py --check` and `pytest evals`) before every commit; secrets only in `.env`; copy as full 12th-grade sentences, no em dashes; dummy data stays dummy.
- Every new SQL file `lakehouse/0*.sql` must be a task in `databricks.yml` in run order (`test_bundle_runs_every_sql_file_in_the_lakehouse`).
- Local commands use `FAIRSHARE_BACKEND=duckdb` explicitly: `.env` points the laptop at Databricks and Foundry.
- Existing numbers must not change: `data/make_data.py` keeps its random stream (new tables use their own `random.Random`).
- The app runs offline (`FAIRSHARE_MODEL=none`): every agent has a template writer.
- No deploys, secret scopes, workspace uploads or job submits from this session (blocked); the morning note carries them.

## Review Focus

1. An agency with no agreement (eight of twelve) must get a pack page that says "no agreement on file" rather than an empty clause section or a crash: Task 4 test `test_pack_agency_without_agreement`.
2. A month with no prior year (2025-xx) has no decomposition row; the pack must degrade to "no comparison" for that block: Task 4 test `test_pack_month_without_prior_year`.
3. Approving the same item twice must write one CRM activity, not two: Task 3 test `test_approve_is_idempotent`.
4. A run whose block raises (a bad SQL on one agency) must end `failed` with the error text and keep the items already finished: Task 3 test `test_run_records_a_failed_block`.
5. A clause whose threshold the model extracted wrongly must be caught by the review step: Task 2 pins every clause row against the agreement text with `test_clause_quotes_are_verbatim` (each `quote` must appear in its file on its page).

---

### Task 1: CRM stand-in data and the state-table path

**Files:**
- Modify: `data/make_data.py` (append `build_crm()` and three `write` calls at the end of `main()`)
- Modify: `lakehouse/run.py` (BRONZE_TABLES), `lakehouse/00_bronze.sql`, `lakehouse/01_silver.sql`, `lakehouse/02_gold.sql`
- Modify: `fairshare/db.py` (`state_execute`, `state_query` map every `aa_demo.ops.<name>` onto the state file; `CRM_ACTIVITIES = "aa_demo.ops.crm_activities"`)
- Test: `evals/test_lakehouse.py`

**Interfaces:**
- Produces: `aa_demo.gold.crm_contacts(contact_id INT, agency_id INT, contact_name, title, email)`, `aa_demo.gold.crm_opportunities(opp_id INT, agency_id INT, opp_name, stage, amount_usd DOUBLE, close_date DATE, health, owner, updated_at DATE)`, `aa_demo.gold.crm_activities(activity_id INT, agency_id INT, contact_id INT, activity_type, subject, happened_at DATE, owner, notes)`; `db.state_execute([...])` and `db.state_query(sql)` accept any `aa_demo.ops.*` name.

- [ ] **Step 1: Failing tests** in `evals/test_lakehouse.py`:

```python
def test_crm_stand_in_tables_load():
    c = db.query("SELECT COUNT(*) n, COUNT(DISTINCT agency_id) a FROM aa_demo.gold.crm_contacts").iloc[0]
    assert c["a"] == 12 and c["n"] >= 12
    o = db.query("SELECT agency_id, opp_name, stage, health FROM aa_demo.gold.crm_opportunities WHERE agency_id = 5 AND opp_name LIKE '%renewal%'").iloc[0]
    assert o["stage"] == "Negotiate" and o["health"] == "On track"  # the planted CRM-versus-reality trap
    last = db.query("SELECT agency_id, MAX(happened_at) AS last_touch FROM aa_demo.gold.crm_activities GROUP BY ALL")
    assert len(last) == 12 and str(last["last_touch"].min()) >= "2026-07-01"

def test_state_tables_map_every_ops_name(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "STATE_FILE", tmp_path / "s.duckdb")
    db.state_execute(["CREATE TABLE IF NOT EXISTS aa_demo.ops.crm_activities (activity_id STRING, agency_id INT)", "INSERT INTO aa_demo.ops.crm_activities VALUES ('a', 5)"])
    assert db.state_query("SELECT COUNT(*) AS n FROM aa_demo.ops.crm_activities")["n"].iloc[0] == 1
```

- [ ] **Step 2: Run** `FAIRSHARE_BACKEND=duckdb .venv/bin/python -m pytest evals/test_lakehouse.py -q -k "crm or state"` and watch both fail (missing table, wrong replace).
- [ ] **Step 3: Generator.** In `data/make_data.py` after the existing builders:

```python
def build_crm():
    """Dynamics-shaped stand-in: contacts, opportunities, activities. Its own generator so the sales stream above stays identical."""
    rng = random.Random(88202)
    first = ["Avery", "Jordan", "Morgan", "Riley", "Casey", "Quinn", "Taylor", "Drew", "Reese", "Harper", "Rowan", "Sage"]
    last = ["Patel", "Nguyen", "Garcia", "Okoro", "Kim", "Silva", "Brennan", "Haddad", "Larsen", "Mehta", "Flores", "Walsh"]
    titles = ["Director of Air", "VP Supplier Relations", "Air Sourcing Manager", "Head of Corporate Travel", "Operations Lead"]
    contacts, opps, acts = [], [], []
    cid, oid, aid_ = 9000, 7000, 30000
    today = date(2026, 10, 1)
    for aid, name, atype, region, am in agencies:
        domain = name.lower().replace(" ", "") + ".example"
        n = rng.choice([1, 2, 2, 3])
        people = []
        for _ in range(n):
            cid += 1
            fn, ln = rng.choice(first), rng.choice(last)
            contacts.append((cid, aid, f"{fn} {ln}", rng.choice(titles), f"{fn.lower()}.{ln.lower()}@{domain}"))
            people.append(cid)
        # one renewal per agency, plus a second opportunity for the larger ones
        health = {5: "On track", 3: "At risk", 1: "On track"}.get(aid, rng.choice(["On track", "On track", "At risk", "Stalled"]))
        stage = {5: "Negotiate", 3: "Propose", 1: "Negotiate"}.get(aid, rng.choice(["Qualify", "Propose", "Negotiate"]))
        base = agency_profile[aid][0]
        oid += 1
        opps.append((oid, aid, f"{name} 2027 renewal", stage, round(base * 12 * 0.45 * 1.5, -3), date(2026, 12, 15).isoformat(), health, am, (today - timedelta(days=rng.randint(3, 40))).isoformat()))
        if base >= 700000:
            oid += 1
            opps.append((oid, aid, f"{name} NDC adoption", rng.choice(["Qualify", "Propose"]), round(base * 1.2, -3), date(2027, 3, 31).isoformat(), rng.choice(["On track", "Stalled"]), am, (today - timedelta(days=rng.randint(10, 90))).isoformat()))
        kinds = [("Call", "Monthly check-in"), ("Email", "Performance report sent"), ("Meeting", "Quarterly business review"), ("Email", "Follow-up on fare display")]
        d = date(2026, 1, 10)
        while d < today - timedelta(days=rng.randint(5, 60)):
            aid_ += 1
            k, s = rng.choice(kinds)
            acts.append((aid_, aid, rng.choice(people), k, s, d.isoformat(), am, ""))
            d += timedelta(days=rng.randint(12, 35))
    return contacts, opps, acts
```

and in `main()` after the existing writes: build and write `crm_contacts.csv`, `crm_opportunities.csv`, `crm_activities.csv` with the headers above. Run `.venv/bin/python data/make_data.py` and confirm with `git diff --stat data/out` that only the three new CSVs appear (the others are byte-identical).

- [ ] **Step 4: Lakehouse.** `run.py` BRONZE_TABLES += the three; `00_bronze.sql` three `read_files` loads (dates stay strings in bronze); `01_silver.sql` three typed `CREATE OR REPLACE TABLE aa_demo.silver.crm_*`; `02_gold.sql` three copies. `db.py`: `_STATE_NAMES = re.compile(r"aa_demo\.ops\.(\w+)")` and `.replace(SUMMARIES, "summaries")` becomes `_STATE_NAMES.sub(r"\1", s)` in both functions. Rebuild: `FAIRSHARE_BACKEND=duckdb .venv/bin/python lakehouse/run.py` (stop any local uvicorn first).
- [ ] **Step 5: Run** the whole suite: `FAIRSHARE_BACKEND=duckdb .venv/bin/python -m pytest evals -q`. Expected: all green, 71 tests.
- [ ] **Step 6: Commit** `data: a CRM stand-in (contacts, opportunities, activities) shaped like Dynamics; the state file maps every ops table`.

### Task 2: Agreement clauses and the watch table

**Files:**
- Create: `lakehouse/clauses.py`, `lakehouse/07_agreement_watch.sql`, `data/out/contract_clauses.csv`
- Modify: `lakehouse/run.py` (BRONZE_TABLES += `contract_clauses`; PORTABLE += `07_agreement_watch.sql`), `00_bronze.sql`, `01_silver.sql`, `02_gold.sql`, `databricks.yml` (task `agreement_watch` after `gold`, before `parity`? No: after `decomposition`, both read gold only), `evals/test_lakehouse.py`
- Test: `evals/test_lakehouse.py`

**Interfaces:**
- Produces: `aa_demo.gold.contract_clauses(clause_id, agency_id INT, file, page INT, section, clause_type, metric, operator, threshold DOUBLE, threshold_2 DOUBLE, window_quarters INT, consequence, quote)` and `aa_demo.ops.agreement_checks(clause_id, agency_id, agency_name, as_of DATE, clause_type, metric, value DOUBLE, threshold DOUBLE, distance DOUBLE, unit STRING, quarters_below INT, dollars DOUBLE, dollars_label STRING, status STRING, consequence, file, page, quote)`.

- [ ] **Step 1: Failing tests:**

```python
def test_clause_quotes_are_verbatim():
    rows = db.query("SELECT file, page, quote FROM aa_demo.gold.contract_clauses")
    from harness.tools import _pages
    for r in rows.itertuples():
        pages = dict(_pages(ROOT / "data" / "contracts" / r.file))
        assert r.quote.split("\n")[0].strip()[:60] in pages[int(r.page)], (r.file, r.page, r.quote[:60])

def test_agreement_checks_cover_every_clause_and_month():
    n = db.query("SELECT COUNT(DISTINCT clause_id) c, COUNT(DISTINCT as_of) m, COUNT(*) n FROM aa_demo.ops.agreement_checks").iloc[0]
    assert n["m"] == 9 and n["n"] == n["c"] * n["m"]  # Jan to Sep 2026

def test_harbor_commitment_and_summit_share_clauses():
    h = db.query("SELECT status, value, threshold, dollars FROM aa_demo.ops.agreement_checks WHERE agency_id = 5 AND clause_type = 'annual_commitment' AND as_of = DATE '2026-09-01' ORDER BY threshold DESC").iloc[0]
    assert h["status"] in ("watch", "breached") and h["dollars"] > 0
    s = db.query("SELECT status, quarters_below FROM aa_demo.ops.agreement_checks WHERE agency_id = 1 AND clause_type = 'share_floor_quarters' AND as_of = DATE '2026-09-01'").iloc[0]
    assert s["status"] == "ok" and s["quarters_below"] == 0
```

- [ ] **Step 2: Run, watch fail.**
- [ ] **Step 3: Extraction.** `lakehouse/clauses.py`: `extract()` builds one prompt per agreement (the page-tagged text, the schema below, the clause types with one example each) and asks the thinking model (`make_client(os.environ.get("FAIRSHARE_THINKER") or model_backend())`) for JSON rows; `review()` asserts each quote is verbatim on its page and each `clause_type` is known; writes the CSV. The extraction prompt must say: thresholds as plain numbers (45 for 45%, 4290000 for $4,290,000), `metric` in {aa_share, aa_revenue, share_premium_pts, share_gap_pts, revenue_yoy_ratio, aa_seats_yoy_pct, none}, one row per threshold (Harbor 2.3 gives two rows: repay at 90, forfeit at 75), `window_quarters` for consecutive-quarter rules, `consequence` in the agreement's words. Run it once: `FAIRSHARE_MODEL=azure FAIRSHARE_TRACES= .venv/bin/python lakehouse/clauses.py extract`. Read the CSV by eye against the four files; fix by hand if a row is wrong (the review test pins quotes, not thresholds). Expected rows (the plan's own reading of the agreements, for the review): Summit: tiers (4 rows, `share_premium_tiers`, thresholds 5/10/15 with incentive 1.0/2.0/3.0 in threshold_2), share floor 45 for 2 quarters, capacity exclusion 15, goal 5184000 and share goal 48 (`annual_commitment` is Harbor's word; Summit's goals are `goal`, checked as pace), notice rules `not_checkable`. BlueSky: share tiers 43 -> 1.5, 47 -> 2.5; floor 40 for 2 quarters; revenue decline 50 for 2 quarters; termination `not_checkable`. FareHub: gap tiers (>= 0 -> 0.5, >= -10 -> 0.25); data due dates and service levels `not_checkable`. Harbor: commitment 4290000 with repay 90 and forfeit 75; front-end 1.5; preferred carrier notice `not_checkable`.
- [ ] **Step 4: The watch SQL** (`07_agreement_watch.sql`, portable). Build month-level and quarter-level agency measures once, then one `SELECT` per clause type unioned:

```sql
CREATE OR REPLACE TABLE aa_demo.ops.agreement_checks AS
WITH months AS (SELECT DISTINCT sales_month AS as_of FROM aa_demo.gold.fact_agency_sales_monthly WHERE sales_month >= DATE '2026-01-01'),
ytd AS (  -- per agency and as-of month: year-to-date revenue, share, fair share, premium, gap
  SELECT m.as_of, s.agency_id,
         SUM(s.aa_revenue) AS ytd_revenue, SUM(s.market_revenue) AS ytd_market, SUM(s.market_revenue * c.aa_seat_share) AS ytd_fair,
         CAST(EXTRACT(MONTH FROM m.as_of) AS INT) AS months_elapsed
  FROM months m JOIN aa_demo.gold.fact_agency_sales_monthly s ON s.sales_month BETWEEN DATE '2026-01-01' AND m.as_of
  JOIN aa_demo.gold.fact_market_capacity c ON c.market_id = s.market_id AND c.sales_month = s.sales_month
  GROUP BY ALL),
q AS (  -- closed calendar quarters per agency with share and revenue, and the prior-year quarter
  SELECT agency_id, CAST(EXTRACT(YEAR FROM sales_month) AS INT) AS yr, CAST(EXTRACT(QUARTER FROM sales_month) AS INT) AS qtr,
         SUM(aa_revenue) / NULLIF(SUM(market_revenue), 0) * 100 AS share_pct, SUM(aa_revenue) AS revenue,
         MAX(sales_month) AS quarter_end
  FROM aa_demo.gold.fact_agency_sales_monthly GROUP BY ALL),
-- consecutive closed quarters below the floor as of each month: count back from the last closed quarter
...
```

The plan's rule for `status`: `breached` when the rule's condition holds (quarters_below >= window; projected attainment below the threshold); `watch` when within 2 points, within one quarter of the window, or projected attainment within 5 points of the threshold; `ok` otherwise; `not_checkable` rows carry NULL value. `dollars`: for tiers, `ytd_revenue * incentive_pct / 100` at the current tier and `dollars_label = 'incentive at the current tier'`; for the next tier, a second row per tier clause is not needed: the agent reads `distance` to the next tier from the ordered tier rows. For `annual_commitment`: `dollars = ytd_revenue * 1.5 / 100` (the advanced incentive at risk) with `dollars_label = 'advanced incentive at risk'`; `value` = projected attainment `ytd_revenue * 12.0 / months_elapsed / threshold_amount * 100` (a column, so the writer never computes). Quarter logic uses only closed quarters (`quarter_end < as_of` or as_of is the quarter's last month).

- [ ] **Step 5: Bronze to gold for `contract_clauses`** (CSV in `data/out`, typed in silver with `CAST(threshold AS DOUBLE)`, copied to gold). `run.py` PORTABLE gets `07_agreement_watch.sql` after `06_decomposition.sql`. Rebuild, run the three tests, then the suite.
- [ ] **Step 6: Bundle.** `databricks.yml` task `agreement_watch` (`sql_task`, file `lakehouse/07_agreement_watch.sql`, depends on `gold`); the bundle test's `on_disk` list now includes it in order (the test compares sorted file names to task order, so place the task after `decomposition`).
- [ ] **Step 7: Commit** `lakehouse: contract clauses extracted once with page citations; ops.agreement_checks every clause, every month`.

### Task 3: The agent runtime

**Files:**
- Create: `harness/agents.py`
- Modify: `harness/agent.py` (`make_client(backend: str | None = None)`), `harness/summary.py` (`make_writer` passes `FAIRSHARE_THINKER`), `fairshare/db.py` (`AGENT_RUNS = "aa_demo.ops.agent_runs"`)
- Test: `evals/test_agents.py`

**Interfaces (produces):**

```python
@dataclass
class Fact:      name: str; label: str; df: pd.DataFrame; sql: str; source: str
@dataclass
class Item:      item_id: str; kind: str; title: str; subtitle: str; severity: str | None; status: str = "draft"
                 facts: list[Fact]; sources: list[dict]; draft: str = ""; verified_text: str = ""; flagged: list = ...; badges: list = ...
                 action: dict = {"type": "none"}; decided_at: str | None = None; decided_by: str | None = None
@dataclass
class Run:       run_id: str; agent: str; scope: dict; requested_by: str; model: str; created_at: str; finished_at: str | None
                 items: list[Item]; progress: dict = {"done": 0, "total": 0, "text": ""}; error: str | None = None
                 status (property): running | needs_approval | approved | rejected | failed
@dataclass
class AgentDef:  key: str; name: str; summary: str; reads: list[str]; writes: list[str]; approver: str; scope_kind: str
                 plan: Callable[[dict], list[dict]]            # scope -> item seeds [{title, subtitle, kind, key...}]
                 facts: Callable[[dict, dict], list[Fact]]     # (scope, seed) -> facts (runs SQL, records calls)
                 instructions: str                             # the writer's system prompt
                 template: Callable[[dict, list[Fact]], str]   # (seed, facts) -> prose with no model
                 action: Callable[[dict, list[Fact], str], dict]  # (seed, facts, verified_text) -> action dict
                 severity: Callable[[dict, list[Fact]], str | None]
AGENTS: dict[str, AgentDef]                                    # filled by precall, watch, prospect, mismatch at import
async def run_async(agent_key, scope, requested_by, writer=None, on_progress=None) -> Run
def run(agent_key, scope, requested_by, writer=None) -> Run        # sync wrapper (job, tests)
def save(run: Run) -> None; def load(run_id) -> Run | None; def list_runs(limit=20) -> list[dict]
def approve(run: Run, item_id: str, text: str | None, by: str) -> Item   # re-verify, side effect, save
def reject(run: Run, item_id: str, by: str) -> Item
def verify_item(item: Item, draft: str) -> None                     # pool from facts (+ source numbers), sets draft/verified/badges/flagged
def crm_write(agency_id: int, activity_type: str, subject: str, notes: str, by: str, run_id: str, item_id: str) -> str
def make_writer(instructions: str)                                   # tool-less Agent on the thinker backend, or None
```

Prose per item: `facts_text(item)` renders each fact as `label:\n<table>` (dates as strings, `_clean` from summary), then `FACTS ... (quote numbers exactly as shown)`. Source numbers: for each `sources[i].snippet`, `extract_numbers` -> `pool.add(value, unit, f"web: {url}")` plus the pct twin, like the question numbers in `verify()`.

- [ ] **Step 1: Failing tests** (`evals/test_agents.py`) with a fake agent registered in the test: two seeds, a facts function returning one DataFrame, a template that writes one supported and one unsupported number; assertions: `run()` returns `needs_approval` with two items, the unsupported sentence is in `flagged`, `save`/`load` round-trip through `tmp_path` state file, `approve` with a bad edit raises `Unverified`, approve twice writes one `ops.crm_activities` row (`test_approve_is_idempotent`), a facts function that raises on the second seed ends `failed` with one finished item (`test_run_records_a_failed_block`), `list_runs` newest first, `status` derivation.
- [ ] **Step 2: Run, fail. Step 3: Implement. Step 4: Pass + suite. Step 5: Commit** `harness: the agent runtime (facts, prose, check, approval), runs in ops.agent_runs, the thinker backend`.

### Task 4: Monday pre-call pack (with the CRM versus reality line)

**Files:** Create `harness/precall.py`; Test `evals/test_agents.py`.

Blocks per agency (all portable SQL, month `mo`, prior `prior`): `numbers` (revenue, yoy, share, fair, gap pts, gap usd, pace from the agencies block pattern in `summary.agencies_block` filtered to the agency), `why` (the `ops.decomposition` row plus top three markets by share effect, as `explain_change` does, or an empty frame with a note when no prior year), `clauses` (`ops.agreement_checks` rows for the agency and month, or "no agreement on file"), `crm` (open opportunities; last touch = `MAX(happened_at)` across `gold.crm_activities` and `ops.crm_activities`), `schedule` (AA seats and seat share by market for the agency's top five markets, this month versus last year), `mismatch` (opportunity health versus the data: `health = 'On track' AND share_chg_pts <= -3` or `health = 'At risk' AND share_chg_pts >= 3`).

Instructions (writer): "You write a one-page pre-call pack for the account manager from the FACTS only. Four short paragraphs: where they stand (revenue, year over year, share against fair share, pace), what moved and why (volume, mix, share; name the markets), what the agreement says is at stake (or that there is no agreement on file), what to do on the call (three talking points, each tied to a number). Then a blank line and an email of five sentences to the agency contact named in the facts, subject line first. Every number exactly as in the facts; no number not in the facts; plain punctuation; no em dashes; no bullet lists. End with one line starting 'Could not verify:' naming what the facts do not cover." Action: `{type: "email", subject, body (the email part), crm: {agency_id, activity_type: "Pre-call pack", subject: "Pre-call pack approved for <month>"}}`.

Tests: `test_pack_marcus_lee_offline` (4 items, every sentence verified with the template, Harbor severity `risk`, Harbor's facts include a mismatch row and a clause row), `test_pack_agency_without_agreement` (Northstar: the clauses fact has a note, the template says "no agreement on file"), `test_pack_month_without_prior_year` (2025-09: `why` fact empty, template says "no comparison").

- [ ] Steps: failing tests, run, implement, pass, suite, commit `harness: the Monday pre-call pack`.

### Task 5: Agreement watch

**Files:** Create `harness/watch.py`; Test `evals/test_agents.py`.

Seeds: one item per `agreement_checks` row for the month with status in (`breached`, `watch`) plus one per tier clause within 2 points of the next tier (the upsell), ordered breached first, then by dollars. Facts: the check row, the agency's monthly share for the last six months, and for tiers the ordered tier table. Instructions: "Write the alert for the Sales Ops lead in three sentences from the FACTS: what the clause says (quote the threshold), where the agency is (the value and the distance), what is at stake in dollars. Then, after a blank line, the draft notice to the agency (a breach) or the draft upsell note (one tier from a higher incentive), five sentences, subject line first. Numbers exactly as in the facts..." Action: email with subject "Agreement watch: <agency>, <clause>". Severity: `risk` for breached, `watch` otherwise. Template: deterministic from the row.

Tests: `test_watch_september` (Harbor's commitment appears first with severity `risk` or `watch`; a Summit tier item exists with `distance` in its facts; every template sentence verified).

- [ ] Steps as above; commit `harness: agreement watch`.

### Task 6: Prospect research with cached public sources

**Files:** Create `harness/research.py`, `harness/prospect.py`, `data/research/CLT-LGA.json` (+ DFW-DCA, MIA-JFK, DFW-LAX); Modify `lakehouse/app_deploy.py` INCLUDE (`data/research`); Test `evals/test_agents.py`.

`research.py`: `sources(market: str) -> list[dict]`; provider from `FAIRSHARE_SEARCH` (`cached` default, `brave`); `fetch(market)` uses the provider and writes the cache file `{market, fetched_at, query, sources: [{title, url, published, snippet}]}`; CLI `python -m harness.research fetch CLT-LGA`. The brave provider: `GET https://api.search.brave.com/res/v1/web/search?q=...&count=8` with header `X-Subscription-Token: SEARCH_API_KEY`, mapping `web.results[].{title,url,age,description}`. The cache for the four markets is written tonight from public route and airport pages found by hand (title, url, published, a quoted snippet), never a company's private figures.

`prospect.py`: seeds = one item for the market in scope; facts: `headroom` (per agency on the market in 2026: AA revenue, share, fair share, gap usd, ordered by gap), `trend` (the market's monthly share and fair share for twelve months), `capacity` (AA seats and share this month versus last year); sources from `research.sources(market)`. Instructions: "Write a prospecting brief for the market from the FACTS and the SOURCES: where the headroom is (the agencies below fair share and the dollars), what the sources say about the route (quote them, cite them by number [1], [2]), and a suggested play in two sentences. Numbers from the facts or quoted verbatim from a source only." Action: `{type: "none"}` (a brief to read) with `crm: null`. Template: headroom sentences plus "Source [n]: <title>" lines.

Tests: `test_prospect_clt_lga_offline` (the item has 3 facts and at least 2 sources; a number quoted from a source verifies with source `web: <url>`).

- [ ] Steps as above; commit `harness: prospect research with cited public sources`.

### Task 7: CRM versus reality

**Files:** Create `harness/mismatch.py` (reuses the pack's mismatch SQL from `precall.mismatch_block`); Test `evals/test_agents.py`.

Seeds: one item per mismatching open opportunity for the month (region or All). Facts: the opportunity row, the agency's share change and revenue change (from `ops.decomposition`), the last touch. Instructions: three sentences (what the CRM says, what the data says, what to change) then the CRM note in two sentences. Action: `{type: "crm", crm: {agency_id, activity_type: "CRM update", subject: "Health changed after review"}, subject, body}`. Severity `risk`.

Tests: `test_mismatch_finds_harbor_renewal` (All, 2026-09: Harbor's renewal is an item; approving it writes one `ops.crm_activities` row with `source = app`).

- [ ] Steps as above; commit `harness: CRM versus reality`.

### Task 8: API routes

**Files:** Modify `server/api.py` (or create `server/agents_api.py` included by `api.router`); Test `evals/test_api.py`.

Routes exactly as the spec's API section. The background run: `asyncio.create_task(agents.run_async(...))` with the viewer's context (contextvars copy on create_task); `?wait=true` awaits the task before answering (tests, scripts). In-memory `RUNS: dict[str, Run]` (cap 50) fronts the table; `GET /agents/runs/{id}` reads memory first, then `agents.load`. `requested_by` is the viewer's email or "laptop". Status derivation and item approval through `agents.approve/reject`.

Tests: `test_agents_catalog` (four agents, managers has four names, markets has twelve), `test_run_pack_wait_and_poll` (POST with wait returns `needs_approval` with 4 items; GET returns the same; `GET /agents/runs` lists it first with `needs_approval = 4`), `test_approve_and_reject_items` (approve one item -> `approved`, `decided_by` the viewer email from the forwarded header; a bad edit 422 `unverified`; reject one -> `rejected`; run status stays `needs_approval` while a draft remains), `test_crm_activities_merge_both_tables`, `test_run_unknown_agent_is_404`, `test_run_bad_scope_is_422`.

- [ ] Steps as above; commit `server: the agents routes`.

### Task 9: The chat router

**Files:** Create `server/router.py`; Modify `server/stream.py` (`AskIn.last_answer: LastAnswer | None`; the classification before the agent), `web/src/lib/api.ts` and `App.tsx` (send `last_answer` from the previous assistant turn: `{calls: [{tool, sql, rows, note}], removed, verified_numbers, sources}`), `server/cached.py` FOLLOW_UPS (`meta`, `general`); Test `evals/test_router.py`, `evals/test_stream.py`.

```python
META = re.compile(r"\b(what|which)\b.*\b(checks?|queries|query|tools?|tables?|sources?)\b.*\b(you|did|ran|performed|used)\b|\bhow (did|was) (you|that|this) (get|check|verify|verified|checked)|\bwhat did you remove|\bwhat was removed|\bshow (me )?(the )?(sql|query) (you|that) (ran|used)", re.I)
DOMAIN = ("revenue", "share", "fair", "gap", "pace", "goal", "agency", "agencies", "market", "route", "agreement", "contract", "clause", "incentive", "tier", "region", "central", "east", "west", "quarter", "month", "year", "yoy", "booking", "corporate", "passenger", "seat", "capacity", "decline", "churn", "dollar", "$", "%") + agency and market names from gold + month names
CONCEPT = re.compile(r"^(what is|what are|what does .* (mean|stand for)|explain|define|who is|how do(es)? .* work)\b", re.I)
def classify(question: str, has_last: bool) -> str   # "meta" | "general" | "data"
def meta_answer(question, last: dict | None) -> dict  # an Answer payload, kind "meta", sentences as notes
```

`general`: `make_writer("Answer in three plain sentences... say when something is outside the airline sales data.")` with no tools; `answer_json` with kind `general`, trust line handled by the browser copy (`copy.trustGeneral = "This answer did not use your data."`). Tests: thirty questions in a table (ten meta, ten general, ten data, including "explain fair share" -> data, "what does TMC stand for" -> general, "What are the checks you performed?" -> meta, "Why is Harbor down?" -> data, "which query did you run" -> meta); the stream test posts a meta question with `last_answer` and gets `answer` with kind `meta` and no model.

- [ ] Steps as above; commit `server: a router for questions about the last answer and general questions`.

### Task 10: The nightly job runs the agents

**Files:** Modify `lakehouse/job_tasks.py` (`agents_task(model)`: pack for every manager, watch for the month, mismatch for All; saves each run; prints removed sentences), `databricks.yml` (task `agents` after `parity`, `decomposition`, `agreement_watch`), `evals/test_lakehouse.py` (the bundle test's parameter set becomes `{"parity", "summary", "agents"}`; `job_tasks.managers() == [...]`).

- [ ] Steps; commit `job: the agents run nightly and wait for approval`.

### Task 11: Delegate in the web app

**Files:** Create `web/src/components/Delegate.tsx`, `AgentCard.tsx`, `RunList.tsx`, `RunView.tsx`, `ItemView.tsx`, `web/src/lib/runs.ts` (+ `runs.test.ts`); Modify `web/src/lib/types.ts`, `api.ts`, `store.ts` (`mode: "ask" | "delegate"`, `runId: string | null`, remembered in localStorage), `copy.ts`, `Sidebar.tsx` (the Ask/Delegate switch under the wordmark; in Delegate the quick actions and Recent hide and the four agents are listed instead), `App.tsx` (render `Delegate` in place of the summary and conversation when mode is delegate; the floating bar hides), `web/e2e/delegate.spec.ts`.

Behavior: the catalog from `GET /api/agents`; each card has a scope control (`select` of managers, or region + month from the TopBar scope, or a market select) and "Run now"; a run starts with `POST` and the view polls `GET /api/agents/runs/{id}` every 2 s while `running` (progress line "3 of 4 pages written"); the run list from `GET /api/agents/runs`; `RunView` shows items with `ItemView`: title, subtitle, severity chip (`watch` grey, `risk` red), verified sentences with checks, removed box, "Show the numbers" (tables per fact, `Table` from Answer.tsx extracted to `components/Table.tsx`), "Show the query" (`pre.sql` per fact), sources list with links, then Approve / Edit / Reject; approve with an email action calls `emailDraft` after the server answers; a CRM action shows "Recorded in the CRM stand-in."; approved and rejected items show their decision line. `lib/runs.ts`: `statusLabel(status)`, `progressText(run)`, `needsApproval(run)`, `groupRuns(runs)` with vitest.

Tests: vitest for `lib/runs.ts`; Playwright `delegate.spec.ts` with mocked `/api/agents`, a mocked run that answers `running` twice then `needs_approval`, the approve click marking the item and the mail draft (`page.on("request")` or the `location.href` change intercepted by stubbing `emailDraft` through `window.__fairshareMailto`? Simpler: assert the item status text changes; the mailto is a `location.href` assignment that Playwright sees as a navigation attempt to `mailto:`; wrap in a `page.route("mailto:*")` is not possible, so assert the item's approved line and the request body). `tsc --noEmit && vite build` clean.

- [ ] Steps; commit `web: Delegate, the agents, their runs and approvals`.

### Task 12: Docs, deploy manifest, and the morning note

**Files:** Modify `docs/walkthrough.md` (a sixth beat: Delegate, two minutes, after Ask; the pre-call pack for Marcus Lee with Harbor's page, the watch alert, the mismatch), `README.md` (the shape: agents in the harness, the CRM stand-in, the nightly runs), `CLAUDE.md` layout lines, `docs/limits.md` (anything met), `lakehouse/app_deploy.py` (INCLUDE `data/research`), `.env.example` (`FAIRSHARE_THINKER`, `FAIRSHARE_SEARCH`, `SEARCH_API_KEY`).

- [ ] Steps; commit `docs: Delegate in the walkthrough, the README and the deploy manifest`.

## Self-review

Spec coverage: data (Tasks 1, 2, 6), runtime and the thinker split (3), the four agents (4 to 7), API (8), router (9), job (10), web (11), docs and deployment note (12). Placeholders: the watch SQL shows its shape and rules, not every union; the author fills it with the clause types from Task 2. Types: `Item`, `Run`, `Fact`, `AgentDef` names are used consistently in Tasks 3 to 8 and mirrored in the spec's API. Review Focus items map to tests in Tasks 2, 3 and 4.
