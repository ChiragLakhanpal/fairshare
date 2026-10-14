# The ten-minute walkthrough (five beats)

Audience: a sales director who is "not super technical but very smart," and the hiring manager who built the data. Every
technical thing gets three sentences before any jargon: what the person asks, what they get back, why they can trust it.
Then one layer deeper only if asked. Numbers below are from the local build; re-check them against the live app the night before.

**0:00 The dashboard (one minute).** The AI/BI dashboard, already open (the first load after a publish takes a minute on the
free warehouse). "This is the Monday view a sales director has today, on the same metric view everything else here uses.
September close: the network is at 139% of pace, AA share 37.8% against a fair share of 39%. The red bar on the left is what
moved: Harbor Business Travel, ten points of share below last September. The dashboard can show you that. It cannot tell you
why, whether it is capacity or the agency, what the agreement says, or whether the number is right. That is what the app
is for." If there is time, pick Harbor in the Agency filter: the trend line shows the collapse from February and the
partial recovery, with fair share flat at 40%. One sentence on placement: "At American this is the Power BI report on the
mirrored catalog, same definitions." Then the question: "An account manager at my current company asks me the same thing yours
ask you: why is Summit's share down on Dallas to Chicago, and what does their contract say about it? Today that is a ticket, a
query, and a few days. I built a small version of what I think your global sales agent should be, on public airline seat data,
with made-up agencies on top. One screen, one Monday."

**1:00 The app opens on the month (two minutes).** All regions, September. "This is what an account manager sees on Monday:
one sentence, five numbers, the three agencies that moved, who is behind pace. Hover a word like fair share and you get the
definition; click it and you get the Power BI check." Then the sidebar: "Write my Monday brief." Point at the checks: "every
sentence here was checked against its query; the brief tells you when it removed one." If a red box appears: "this sentence
the model wrote on its own; no query supports it, so it never reaches the VP. A person still presses Approve, and that opens
the email." Do not fake it; the brief says exactly what it removed.

**3:00 Why (two minutes).** Click "Why did this happen?" next to Harbor Business Travel (the same month as the dashboard and
the summary). The summary folds into the strip at the top; the answer comes back with the breakdown open: revenue 330K,
down 16.4%. "The agency sold more travel overall, plus 8.3%, so it is not volume. AA share went from 44.3% to 34.2%; that is
97K of the 65K drop, offset by 33K of volume. Fair share did not move, 40.1% both years, so AA did not lose capacity: the
agency moved share to other carriers, mostly on CLT-LGA, LAX-JFK and DFW-DCA. The three parts sum to the total; that is
arithmetic in the warehouse, not a model." Then the one line it will not say: "Could not verify whether they changed a
preferred-carrier setting; not in the data." (August tells the same story: 386K, down 15.5%, share 45.6% to 35.4%, 110K of
share against 40K of volume, fair share 39.5% to 39.9%.)

**5:00 Ask (two and a half minutes).** Three questions in the chat bar, in this order. Summit on DFW to ORD, Q3 2026 vs
Q3 2025: revenue $221K to $298K, AA share 46.3% to 53.5%, fair share flat at 37.7%, so the share gap went from 8.6 to 15.9
points; "Show the query" opens the MEASURE() query Genie wrote against the metric view, and "Open in Genie" opens the same
conversation in Genie. The contract question: clause 5.1 quoted with file and
page (below 45% for two consecutive quarters), and the quarterly shares from 45.1% to 52.6% showing it has not happened. Then
"which agencies are about to churn": it refuses, explains there is no churn label, and offers a labeled proxy. "Unknown is an
allowed answer. That is the difference between a demo and something you can put in front of a VP." If Wi-Fi fails, the three
answers are cached from a real run (the page says so).

**7:30 Definitions and parity (one and a half minutes).** Click "AA share" under the number. "Written once in English; this
is the Databricks metric view the agent and Genie use; show the formula; a nightly job computes the Power BI twin too and
the window says whether they matched." Three runs are on record: 1,500 checks green, then the retired passenger-based twin
red on all 250 months of AA share, then green again after the fix (lakehouse/parity.py --retired reproduces it). "When your VP asks why two numbers differ, this page answers before the meeting."
The callback: "Harbor's 34.2% on the dashboard tile, in Genie's answer and in the Monday summary is one measure evaluated three
times. That is what a metric view buys, and the dashboard's own Definitions check tile reads the same parity table."

