# fairshare: rebuild the app as a React SPA on a FastAPI backend (replacing Streamlit)

## Context

The fairshare demo (`Explore/fairshare/`, sibling of jobflow) is the project Chirag will walk Director Matthew Bell and HM Austin Stargle through at the American Airlines on-site. The data layer, metric view, Genie space, Microsoft Agent Framework harness, deterministic verifier, AI/BI dashboard and the Databricks App are live. The current UI is five Streamlit pages. Chirag wants a from-scratch app for non-technical users: a Claude-style chat with the month's numbers at a glance, progressive disclosure, AA look, plain-English copy, and granular control over the UX that Streamlit cannot give.

The design was settled over four wireframe rounds on a private Design canvas: https://claude.ai/artifact/EJ6pt9X88M8Dwk7Ccmajje (source files in this session's scratchpad `wireframes/project/`). Round 4 is locked. This plan turns it into code.

## Decisions (locked by Chirag)

- Shell A: the month's summary is the first screen; a floating chat bar sits over it; on send the summary folds into a one-line strip; the strip or the sidebar's "This month's summary" unfolds it in place above the conversation; Escape folds it; "Start a new chat" returns to the summary.
- Sidebar collapses to a 56 px icon rail (choice remembered). Under "Start a new chat": four quick actions: This month's summary, Write my Monday brief, Prepare for an agency call (agency picker, then a prefilled question), Look up an agreement (picker, then the bar prefilled for the user to finish).
- Help is contextual, no Definitions or How-it-works pages: hover a dotted KPI word for a one-line tooltip; click it for a small window (plain definition, the Power BI check, "Show the formula" one click deeper); "How was that checked?" on a trust line and "See how this works" under the bar open the one "How this app gets an answer" window.
- Exports: Share on the summary (copy, email, PDF); Export on the Monday brief (copy, email to the VP, PDF, copy a link after approval); a "more" menu on every answer (copy, email, PDF, CSV for tables). Approving a brief records it server-side and opens a mail draft with the verified text; the app itself sends nothing.
- Conversation memory lives in the browser (localStorage), per user; follow-ups reuse the Genie conversation; the server stores only approved briefs (`ops.summaries`).
- Look: white and `#F2F5F8` surfaces, `#D0DAE0` hairlines, AA blue `#0078D2` only on actions, links and checks, `#00467F` only on the wordmark and hover, `#36495A` body text, `#627A88` secondary, `#C30019` only for a drop or a removed sentence. Type stack `"American Sans","AmericanSans Var",Inter,"Helvetica Neue",Arial` (aa.com uses AmericanSans Var, not licensable; the site also ships Inter). Scale: display 34/600 (-.02em), title 26/600 (-.02em), section 15/600, body 15/400, secondary 13.5, label 12/600 uppercase. Logo lockup top left: placeholder for the AA mark (asset from Chirag; AA brand rules restrict third-party use, his call), "American Airlines", "fairshare, agency sales".
- Copy: every explanatory line is a full sentence at a 12th-grade level, no LLM-sounding phrasing; buttons stay short verb phrases. "Open the sales dashboard" names the Databricks AI/BI dashboard.
- Motion (emilkowalski `apple-design` skill): springs with no overshoot (bounce 0, duration 0.3 to 0.4 s) for fold, unfold and sidebar collapse, interruptible; translucent floating bar and strip (`backdrop-filter`) with content scrolling beneath and scroll-edge fades, no hard dividers; pointer-down feedback; Send becomes Stop while an answer runs; windows open from their trigger; `prefers-reduced-motion` turns folds into cross-fades.
- Stack: Vite + React 19 + TypeScript + Tailwind v4, static build served by FastAPI in the same process as the Python harness, deployed as the existing Databricks App "fairshare" (resources warehouse `882107b449dd59cd`, Genie space `01f1c60a62e51bcea5943cdd14e9debb`, model endpoint `databricks-qwen3-next-80b-a3b-instruct`; scopes sql, genie, model-serving). Streamlit is removed.

## What exists and is reused (read-only facts from the three sweeps)

