# Benchmark runs

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