**9:00 How this app gets an answer (one minute, then stop).** Click "See how this works" under the chat bar: the path a
question takes and the benchmark scores. "Three layers. Data: bronze, silver, gold in Databricks. Definitions:
one metric view. Agent: Genie for the numbers, a decomposition for why, the agreements for terms, a harness that picks the tool
and a verifier that refuses to show a number no query returned. The harness is the same code on my laptop and in Foundry.
Twenty benchmark questions with known answers: Genie passed 14 the first time, 19 after two trusted examples and a column it kept
asking for, all 20 on the third run; every run is logged. The same twenty sit in the space's own Benchmarks tab, so Databricks
grades Genie too: its judge gave 15 the first time, and it caught a percent multiplied by 100 that my matcher had let through;
three instruction lines later, 20 under both judges." Open How it works in the app: the twenty questions, one row each, with
the four marks (Genie, Databricks's judge, backed, judged) and the links out to the Benchmarks tab, MLflow and the job. Then the
MLflow experiment: one trace per answer, model calls and tool calls in order.
Then one click: the same app running inside the workspace as a Databricks App, signed in as you (the sidebar says so). "SQL, Genie and the model run
with the viewer's permissions, never a service principal's, so an agency user would only ever see their own rows. The model in
there is Databricks-hosted Qwen3-Next, because a Free Edition app cannot reach Foundry; same harness, same verifier, and
the benchmark table shows what each model scored."
At American the same shape: your gold layer from the migration, metric views for your KPIs, Genie agents per domain, the
harness in Foundry or Copilot Studio so it lives in Teams, and the agency version runs with each agency's identity. The first
six months are the data and the definitions. This is what month seven looks like."

**10:00 Stop.** "What would you want it to answer that it doesn't?"

## The three-beat version (if the slot is five minutes)

The dashboard (thirty seconds: pace, the red bar, "it stops here"), Monday (badges and the red box), Ask (the first and the
third question), the diagram. Skip Why and Definitions; mention each in one sentence.

## Before the call

Open the published dashboard and let it load (a minute). `python lakehouse/app_deploy.py start` (Free Edition stops apps after
24 hours). `python -m harness.keepwarm` in a terminal. Have two dashboard links ready: the network view and the Harbor view (the
Agency filter is in the URL). The laptop app (uvicorn on 8000 with the Foundry model, `web/dist` built) is the demo path; the
Databricks App is one click in beat five. Clear the browser's conversation history first ("Start a new chat" and the trash
icons in Recent) so the sidebar is clean.

## If asked to build live

Add a measure to the metric view (average fare: `SUM(source.aa_revenue) / NULLIF(SUM(source.aa_pax), 0)`), rerun
`lakehouse/run.py` for the metric view, add a benchmark question for it, run `evals/run_benchmark.py --check`, show the
pre-commit hook and `.claude/hooks/block-destructive.py`. Five minutes, rehearsed. That is the version of "vibe coding" a
director should want: rules, a review loop, a gate.

## Questions to expect, one line each

- Why Agent Framework and not Agent Bricks Supervisor? Because the harness you described is Microsoft's; the demo puts a Genie agent inside it, which is the shape you said. Supervisor would be the all-Databricks version of the same thing.
- Why not Genie agent mode for "why"? For a known "why" (volume, mix, share) a fixed decomposition is consistent across analysts; agent mode is for the open-ended exploration after that.
- What about per-agency security? Genie runs as the asking user; Unity Catalog row filters do the rest; the harness carries the user's token, never a service principal.
- How do you know it is right? Twenty questions with known answers before and after every change, the verifier on every answer, and traces for anything that goes wrong.
- What is fake? The agencies, the corporates, the contracts. The seats are BTS T-100. The Power BI twin is a second SQL implementation because Power BI Desktop is Windows only.
- Why an app and not just the dashboard? The dashboard is the leadership view: what and where, one glance. The app is the conversation: why, the agreement, a verified summary, and the query one click away. Both read one metric view, so they cannot disagree.
- Why React and FastAPI and not Streamlit? Granular control of the experience for non-technical people: progressive disclosure, a floating chat bar, windows where the information is needed, exports; and a per-request identity so two viewers never share a token or a fact pool.
- What about Genie App Builder? It would let a sales team describe a view and get an app inside an App Space, one governance boundary for identities, scopes and cost. It is in Beta and not on Free Edition, so this app is a classic Databricks App. The harness and the verifier are what would make those self-built views trustworthy.
- Why the AI/BI dashboard and not Power BI? No Fabric tenant on a personal account. The dashboard plays Power BI's part: at American it is Power BI on the mirrored catalog, and the parity job keeps the DAX twin honest.
