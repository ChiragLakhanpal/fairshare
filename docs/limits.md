# Platform limits met while building

Recorded as they are hit, with the date. Nothing here is from a doc page; those are in the plan.

| Date | Platform | Limit or behaviour | Effect | Workaround |
|---|---|---|---|---|
| 2026-10-11 | DuckDB 1.5 | One writer per file; a read-only reader blocks a writer | The app and a rebuild cannot run at the same time | App opens read-only; `lakehouse/run.py` sets `FAIRSHARE_WRITE=1`; summaries live in a separate small file |
| 2026-10-11 | DuckDB / Databricks SQL | Column aliases are case-insensitive | `T_now` and `t_now` collided in the decomposition and the shares came out 9x too small | Distinct names (`tot_now`); noted in CLAUDE.md rule 5 |
| 2026-10-11 | Streamlit | `$...$` in markdown renders as LaTeX | Dollar amounts turned into italic maths | `esc()` in `app/common.py` on every prose string |
| 2026-10-11 | Databricks Free Edition | Personal access token dialog spun for a minute and never returned the token | No PAT | OAuth as the user through the system browser (SDK `auth_type=external-browser`, cached); the SQL connector takes the SDK's header factory |
| 2026-10-11 | databricks-sql-connector | DDL through the connector blocked without end | Build hung | DDL goes through the Statement Execution API with a bounded wait; the connector is used for SELECTs only |
| 2026-10-11 | Databricks metric views | A dimension named `agency` and a join alias named `agency` collide (`agency.agency_name` read as a field of a STRING) | View creation failed | Join aliases `ag`, `mkt`, `cap` |
| 2026-10-11 | Genie Create Space API | Every list must be sorted by id or identifier; exactly one text instruction item; list-of-lines fields are concatenated with no separator | Four rejected payloads | One text block, one element per text field, lists sorted recursively |
| 2026-10-12 | Databricks Free Edition | Starter warehouse auto-stops after 10 minutes; the setting is not editable on free accounts; Genie then waits in PENDING_WAREHOUSE far longer than a direct start (8 s) | Genie calls timed out after idle periods | The Genie tool starts the warehouse first; `python -m harness.keepwarm` during a demo |
| 2026-10-12 | Databricks metric views | The YoY window measure (`offset: -12 month` on sales_month) is only right when the query groups by sales_month; at quarter grain it returned +350% | A wrong number that was nonetheless "from a query" | Genie instruction and a trusted quarter example that computes the change in SQL; measure comment says month grain |
| 2026-10-11 | Microsoft Foundry | The dated Azure OpenAI api-version path answered "API version not supported"; gpt-4.1-mini is marked Legacy in the catalog | First model calls failed | The `/openai/v1` OpenAI-compatible surface with the key as bearer; deployment `gpt-5-mini` (GA) |
| 2026-10-11 | Foundry portal | The SPA stops answering the Chrome extension after the first navigation | Could not read the deployments page | Used the deployments API with the key instead |
| 2026-10-12 | Homebrew on this Mac | `brew install azd` fails (Tier 3 configuration, no bottle) | No Azure Developer CLI yet | Install from Microsoft's script or a release binary before the Foundry hosting step |
