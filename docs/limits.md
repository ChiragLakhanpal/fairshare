# Platform limits met while building

Recorded as they are hit, with the date. Nothing here is from a doc page; those are in the plan.

| Date | Platform | Limit or behaviour | Effect | Workaround |
|---|---|---|---|---|
| 2026-10-11 | DuckDB 1.5 | One writer per file; a read-only reader blocks a writer | The app and a rebuild cannot run at the same time | App opens read-only; `lakehouse/run.py` sets `FAIRSHARE_WRITE=1`; summaries live in a separate small file |
| 2026-10-11 | DuckDB / Databricks SQL | Column aliases are case-insensitive | `T_now` and `t_now` collided in the decomposition and the shares came out 9x too small | Distinct names (`tot_now`); noted in CLAUDE.md rule 5 |
| 2026-10-11 | Streamlit | `$...$` in markdown renders as LaTeX | Dollar amounts turned into italic maths | `esc()` in `app/common.py` on every prose string |
