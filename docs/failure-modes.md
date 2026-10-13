# Failure modes on the day, and what to do

| What breaks | What you see | What you do |
|---|---|---|
| Conference Wi-Fi blocks or drops | Genie or the model times out | Phone hotspot (set it up before the room). The app is on the laptop; only Genie, the model and traces need the network. |
| Still no network | Ask page cannot call the model | `FAIRSHARE_MODEL=none` in `.env` and restart: the Ask page serves the cached scripted answers (`app/cache/answers.json`), Monday uses the template writer, Why and Definitions are fully local (DuckDB, cached parity). |
| Genie rate-limits (429) | `ask_metrics` says Genie failed | The agent falls back to `run_sql` on its own; the answer still carries SQL. Say so out loud: "Genie is rate limited, it wrote the SQL itself." |
| Model quota exhausted on the free trial | 429 from Azure | `FAIRSHARE_MODEL=databricks` (serving endpoint) or `none`. |
| The model drafts a clean summary when you wanted to show the guard | No red box | Switch the writer to the unguarded prompt and rebuild; show the runs table with flagged counts. Never fake a flag. |
| The laptop dies | Nothing | The recorded run (`docs/demo-recording.mp4`) on the phone, and the PDF of the walkthrough. |
| A number on screen differs from the walkthrough script | You say one thing, the screen says another | Read the screen, not the script. The script is re-checked the night before; the data is deterministic, so a difference means a rebuild changed something: say that. |
| DuckDB file lock error when starting the app | "Could not set lock on file" | Another process (a rebuild or a test) holds the file; stop it. Rebuilds need the app stopped. |
| The dashboard shows spinners or a stale month | Tiles loading for a minute | The first load after a publish runs every dataset on the 2X-Small warehouse: open the dashboard before the call and leave the tab. If a tile is wrong in the editor, ignore it: the editor previews a widget expression as its first aggregate; the published page is right. |
| The Databricks App is stopped | "App is not running" | Free Edition stops apps 24 hours after a start: `python lakehouse/app_deploy.py start` (a minute). The laptop app is the demo path anyway. |
| The app inside Databricks answers with a pasted query or no text | A JSON blob or "Could not verify: the model wrote a query" | The open model wrote the tool call instead of making it; the harness retries once, then refuses. Say so: "that is the Databricks-hosted model, Foundry's gpt-5-mini does not do that; the verifier would have stopped the numbers either way." Ask again or switch to the laptop. |
| The Chrome extension drives the Databricks console | "Automated browser control detected" banner, clicks hang | Not a demo-day event, but if it appears, reload the page by hand; it is cosmetic for a human viewer. |
