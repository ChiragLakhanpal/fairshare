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