- Harness: `harness/agent.py` (`make_client`, `make_agent`, `ask` -> `Answer{text, verification, calls, sources, model}`), `harness/tools.py` (`ask_metrics` Genie, `run_sql`, `explain_change`, `search_contracts`; TOOL span wrapper at lines 24-31), `harness/summary.py` (`run(region, month, writer)`, `build_facts`, `save`, `history`), `harness/verifier.py` (`verify`, badges, flagged, verified_text), `harness/facts.py` (RunContext: calls with tool, args, sql, rows, note, preview), `harness/aio.py` (one event loop behind a lock).
- Data access: `fairshare/db.py` (`query`, `execute`, `state_execute`), `fairshare/dbx.py` (`set_user_token`, `workspace_client` with `auth_type="pat"`, `header_factory`, `bearer_token`, `warm_warehouse`).
- Tables: `aa_demo.gold.{dim_agency, dim_market, fact_agency_sales_monthly, fact_market_capacity, agency_pace, fact_corporate_bookings_weekly, sales_metrics}` and `aa_demo.ops.{decomposition, decomposition_markets, kpi_definitions, kpi_parity, summaries}`. Latest month Sep 2026. 12 agencies, 3 regions, 4 account managers.
- Deployment: `lakehouse/app_deploy.py` (INCLUDE allowlist upload to `/Workspace/Users/<me>/fairshare-app`, lean requirements, SNAPSHOT deploy), `app.yaml`. Databricks CLI v1.20 works. Free Edition stops apps 24 h after start (`app_deploy.py start` before a demo).
- Known hazards: process globals (`dbx._user_token`, `facts` RunContext, cached writer, agent cache per token, single event loop); f-string SQL for `region`, `month`, `agency`; Genie 13 to 40 s per answer, warehouse warm-up up to 90 s; the verifier can strip sentences; "Could not verify" is a first-class answer; capacity data is synthetic (do not claim "real seat data" in app copy); `latest.json` lacks `genie_pass_rate` (the old Under-the-hood showed 0%).
- Real numbers for fixtures (local DuckDB, Sep 2026): network $4,492,373 (+0.8% vs $4,456,241), share 37.8% vs fair 39.0%, gap -$143,384, pace 139.1%; movers Harbor -10.1 pts ($330,114, -16.4%, vol +32,836, mix -140, share -97,491, pace 96.1%), FareHub -8.1 pts ($337,460, -25.6%, pace 97.2%), Summit +4.3 pts ($600,998, +8.9%); Harbor markets CLT-LGA -14,784, LAX-JFK -12,039, DFW-DCA -11,341; week of 2026-09-21 corporate $416,407 on 377 tickets (+12.4% wow).

## Architecture

```
browser (React SPA, localStorage conversations)
  -> FastAPI (server/), same process as harness/, per-request viewer token
       -> Genie (as the viewer), SQL warehouse (as the viewer), model serving (as the viewer)
       -> ops.summaries for approved briefs only
  static: web/dist served by FastAPI with SPA fallback; /api/* JSON + SSE
```

### Backend (`server/`, Python) — merged from the Plan agent's design; see "Backend design" below.

### Front end (`web/`, Vite + React 19 + TS + Tailwind v4)

Dependencies: `react`, `react-dom`, `motion` (springs), `@radix-ui/react-tooltip`, `@radix-ui/react-popover`, `@radix-ui/react-dialog`, `@radix-ui/react-dropdown-menu` (accessible tooltip, window, modal, menu with focus and Escape handled), `lucide-react` (icons). No markdown renderer (answers are plain sentences), no chart library in v1 (the breakdown bars are divs; add Recharts only when a chart response exists), no PDF library (print CSS + `window.print()`), no state library (one small store on `useSyncExternalStore`).

