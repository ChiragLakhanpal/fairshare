# fairshare: Delegate, the agents behind the chat

## Context

The app answers questions ("Ask"). The discussion on October 14 settled what it lacks: work that runs on its own, produces
a document, and waits for a person to say yes. That is the harness story Austin described ("Genie agents, Copilot agents,
in a harness") and the part Matthew's team is hiring for. This spec adds a second mode, Delegate, with four agents built
for Sales Ops, the runtime they share, and the small fix to the chat router that stops "what checks did you perform?"
from re-running the last query.

Decisions taken with Chirag before he went to sleep (October 14, evening):

- The summary stays the first screen, greeting first ("Good morning, Chirag."). No insights-first home screen.
- No Dynamics sandbox: the CRM is a stand-in, synthetic tables shaped like Dynamics 365 Sales, labeled as such on screen.
- The Databricks App can reach Foundry (probed with a fake key: Foundry's own 401 came back). Nothing in this design
  needs a laptop. The frontier model is a config switch; the key goes in a Databricks secret scope, never a file.
- Live web search is a switch for later. Tonight the prospect research reads public sources fetched once and stored with
  their URLs, so every sentence still has a citation.
- Commit at each green milestone, local only.

Everything below respects CLAUDE.md: numbers come from tools, the verifier runs on every model-written sentence, new
tables live in `gold` and `ops` only, SQL is portable, nothing destructive, dummy data stays dummy, copy at a 12th-grade
level with no em dashes.

## What a person sees

The sidebar gets a two-way switch under the wordmark: **Ask** and **Delegate**. Ask is the app as it is today.

Delegate is one screen in the main column:

1. **The agents.** Four cards. Each says in one sentence what it does, what it reads, what it writes, and who approves.
   Each has a scope control (an account manager, a region and month, or a market) and a "Run now" button. The card shows
   the last run's time and status.
   - **Monday pre-call pack**: for every agency an account manager owns, one page: the month's numbers, why they moved,
     the agreement clauses at risk, the CRM's last touch and open opportunities, the schedule on their routes, talking
     points, and a drafted follow-up email. Approving a page records an activity in the CRM stand-in and opens the email.
   - **Agreement watch**: every measurable promise in the four agreements, checked against the metric view for the
     month: breached, at risk, or fine, with the distance to the line and the dollars attached. For each alert, a drafted
     notice (a breach) or a drafted upsell (an agency one tier from a higher incentive), for approval.
   - **Prospect research**: for a market, where the headroom is (which agencies sell AA below fair share there, in
     dollars), what public sources say about the route, and a suggested play. Sources are quoted with their links.
   - **CRM versus reality**: every open opportunity whose CRM health disagrees with the data (on track while share
     collapses, at risk while share grows), with a drafted CRM update for approval.
2. **Runs.** A list of runs, newest first, with status: running, needs approval, approved, rejected, failed. The nightly
   job writes runs too, so on Monday morning the list already has the packs and the watch waiting.
3. **One run.** Its items, one per agency, clause, market or opportunity. Each item is rendered like the Monday brief:
   the verified sentences with a check each, a red box for anything the checker removed, "Show the numbers" and "Show the
   query" for the facts behind it, then the action: Approve (with an edit box) or Reject. Approving an item with an email
   opens the mail draft; approving an item with a CRM write records the activity and says so.

Copy is in `web/src/copy.ts` with the rest. The CRM is always called "the CRM stand-in" in text that a viewer could
mistake for a live system.

## How an agent works

Every agent is the same four steps, so the runtime is one piece of code:

1. **Facts.** Fixed, portable SQL blocks, one per section, run as the viewer (the App) or the job (serverless). Every
   number the writer may use is a returned column. Rows are recorded in the run context like the brief's blocks, so the
   app can show the query.
2. **Prose.** A writer agent with no tools reads the FACTS block for one item and writes the section the agent owns
   (talking points and an email, an alert and a notice, a brief and a play, a CRM note). With no model configured, a
   template writes the same section from the same facts.
3. **Check.** The verifier runs on the prose. Unsupported sentences are removed and shown. For prospect research the
   numbers quoted from a public source are added to the fact pool with the source URL, so they verify with provenance.
4. **Approval.** The item waits. Approve re-verifies any edit (as the brief does), performs the side effect, and records
   it. Reject records it. Nothing is sent or written before a person acts.

The thinking model is separate from the loop model: `FAIRSHARE_THINKER` names the backend the writers use (azure for
gpt-5-mini); unset, they use `FAIRSHARE_MODEL`. The chat loop stays on the cheap model; ranking, clause reading and the
"so what" go to the frontier one. Inside the App the Foundry key arrives through a secret scope resource (see Deployment).

## Data

### CRM stand-in (synthetic, generated with the rest of the data)

`data/make_data.py` gains three tables, built after the existing ones with their own seeded generator so the existing
random stream and every existing number stay identical:

- `crm_contacts(contact_id, agency_id, contact_name, title, email)`: one to three fictional contacts per agency.
- `crm_opportunities(opp_id, agency_id, opp_name, stage, amount_usd, close_date, health, owner, updated_at)`: one or two
  per agency (a 2027 renewal, an NDC adoption, a group travel program); stages Qualify, Propose, Negotiate, Closed Won;
  health On track, At risk, Stalled.
- `crm_activities(activity_id, agency_id, contact_id, activity_type, subject, happened_at, owner, notes)`: a history of
  calls, emails and meetings through September 2026, so every agency has a last touch between five and sixty days old.

Planted on purpose, like the existing traps: Harbor's renewal says Negotiate and On track while its share collapsed
(the CRM versus reality story); FareHub's renewal says At risk and is; Summit's says On track and is.

They land as bronze from CSVs (`lakehouse/run.py` BRONZE_TABLES, `00_bronze.sql`), are typed in `01_silver.sql`, and
copied to gold in `02_gold.sql`. The app's own writes go to `aa_demo.ops.crm_activities` (a state table, like
`ops.summaries`); "last touch" reads both.

### Agreement clauses

`lakehouse/clauses.py extract` sends each agreement to the thinking model with a fixed schema and writes
`data/out/contract_clauses.csv`: `clause_id, agency_id, file, page, section, clause_type, metric, operator, threshold,
threshold_2, window_quarters, consequence, quote`. The file is reviewed and committed; the job never re-extracts. Clause
types the checker knows: `share_floor_quarters` (share below X% for N consecutive quarters), `annual_commitment`
(revenue at least $X in the year, with repay and forfeit lines), `share_premium_tiers` (incentive by share premium),
`share_tiers` (incentive by annual share), `gap_tiers` (incentive by share gap to fair share), `revenue_decline_quarters`
(quarterly revenue below X% of the prior year for N quarters), `capacity_exclusion` (a quarter with a seat cut over X% is
excluded), and `not_checkable` (notice periods, data due dates, service levels: shown as "not in the data").

`lakehouse/07_agreement_watch.sql` (portable) builds `aa_demo.ops.agreement_checks`: for every clause and every month of
2026, the metric's value for the clause's window, the threshold, the distance (points or dollars), consecutive quarters
below the line where that applies, the dollars attached (the incentive at the current tier, the incentive one tier up,
the repayment exposure), and a status: `ok`, `watch` (within two points or one quarter of the line), `breached`,
`not_checkable`. The agent reads the rows for its month and nothing else.

### Public sources for prospect research

`harness/research.py` has one function, `sources(market) -> list[{title, url, published, snippet}]`, with two
providers: `cached` reads `data/research/<market>.json`; `brave` calls the Brave Search API with `SEARCH_API_KEY`.
`python -m harness.research fetch <market>` writes the cache. Tonight the cache holds the four markets with the largest
negative share gap in 2026 (CLT-LGA, DFW-DCA, MIA-JFK, DFW-LAX), fetched from public route and airport news. The item
shows each source as a quoted snippet with a link. The rule from CLAUDE.md holds: the research is about a real route,
never a real company with fictional numbers attached.

### Runs

`aa_demo.ops.agent_runs(run_id, agent, scope_json, status, requested_by, model, created_at, finished_at, payload_json)`,
written through `db.state_execute` (DuckDB `app_state.duckdb` locally, the warehouse on Databricks). `payload_json`
holds the items (sentences, removed, facts with rows and SQL, action, status). A run in progress lives in memory and is
saved when it finishes; approving or rejecting an item saves again. `db.state_execute` and `db.state_query` learn to map
every `aa_demo.ops.*` name onto the local state file, not only `summaries`.

## Code

```
harness/agents.py      the runtime: AGENTS registry, Run and Item dataclasses, run_async(agent, scope, writer) that runs
                       the agent's items one by one (facts, prose, verify) and emits progress; save/load/list on
                       ops.agent_runs; approve(run, item, text) and reject(); the CRM write
harness/precall.py     the Monday pre-call pack: blocks (numbers, decomposition, clauses, crm, schedule, mismatch) per
                       agency; instructions; template writer; items for one manager's agencies
harness/watch.py       agreement watch: items from ops.agreement_checks for the month; instructions; template writer
harness/prospect.py    prospect research: headroom block per market, sources, instructions, template writer
harness/mismatch.py    CRM versus reality: the mismatch block for every open opportunity; instructions; template writer
harness/research.py    sources(market) with the cached and brave providers; the fetch command
lakehouse/clauses.py   extract: agreements to data/out/contract_clauses.csv with the thinking model, with page citations
lakehouse/07_agreement_watch.sql   ops.agreement_checks (portable)
server/api.py          /api/agents routes (below); the router in server/stream.py
web/src/components/Delegate.tsx, AgentCard.tsx, RunList.tsx, RunView.tsx, ItemView.tsx; store mode and run selection;
                       api and types; copy
lakehouse/job_tasks.py agents task; databricks.yml task after decomposition and agreement_watch
```

The frontier split: `harness/agent.py make_client(backend=None)` takes an override; `summary.make_writer` and the new
agents pass `os.environ.get("FAIRSHARE_THINKER")`.

### API

All under `/api`, viewer-authenticated like the rest. Errors are `{code, message}`.

- `GET /agents` -> `{agents: [{key, name, summary, reads: [str], writes: [str], approver, scope_kind: manager|region|market,
  last_run: {run_id, status, created_at} | null}], managers: [str], markets: [{market_id, market}], crm_label}`
- `POST /agents/{key}/run` body `{scope: {manager?, region?, month?, market?}, writer?: guarded|template}` -> `Run` with
  status `running`; the work continues in a background task bound to the viewer's token.
- `GET /agents/runs?limit=20` -> `[RunHeader {run_id, agent, agent_name, scope, status, created_at, finished_at, items,
  needs_approval}]`
- `GET /agents/runs/{run_id}` -> `Run {run_id, agent, agent_name, scope, status, requested_by, model, created_at,
  finished_at, progress: {done, total, text}, items: [Item], error: str | null}`
- `Item {item_id, kind: page|clause|prospect|mismatch, title, subtitle, severity: ok|watch|risk|null, status:
  draft|approved|rejected, sentences: [Sentence], removed: [{sentence, reason}], verified_text, draft, facts: [{name,
  label, sql, source, rows}], sources: [{title, url, published, snippet}], action: {type: email|crm|none, subject, body,
  crm: {agency_id, activity_type, subject} | null}, decided_at, decided_by}`
- `POST /agents/runs/{run_id}/items/{item_id}/approve` body `{text?}` -> `Item` (422 `unverified` when an edit carries a
  number no fact supports; the CRM write happens here and is idempotent per item)
- `POST /agents/runs/{run_id}/items/{item_id}/reject` -> `Item`
- `GET /crm/activities?agency_id=` -> `[{activity_id, agency_id, activity_type, subject, happened_at, owner, notes,
  source: crm|app}]` newest first, both tables.

Run statuses: `running` -> `needs_approval` (at least one item is a draft) -> `approved` or `rejected` when no draft is
left, `failed` with `error` when a block raised. Statuses are derived from items, never set by hand.

### The chat router (server/stream.py)

Before the agent runs, the question is classified without a model:

- `meta`: it asks about the previous answer (what checks, which query, what was removed, how was that verified, which
  tables). The browser sends `last_answer` (the previous turn's calls, removed sentences, and verified count) with the
  request; the server writes the answer from that record, kind `meta`, no tools, no model. If there is no previous answer,
  it says so.
- `general`: it has no domain term (an agency name, a market, a KPI word, a region, a month, an agreement word) and reads
  like a concept question ("what is NDC", "explain fair share" is domain, "what does TMC stand for" is general). The
  writer model answers with no tools; the answer is labeled "This answer did not use your data." (kind `general`).
- everything else goes to the sales agent as today.

The classifier is a function with tests, not a model, so it is cheap and its behavior is on record.

## Nightly job

`lakehouse/job_tasks.py agents` runs the pack for every account manager and the watch for the latest month with the
thinking model, saves each run with its items as drafts (`needs_approval`), and prints what it removed. `databricks.yml`
adds the `agreement_watch` SQL task after `decomposition` and the `agents` task after it and `parity`. The existing test
that pins the SQL files to tasks is updated. The serverless environment gets no new dependencies.

## Deployment

`app_deploy.py` ships the new modules (already under `harness/` and `server/`) and `data/research/`. The frontier
model inside the App: a secret scope `fairshare` with the Azure OpenAI key, a `secret` resource on the app, and in
`app.yaml` `AZURE_OPENAI_API_KEY` from that resource plus `FAIRSHARE_THINKER=azure` and the endpoint and deployment
names. These steps need a deploy, which this session cannot run; the commands are in the morning note.

## Tests

- `evals/test_agents.py`: the registry; a pack run offline (template writer) for Marcus Lee has four items, every
  sentence verified, Harbor's item carries the mismatch line and the share clause at risk; the watch run for 2026-09
  lists Harbor's commitment at risk and Summit's tier distance; prospect for CLT-LGA quotes a cached source and its
  numbers verify with the URL as the source; mismatch finds Harbor's renewal; approve re-verifies an edit (422), writes
  one CRM activity (idempotent), and the run status follows the items; save and load through the state file.
- `evals/test_lakehouse.py`: the new bronze tables load and type; `ops.agreement_checks` has a row per clause per month;
  Harbor's 2026-09 commitment check is `watch` or `breached` with a repayment exposure; Summit's share clause is `ok`
  with a consecutive count; the bundle test includes the new tasks.
- `evals/test_api.py`: the agents routes (catalog, run, poll, approve, reject, crm activities) with the template writer.
- `evals/test_router.py`: the classifier on thirty questions.
- Web: vitest for the run status helpers; Playwright: the Delegate switch, a mocked run that goes from running to needs
  approval by polling, approve opens the mail draft and marks the item.

## Out of scope tonight

Foundry hosted agents (Entra, the project endpoint), live Bing grounding, Dynamics itself, Teams delivery, and any
change to the metric view.
