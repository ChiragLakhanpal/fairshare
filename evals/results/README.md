# Benchmark runs

Two judges score the same twenty questions. The repo runner (`evals/run_benchmark.py`) matches by value: a Genie row passes
when it carries at least half of the ground-truth row's numbers within rounding, so column names, types and extra columns do
not count. Genie's own evaluation inside the space (`lakehouse/genie.py eval`, the Benchmarks tab) compares the two result
sets column by column and has a judge name the difference. On Oct 14, 2026 the in-space judge scored 15/20 where the runner
had 20/20: four were column shape (a `date_trunc` alias typed TIMESTAMP against a DATE `sales_month`, a quarter label against a
bare year), one was a real error the half-overlap rule had let through (Genie multiplied `attainment_pct`, already a percent,
by 100), and one answer gave the percent change without the dollar change. Three instruction lines and one ground-truth label
later (q04 says `Q3 2025`, not `2025`): 20/20 under both. The `*-genie-eval.json` files hold Genie's SQL and the reason codes.
On Oct 19 the in-space score went 17/20 (q09, q10 and q17 missed), 17/20 on an unchanged rerun (q07, q10 and q11 missed), then
20/20: the judge is column-strict and Genie's SQL varies from run to run, so q07, q09, q10, q11 and q17 now say which columns to show.
On Oct 20, 2026 the MLflow experiment held traces from the three Oct 12 harness runs (08:11, 08:24 and 08:25: 120 traces, an answer and a judge call for each of the 20 questions in each run) and none from the Oct 13 runs, so the Qwen3-Next run behind the measured slide was not traced.

| run | label | backend | Genie pass | harness supported | harness correct | model |
|---|---|---|---|---|---|---|
| 2026-10-12T07:38:09 | first run, metric view + trusted SQL | databricks | 0.7 |  |  | (Genie only) |
| 2026-10-12T07:48:18 | second run: matcher by row overlap, attainment_pct column, rolling-average example | databricks | 0.95 |  |  | (Genie only) |
| 2026-10-12T08:03:49 | third run: counting example, quarter example with change column, YoY guidance | databricks | 1.0 |  |  | (Genie only) |
| 2026-10-12T08:11:25 | harness run 1: Genie + verifier + judge | databricks |  | 0.4 | 0.45 | azure/gpt-5-mini |
| 2026-10-12T08:24:45 | harness run 2: judge on the shared loop, fact pool by magnitude | databricks |  | 1.0 | 1.0 | azure/gpt-5-mini |
| 2026-10-12T08:25:14 | harness run 2: judge on the shared loop, fact pool by magnitude, question numbers as facts | databricks |  | 0.95 | 0.9 | azure/gpt-5-mini |
| 2026-10-13T15:42:46 | harness run 3: Databricks Llama 4 Maverick, the model inside the Databricks App (judge is Maverick too) | databricks |  | 0.95 | 0.55 | databricks-llama-4-maverick |
| 2026-10-13T15:52:07 | harness run 4: Databricks Llama 4 Maverick as the agent, gpt-5-mini as the judge (the judge is now fixed across runs) | databricks |  | 0.85 | 0.75 | databricks-llama-4-maverick |
| 2026-10-13T16:01:43 | harness run 5: Databricks Qwen3-Next 80B instruct as the agent (the model inside the Databricks App), gpt-5-mini judge, pasted-call guard | databricks |  | 0.85 | 0.75 | databricks-qwen3-next-80b-a3b-instruct |
| 2026-10-14T12:55:20 | Genie's in-space evaluation of the same twenty benchmarks (run 01f1c8086f1e191fbab00c06ebe31929, 0 need review) | databricks | 0.75 |  |  | (Genie only, Databricks judge) |
| 2026-10-14T13:03:28 | Genie's in-space evaluation of the same twenty benchmarks (run 01f1c809a4101e6bb984d91864fcc203, 0 need review) | databricks | 1.00 |  |  | (Genie only, Databricks judge) |
| 2026-10-19T21:11:29 | Genie's in-space evaluation of the same twenty benchmarks, after the pace fix (run 01f1cc3b9bd8150d8d8453bf60ef193c, 0 need review; missed q09, q10, q17) | databricks | 0.85 |  |  | (Genie only, Databricks judge) |
| 2026-10-19T21:29:48 | Genie's in-space evaluation of the same twenty benchmarks, rerun unchanged (run 01f1cc3e45691089b3b6a7ff28ab8507, 0 need review; missed q07, q10, q11) | databricks | 0.85 |  |  | (Genie only, Databricks judge) |
| 2026-10-19T21:36:12 | Genie's in-space evaluation of the same twenty benchmarks, q07, q09, q10, q11, q17 name their columns (run 01f1cc3f2c02140a870423eca2b920b4, 0 need review) | databricks | 1.00 |  |  | (Genie only, Databricks judge) |