Tree:
```
web/
  index.html, vite.config.ts (proxy /api -> :8000), tailwind via @tailwindcss/vite
  src/main.tsx, App.tsx
  src/styles.css            # @theme tokens: colors, font stack, type scale; print styles
  src/lib/api.ts            # fetch helpers + SSE reader for /api/ask (AbortController for Stop)
  src/lib/store.ts          # conversations in localStorage, sidebar collapsed, scope; grouped Today/Yesterday/Last week/Older; cap 50
  src/lib/format.ts         # money ($4.49M, $330K), pct, pts, dates
  src/lib/export.ts         # copy, mailto, print (PDF), CSV
  src/components/Sidebar.tsx        # expanded 256 px / collapsed 56 px, quick actions, recent, user footer
  src/components/TopBar.tsx         # region + month selects (URL query), dashboard link
  src/components/Summary.tsx        # headline, Stats, Movers, BehindPace, Share menu
  src/components/SummaryStrip.tsx   # folded one-line summary, whole strip is the toggle (aria-expanded)
  src/components/FloatingBar.tsx    # input, Send/Stop, empty-state chips
  src/components/Conversation.tsx   # turns; user bubble; Answer per assistant turn
  src/components/Answer.tsx         # sentences with badges, trust lines, disclosure buttons, panels, follow-up chips, more menu
  src/components/panels/Breakdown.tsx, Query.tsx, Numbers.tsx, Agreement.tsx, Steps.tsx
  src/components/Brief.tsx          # Monday brief card: sentences, removed box, Approve and send, Edit, Export menu
  src/components/Term.tsx           # KPI word: tooltip on hover, definition window on click (fetches /api/definitions once)
  src/components/HowItWorks.tsx     # the one help dialog
  src/components/AgencyPicker.tsx   # for the two quick actions
```

State model (store): `scope {region, month}` (mirrored in the URL query), `sidebarCollapsed`, `summaryExpanded` (true on a new chat, false after the first send, toggled by strip/sidebar/Escape), `conversations[]` `{id, title, createdAt, updatedAt, scope, genieConversationId?, turns: [{role, text, at, answer?}]}`, `activeId`, `inFlight {turnId, abort}`.

Behaviour details: nothing moves while typing; fold happens on send; Stop aborts the fetch (server cancels on disconnect); follow-up chips come from the answer payload (server suggests three) with a client fallback; quick actions "Prepare for an agency call" and "Look up an agreement" open AgencyPicker then prefill the bar (call prep sends immediately; agreement lookup leaves the cursor in the bar to finish the sentence); keyboard: Enter sends, Shift+Enter newline, Escape folds/closes, "/" focuses the bar; under 900 px the sidebar becomes a sheet and stats wrap.

Rendering by response type (server tags each answer with a `kind`): `numbers` (sentences + Numbers panel), `why` (sentences + Breakdown panel open by default), `agreement` (quote block with file and page), `refusal` (info-style trust line, proxy offered), `comparison` (table first), `brief` (Brief card). Unknown kinds render as `numbers`.

Copy source: all UI strings in `web/src/copy.ts`, written as full sentences; run the humanizer skill on that file before the first deploy.

## Backend design (`server/`, Python, same process as `harness/`)

Verified in the venv before designing: Agent Framework runs sync `@tool` bodies through `asyncio.to_thread` (contextvars propagate); `starlette.run_in_threadpool` and `to_thread` propagate contextvars, `loop.run_in_executor` does not; `agent_framework_openai` passes a callable `api_key` straight to `AsyncOpenAI` (resolved per call); `WorkspaceClient` construction probes the host (cache per token); SDK `Wait.result(timeout, callback)` gives a cancellation hook on Genie polls; fastapi 0.141, uvicorn 0.54, sse-starlette 3.5 are already installed; node 22 is installed but `npm` is not on PATH (`corepack enable` or `bun`).

New files:
```
server/__init__.py
server/main.py       create_app(): lifespan sets a 16-thread default executor, include api.router at /api, static mount; __main__ runs uvicorn on DATABRICKS_APP_PORT or 8000, one worker
server/context.py    Viewer(token, email, user, inside_app); async dependency reads x-forwarded-access-token/-email/-user, binds dbx.set_user_token; 401 {"code":"no_viewer_token"} when DATABRICKS_CLIENT_ID is set and no token arrived
server/validate.py   Region Literal["All","Central","East","West"], MONTH_RE ^\d{4}-(0[1-9]|1[0-2])$ + membership in months() (DISTINCT sales_month from ops.decomposition, cached 15 min), agencies() from dim_agency, RUN_ID_RE ^[0-9a-f]{12}$, topic <= 200 chars
server/schemas.py    pydantic models (shapes below)
server/serialize.py  records(df) (NaN -> null, dates -> ISO), call_json(ToolCall), answer_json(Answer, ctx), brief_json(result), genie_url()
server/api.py        routes: me, agencies, summary, explain, agreements, definitions, brief, brief/{id}/approve, brief/{id}, ask
server/stream.py     ask_events(viewer, body): SSE generator (queue bridge, timeout, cancel, cached fallback)
server/drafts.py     in-memory draft briefs {run_id: (expires, result)}, TTL 2 h, max 50, lock
server/cached.py     FAIRSHARE_MODEL=none fallback from app/cache/answers.json in the Answer shape
server/static.py     /assets mount (immutable) + SPA fallback (never for api/*); 503 no_web_build when web/dist/index.html is missing
evals/test_api.py    new tests (list below)
```

