# The ten-minute walkthrough (five beats)

Audience: a sales director who is "not super technical but very smart," and the hiring manager who built the data. Every
technical thing gets three sentences before any jargon: what the person asks, what they get back, why they can trust it.
Then one layer deeper only if asked. Numbers below are from the local build; re-check them against the live app the night before.

**0:00 The question (one minute).** "An account manager at my current company asks me the same thing yours ask you: why is
Summit's share down on Dallas to Chicago, and what does their contract say about it? Today that is a ticket, a query, and a
few days. I built a small version of what I think your global sales agent should be, on public airline seat data, with made-up
agencies on top. Five screens, one Monday."

**1:00 Monday (two minutes).** Open Monday, Central region, September. Build the summary. Point at the badges: "every number
has a green badge; click one and you get the query and the row it came from." Scroll to the red box: "this sentence the model
wrote on its own; no query supports it, so it never reaches the VP. A person still presses send." If the draft is clean that
day, switch the writer to the unguarded prompt and build again, saying what you are doing: "I loosened the prompt on purpose
to show what the guard catches." Do not fake it; show the runs table with the flagged count per run.

**3:00 Why (two minutes).** Harbor Business Travel, August: revenue 386K, down 15.5%. "The agency sold more travel overall,
plus 8.8%, so it is not volume. AA share went from 45.6% to 35.4%; that is 110K of the 71K drop, offset by 40K of volume.
Fair share barely moved, 39.5% to 39.9%, so AA did not lose capacity: the agency moved share to other carriers, mostly on
DCA-BOS, LAX-JFK and DFW-DCA. The three parts sum to the total; that is arithmetic in the warehouse, not a model." Then the
one line it will not say: "Could not verify whether they changed a preferred-carrier setting; not in the data."

**5:00 Ask (two and a half minutes).** Three questions, in this order. Summit on DFW to ORD, Q3 2026 vs Q3 2025: revenue
$221K to $298K, AA share 46.3% to 53.5%, fair share flat at 37.7%, so the share gap went from 8.6 to 15.9 points; Genie wrote
the MEASURE() query against the metric view and it sits in the drawer. The contract question: clause 5.1 quoted with file and
page (below 45% for two consecutive quarters), and the quarterly shares from 45.1% to 52.6% showing it has not happened. Then
"which agencies are about to churn": it refuses, explains there is no churn label, and offers a labeled proxy. "Unknown is an
allowed answer. That is the difference between a demo and something you can put in front of a VP." If Wi-Fi fails, the three
answers are cached from a real run (the page says so).

**7:30 Definitions and parity (one and a half minutes).** Pick AA share. "Written once in English; this is the Databricks
metric view the agent and Genie use; this is the Power BI measure; a nightly job computes both and shows red where they
disagree." The runs table shows three runs: 1,500 checks green, then the retired passenger-based twin red on all 250 months of
AA share, then green again after the fix. "When your VP asks why two numbers differ, this page answers before the meeting."

**9:00 Under the hood (one minute, then stop).** The diagram. "Three layers. Data: bronze, silver, gold in Databricks. Definitions:
one metric view. Agent: Genie for the numbers, a decomposition for why, the agreements for terms, a harness that picks the tool
and a verifier that refuses to show a number no query returned. The harness is the same code on my laptop and in Foundry.
Twenty benchmark questions with known answers: Genie passed 14 the first time, 19 after two trusted examples and a column it kept
asking for, all 20 on the third run; every run is logged." Open the MLflow experiment: one trace per answer, model calls and tool calls in order.
At American the same shape: your gold layer from the migration, metric views for your KPIs, Genie agents per domain, the
harness in Foundry or Copilot Studio so it lives in Teams, and the agency version runs with each agency's identity. The first
six months are the data and the definitions. This is what month seven looks like."

**10:00 Stop.** "What would you want it to answer that it doesn't?"

## The three-beat version (if the slot is five minutes)

Monday (badges and the red box), Ask (the first and the third question), the diagram. Skip Why and Definitions; mention each in one sentence.

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
