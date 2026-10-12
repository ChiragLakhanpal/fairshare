# Benchmark runs

| run | label | backend | Genie pass | harness supported | harness correct |
|---|---|---|---|---|---|
| 2026-10-12T07:38:09 | first run, metric view + trusted SQL | databricks | 0.7 |  |  |
| 2026-10-12T07:48:18 | second run: matcher by row overlap, attainment_pct column, rolling-average example | databricks | 0.95 |  |  |
| 2026-10-12T08:03:49 | third run: counting example, quarter example with change column, YoY guidance | databricks | 1.0 |  |  |
| 2026-10-12T08:11:25 | harness run 1: Genie + verifier + judge | databricks |  | 0.4 | 0.45 |
| 2026-10-12T08:24:45 | harness run 2: judge on the shared loop, fact pool by magnitude | databricks |  | 1.0 | 1.0 |
| 2026-10-12T08:25:14 | harness run 2: judge on the shared loop, fact pool by magnitude, question numbers as facts | databricks |  | 0.95 | 0.9 |