Endpoints (all under `/api`, JSON; errors `{"code","message"}`; 422 from validation):
- `GET /me` -> `{email, user, inside_app, scopes, backend, model, genie:{space_id,url}|null, data_through:"2026-09", regions, months (desc), links:{dashboard, genie, traces, repo, app}}`
- `GET /agencies` -> `[{agency_id, agency_name, agency_type, region, account_manager}]`
- `GET /summary?region&month` -> `{region, month, prior_month, kpis:{aa_revenue, aa_revenue_prior_year, yoy_pct, aa_share_pct, fair_share_pct, share_gap_pts, share_gap_usd, pace_pct}, movers:[3 x {agency_id, agency, share_now_pct, share_prior_pct, share_chg_pts, revenue_now, yoy_pct}], behind_pace:[{agency_id, agency, pace_pct, aa_revenue, yoy_pct}], headline, calls:[Call]}`. New portable SQL in `summary.py`: `_region_pred()` (region "All" drops the predicate), a pace block over `agency_pace`, a movers block over `ops.decomposition` ordered by `ABS(aa_share_now - aa_share_prior)` limit 3, behind_pace = the existing agencies block (`summary.py:60-76`, add `agency_id`) filtered `pace_pct < 100`. `headline()` is deterministic code from the kpis (pace >= 100 "ahead of pace" else "behind pace"; |gap| < 2 pts "a little under/over fair share", else "under/over fair share by N points"). The brief's FACTS keep the four existing blocks so `test_template_summary_verifies_clean` and the benchmark are untouched.
- `GET /explain?agency_id&month` -> `{agency, month, prior_month, summary:{revenue_now, revenue_prior, delta_revenue, delta_pct, market_delta_pct, aa_share_now_pct, aa_share_prior_pct, fair_share_now_pct, fair_share_prior_pct, volume_effect, mix_effect, share_effect, fair_share_effect, parts_sum}, markets:[{market, share_effect, mix_effect, aa_share_now_pct, aa_share_prior_pct, market_revenue_now}], could_not_verify, calls}`; 404 `no_decomposition`. Reuses `explain_change.func` via `run_in_threadpool`; the API resolves `agency_id` to the exact `agency_name`, so free text never reaches SQL.
- `GET /agreements?agency_id&topic` -> `{agency, topic, hits:[{file, page, text, score}]}` (top 3) from a new `tools._search()` pulled out of `search_contracts` (`tools.py:244-257`).
- `GET /definitions` -> `{kpis:[kpi_definitions rows], parity:{run_id, run_at, kpis, rows, drift, grid, drifting (<= 20), source}|null, runs}` (CSV fallback offline).
- `POST /brief {region, month, writer: guarded|unguarded|template}` -> `Brief {run_id, region, month, created_at, status:"draft", model, writer, sentences:[Sentence], removed:[{sentence, reason}], verified_text, draft, calls}`; `POST /brief/{run_id}/approve` -> `summary.save(status="approved")` -> `{run_id, status, table}` (404 `draft_expired`); `GET /brief/{run_id}` -> Brief from the draft store, else from `ops.summaries` via a new `summary.load(run_id)`.
- `POST /ask {question (<= 2000), history (<= 6 turns, each <= 4000), genie_conversation_id?, scope?}` -> `text/event-stream`. `scope` is prepended as one line ("Current scope: Central, 2026-09") so Genie and SQL default to it.

Shared shapes: `Call {i, tool, args, sql, rows, note, preview (<= 50 rows), genie:{conversation_id, message_id, url}|null, ms}`; `Sentence {text, status: verified|flagged|note, numbers:[{raw, source, fact}]}`; `Answer {question, text, model, kind, sentences, removed, could_not_verify, verified_text, calls, sources, follow_ups:[3 strings], genie_conversation_id, timing:{total_ms, tools_ms}, cached|null, trace_url}`. `kind` is derived server-side from the tools used (explain_change -> why, search_contracts -> agreement, a refusal line -> refusal, two agencies in the question -> comparison, else numbers); the brief has its own endpoint.

SSE (`POST /api/ask`, read with `fetch` + `ReadableStream`, not `EventSource`): each message `id: <seq>`, `event: <type>`, `data: <json>`. Order: zero or more `status`/`tool`, then exactly one `answer` or `error`, then `done`. Pings every 15 s. Events: `status {phase: model|warehouse|genie|sql|explain|agreement|verify, text, tool, args, genie, t_ms}`, `tool` (a Call, emitted when a tool finishes), `answer` (Answer), `error {code: timeout|busy|agent_failed|no_model|cancelled, message}`, `done {t_ms}`. Hook: the `_traced` decorator at `harness/tools.py:24-31` becomes `_instrumented(name, phase)` and always wraps (emits a status before the body and `model` after; opens the MLflow span only when tracing is on; `functools.wraps` keeps the `Annotated` signature); `_genie_ask` emits `warehouse` before `warm_warehouse()` (`tools.py:61`) and `genie` once the `Wait` returns ids. Stop = client `AbortController.abort()`; sse-starlette cancels the generator on disconnect; the generator's `finally` sets `ctx.cancel` and cancels the agent task. If the Apps proxy cuts idle streams despite pings, the queue design allows a thin `GET /api/ask/{id}/events?after=` poller later.

Genie follow-ups: the browser sends `genie_conversation_id` (stored on the thread); it lives on `RunContext.genie_conversation_id`; `_genie_ask` uses `w.genie.create_message(space, conversation_id, content)` when set, else `start_conversation`; 400/403/404 on continue falls back to a fresh conversation; the final answer returns the id. Deep link `{host}/genie/rooms/{space_id}/chats/{conversation_id}` (confirm once in the workspace).

Identity and run-context refactor (numbered edits):
1. `fairshare/dbx.py:20-29`: `_user_token` -> `ContextVar`; `set_user_token()` returns the reset token; add `reset_user_token()` and a `bind(token)` context manager. `bearer_token()` and `header_factory()` already call `user_token()`.
2. `fairshare/dbx.py:62-68`: `workspace_client()` -> `_client_for(user_token())` with `lru_cache(maxsize=32)` building `WorkspaceClient(host, token, auth_type="pat")`; `None` keeps the laptop client.
3. `fairshare/db.py:23,51-71`: one SQL connection per token `{token: (conn, lock)}` (viewer token -> `sql.connect(..., access_token=token)`; `None` keeps the PAT/header_factory branch), cap 8 (evict oldest); `query()` locks per connection (the connector is not documented thread-safe); DuckDB uses a cursor per query.
4. `harness/facts.py:41-51`: `_current` -> `ContextVar`; `current()` creates lazily; `reset(**kw)` sets a fresh one; add `use(ctx)`.
5. `harness/facts.py:26-38`: RunContext gains `on_event`, `cancel: threading.Event`, `genie_conversation_id`, `t0`; methods `emit(type, **data)`, `check_cancel()` raising `Cancelled`, `clear()` (pool/calls/sources only). `ToolCall` gains `genie`, `ms`; `record()` emits `tool`.
6. `harness/tools.py:24-31`: `_traced` -> `_instrumented(name, phase)`; decorators at 102/144/177/241 get their phase.
7. `harness/tools.py:56-95`: `_genie_ask(question, conversation_id=None) -> (text, df, sql, conversation_id, message_id)` using the non-`_and_wait` calls, the existing 429 backoff around the start, `wait.result(timeout, callback=lambda m: ctx.check_cancel())`; `ask_metrics` (103-120) passes and updates the conversation id and records `genie={...}`.
8. `harness/tools.py:244-257`: extract `_search(agency, topic)`.
9. `harness/agent.py:84-92`: databricks branch `api_key=bearer_token` (the function); one agent for all viewers, memoized `get_agent()`; the Streamlit per-token cache goes away.
10. `harness/agent.py:110-146`: split into `async def ask_async(question, agent=None, *, history=()) -> Answer` (history turns passed as prior messages; `facts.reset()` at 133/138 become `ctx.clear()`) and `def ask()` = span + `aio.run(ask_async())` for the CLI, benchmark and cache. `Answer` gains `genie_conversation_id`, `elapsed_ms`. One line in `INSTRUCTIONS`: numbers from earlier turns must be re-queried.
11. `harness/summary.py:26-107`: `_check_scope(region, month)` allowlist at the top, `_region_pred`, per-block functions, `build_facts(region, month, blocks=...)`, `headline()`; `UNGUARDED_INSTRUCTIONS` moves here from `app/pages/1_Monday.py:20-21`.
12. `harness/summary.py:201-229`: `run_async()` (`to_thread(build_facts)`, `await writer.run`, verify) and `run()` = span + `aio.run()` for `lakehouse/job_tasks.py`; `facts.reset()` at 223 becomes `facts.current().clear()`; add `load(run_id)`.
13. `harness/aio.py` unchanged; the server never calls it (every model call happens on uvicorn's loop; `test_server_never_calls_aio`).
14. `server/context.py` binds the token in an `async` dependency; `stream.py` re-binds `dbx.set_user_token` and `facts.reset(on_event=..., genie_conversation_id=...)` as its first statements so the agent task (`create_task` copies the context) and every `to_thread` tool body share them.

Concurrency and budgets: one uvicorn worker, async endpoints; deterministic endpoints use `run_in_threadpool`; `GENIE_TIMEOUT_S=150`, warm-up 90 s, `ASK_TIMEOUT_S=300` via `asyncio.wait_for`, `ASK_CONCURRENCY=4` (semaphore; beyond it `error{busy}`). `EventSourceResponse(gen, ping=15, send_timeout=30, headers Cache-Control no-store, X-Accel-Buffering no)`. Uncancellable remainder after Stop: one Genie poll or one SQL statement.

Static: router at `/api`, then `/assets` mount (hashed, immutable), then catch-all: 404 JSON for `api/*`, `FileResponse` for real files inside `web/dist`, else `index.html` with `no-store`.

Deployment: `app.yaml` command `["python", "-m", "server.main"]`, drop the Streamlit env var; `lakehouse/app_deploy.py:28` `INCLUDE = [app.yaml, requirements.txt, server, harness, fairshare, data/contracts, web/dist, app/cache, evals/results/latest.json]`; `APP_REQUIREMENTS` (32-41): remove streamlit, add fastapi, uvicorn, sse-starlette; `deploy()` (111-123) runs the web build first (`corepack npm ci && corepack npm run build`, or bun) and refuses to sync without `web/dist/index.html`. Build locally and upload `web/dist` (no `package.json` at the app root: Free Edition egress is restricted and the bundle is a few hundred KB). `.gitignore`: `web/node_modules/`, `web/dist/`.

Local dev: `.venv/bin/uvicorn server.main:app --reload --port 8000` + `cd web && npm run dev` (Vite proxies `/api`). Offline (`FAIRSHARE_BACKEND=duckdb FAIRSHARE_MODEL=none`): `/me` reports `model:"none"`, `/ask` serves `app/cache/answers.json` for the three scripted questions (`status{model}`, `answer{cached}`, `done`) and `error{no_model}` otherwise; `/brief` uses the template writer; `/definitions` uses the CSV.

Risks: callable `api_key` must resolve per request (test 12 proves it on day one; fallback = per-token agent LRU); never use `run_in_executor`; SQL connector thread safety (per-token lock); Genie continuation across expiry (fallback); Apps proxy idle timeout on SSE (pings; polling contingency); `npm` not on PATH (`corepack enable`); `summary.save` needs the viewer's write grant on `ops.summaries` (unchanged); the "note" sentence status and the extra `agency_id` column must not change `template_draft`.

Tests (`evals/test_api.py`, FastAPI TestClient, conftest already forces duckdb/none/no tracing): me offline; region/month allowlists (422 on `Central' OR '1'='1`, `2026-13`, `2024-01`); summary for a region and for All (3 movers, behind_pace all < 100, headline deterministic); explain unknown agency 422 and Harbor August parts_sum; agreements Summit page 2 with "45%"; definitions offline parity CSV; brief template -> approve -> get (tmp state file); approve unknown 404; ask cached SSE order (`status, answer, done`, ids increasing); ask SSE with a stub agent (expect `status(sql), tool, status(model), status(verify), answer, done`); identity isolation across two parallel requests with different tokens (and the test thread's var unset afterwards); bearer token resolved per request (httpx MockTransport sees two Authorization headers); SPA fallback (route -> index.html, `/api/nope` -> 404 JSON, missing asset 404, no build 503); SQL connection per token; cancel stops the Genie wait; server never calls `aio`; Stop sets cancel. Front end: `web/src/lib/sse.test.ts` parses a stream split at arbitrary byte boundaries; `npm run check` = `tsc --noEmit && vite build`.

## Build order (work in `Explore/fairshare/`, own git; commit per step; pre-commit gate must stay green)

0. Write this plan's design section as `docs/superpowers/specs/2026-10-14-react-app-design.md` (link to the canvas) and commit. Install the design skills: `npx skills@latest add emilkowalski/skills` (apple-design, animate, review-animations, break-ui). `corepack enable` so `npm` resolves.
1. Backend edits 1-5 (dbx, db, facts) and adapt `evals/test_lakehouse.py:72-87` to `dbx.bind()`; `pytest evals -q` green.
2. Backend edits 6-14 (tools, agent, summary); `python -m harness.agent "..."`, `python -m harness.summary` and `evals/run_benchmark.py --check` still work.
3. `server/` deterministic endpoints + static + their tests.
4. `server/stream.py` + `/api/ask` + cached fallback + the SSE, identity and cancel tests.
5. `app.yaml`, `app_deploy.py`, requirements; deploy with a placeholder `web/dist/index.html` to prove uvicorn, the forwarded headers, Genie and the model inside the App.
6. Front end, in this order: tokens and shell (Sidebar, TopBar, FloatingBar) -> Summary + Strip + fold/unfold -> Conversation + Steps + Answer panels + Stop -> Brief + exports -> quick actions + AgencyPicker -> Term tooltips/windows + HowItWorks -> motion polish, reduced motion, print CSS, 900 px layout. `npm run check` clean; vitest; Playwright smoke.
7. Deploy the real bundle; run the demo script in the live app as the viewer.
8. Remove Streamlit (`app/Home.py`, `app/pages/`, `app/common.py`, `.streamlit/`; keep `app/cache/`); update `CLAUDE.md` layout and commands, `README.md`, `docs/walkthrough.md` (also fix its stale Maverick line); run `review-animations` and `break-ui` (long agency names, empty history, zero movers, a month with no prior year, a flagged-only answer) before calling it done; humanizer pass on `web/src/copy.ts`.

## Verification

- `pytest evals -q` plus new API tests (identity isolation across two fake tokens, allowlist rejections, SSE event order and final payload, SPA fallback, brief approve/get). Offline mode (`FAIRSHARE_BACKEND=duckdb`, `FAIRSHARE_MODEL=none`) must pass.
- `npm run build` clean; vitest for store grouping, format, export helpers.
- Playwright smoke against the Vite dev server with mocked `/api`: summary renders the five numbers; a sent question folds the summary into the strip and streams steps; the strip unfolds; sidebar collapse persists across reload; the definition window opens and closes with Escape.
- Live: `python lakehouse/app_deploy.py deploy` then open the app as the viewer; run the demo script (Why is Harbor down, Summit DFW to ORD, Summit agreement, churn, Write my Monday brief, approve); confirm Genie deep links open the conversation; confirm the Stop button cancels.
- Design check: screenshot each state at 1440 and 390 wide and compare against the canvas boards; copy pass with the humanizer skill.

## Open items outside this plan (unchanged)

T-100 download (fair share is synthetic today), Foundry hosted deploy (no azd), public GitHub repo (needs his yes), rehearsal and recording, Genie in-space benchmarks.
