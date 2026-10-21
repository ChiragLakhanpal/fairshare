// The deck's slides in the order a talk walks them: the welcome and the agenda, the five topics, the thanks, and then the backup slides,
// which the notes window's outline reaches. A slide's part is open (the welcome and the agenda), one of the five topics, close (the thanks)
// or backup. min is a slide's minutes on the main path, short its minutes on the short path (only the slides on it have one). Assets and
// thumbs are keys of images and pages in assets.ts; the thumb is the PNG under a live or animated frame. Every number is a {placeholder}
// that SlideView fills from facts.json, and deck.test.ts holds every string here to the content rules. A still is a screenshot of the app
// with its own top bar, so it gets no frame at all. A note is what the speaker says on the slide, under 40 words and in the way he talks;
// the notes window fills in its numbers.
import type { Slide } from "../lib/deck";

/** Names of things that exist today. A tile tagged "Possibility" names none of them. */
export const BUILT = ["Foundry writer", "hosted agent", "Genie", "metric view", "MLflow", "Delegate", "verifier", "harness", "Databricks App", "AI/BI dashboard", "nightly job", "CRM stand-in"];

/** The report that explains the whole project. The start slide links to it once it is published. */
export const REPORT_URL: string | null = null;

export const slides: Slide[] = [
  // The welcome and the agenda
  {
    id: "welcome", part: "open", kind: "live", title: "Fairshare: sales answers you can check", min: 0.5, short: 0.5,
    asset: "hairline/title-b-airliner.html", thumb: "hairline/png/title-b.png",
    byline: ["Chirag Lakhanpal", "Analyst/Sr Analyst, Sales AI & Innovation", "Every number in this talk comes from made-up data."],
    note: "Name and one line on me. Before anyone asks, all the data here is made up, the agencies, the sales, the contracts, the seats and so on. Then the plan for today.",
  },
  {
    id: "agenda", part: "open", kind: "native", title: "From two slow steps to starting at AA", min: 0.5, short: 0.5,
    native: { layout: "agenda" },
    note: "Here's the plan, a press for each part. Stop me anywhere, I'd rather take questions as we go. First, what I heard in round one.",
  },

  // 1. Two slow steps
  {
    id: "problem", part: "steps", kind: "native", title: "Two slow steps today", min: 1, short: 1,
    native: {
      layout: "statement",
      lines: [
        "A share question becomes a ticket to sales BI, and the answer can take days.",
        "Account managers build each pre-call pack by hand, one agency at a time.",
      ],
      ask: "How long does a pack take your team today?",
    },
    note: "So there are two slow steps, a share question turns into a ticket to sales BI, and account managers build pre-call packs by hand. Ask the sales director how long a pack takes today. Then what I built.",
  },

  // 2. Ask and Delegate: Ask live and what happened behind its answer, then Delegate live
  {
    id: "what", part: "modes", kind: "native", title: "An app that answers sales questions with numbers you can check", min: 0.5, short: 0.5,
    native: {
      layout: "tiles",
      tiles: [
        { head: "Ask", body: "Ask a question in plain words. Every number in the answer comes from a query, and one click shows its rows." },
        { head: "Delegate", body: "Agents draft the routine pages overnight, like the Monday pre-call pack. A person approves each page before anything goes out." },
      ],
    },
    note: "It's one app with two modes. In Ask you type a question in plain words, and every number links to its query. Delegate drafts routine pages overnight for a person to approve. I'd like to show you Ask live.",
  },
  {
    id: "query-opener", part: "modes", kind: "live", title: "It starts with a question", min: 0.25,
    asset: "hairline/opener-query.html", thumb: "hairline/png/query.png",
    note: "It starts with a question, the kind that comes up in a Monday sales meeting. Let it play a few seconds, then ask it live.",
  },
  {
    id: "ask", part: "modes", kind: "native", title: "A live question in Ask", min: 3.5, short: 2.5,
    native: {
      layout: "demo",
      demo: { kind: "ask", question: "Why is Harbor Business Travel down in September?" },
      lines: [
        "It splits the drop into volume, route mix and share.",
        "Click the share effect to see the rows behind it.",
        "The app matches every number to a query before you see it.",
      ],
    },
    note: "Click Ask it live, click the box, Enter, talk through the steps. Click the share effect, {harbor_share_usd}. Fair share is made up. A removed sentence likely had a rounded dollar figure. Past a minute, the still. Back: sidebar.",
  },
  {
    id: "director", part: "modes", kind: "animated", title: "Sales director: a question in the Monday meeting", min: 1.25, data: true,
    asset: "04-journey-sales-director-animated.html", thumb: "export/04-journey-sales-director.png",
    note: "Behind that answer, one press per step. Genie ran the query as me, SQL split the change, the model wrote only the words, and the verifier checked every number. That's Ask. Now the other mode.",
  },
  {
    id: "riffle-opener", part: "modes", kind: "live", title: "Pages wait for a person to decide", min: 0.25,
    asset: "hairline/opener-riffle.html", thumb: "hairline/png/riffle.png",
    note: "The other mode is Delegate, where pages wait for a person to decide. Let it play, then how the agents work.",
  },
  {
    id: "delegate", part: "modes", kind: "image", title: "Agents draft, people decide", min: 1.25,
    asset: "export/03-delegate.png",
    note: "Every night the job runs four agents. Fixed queries pull the facts, a Foundry writer drafts from only those, and the verifier checks every number. Nothing is logged or sent until a person approves. Let me open one.",
  },
  {
    id: "precall", part: "modes", kind: "native", title: "The pre-call pack the 6 am job wrote", min: 3, short: 2,
    native: {
      layout: "demo",
      demo: { kind: "precall" },
      lines: [
        "One page per agency, each with a drafted email.",
        "The verifier checked every number on the page against a query.",
        "Nothing is sent or recorded until a person approves it.",
      ],
    },
    note: "Open the pack, pick FareHub Online or Lone Star. Click a number for its rows, then Approve. If asked, fine means {tier_watch_band_pts} or more points from a tier line. Past a minute, the still. Then the layers underneath.",
  },

  // 3. Where the numbers come from: the layers, the data and one row of it, the tests it passes, the seven numbers, why Harbor moved
  {
    id: "stack-opener", part: "numbers", kind: "live", title: "Five layers under every answer", min: 0.25,
    asset: "hairline/stack.html", thumb: "hairline/png/stack.png",
    note: "Now where the numbers come from, and first the five layers under every answer. Let it play, pointing does nothing in the deck. Then the layers one at a time.",
  },
  {
    id: "system", part: "numbers", kind: "animated", title: "The system", min: 2.25, short: 1.5,
    asset: "01-system-exploded-animated.html", thumb: "export/01-system-exploded.png",
    note: "Five layers, one press each. The data's made up, Ask runs on Genie and Qwen3-Next, Delegate on Foundry writers. Blue is the checks, with traces on laptop runs. Now the bottom layer, the data.",
  },
  {
    id: "elevator-opener", part: "numbers", kind: "live", title: "Four floors: as delivered, cleaned, ready to use, and defined once", min: 0.25,
    asset: "hairline/opener-elevator.html", thumb: "hairline/png/elevator.png",
    note: "Four floors, from the files as they came in up to each number defined once. Let it play, then the floors one by one.",
  },
  {
    id: "pipeline", part: "numbers", kind: "animated", title: "Where the numbers come from", min: 1.5, data: true,
    asset: "06-data-pipeline-animated.html", thumb: "export/06-data-pipeline.png",
    note: "Four sources, and the seat shares are made up, one per route. Bronze is as delivered, silver cleaned, gold is {sales_rows} rows, one per agency, route and month. On top, {kpis} numbers, each defined once. Then one actual row.",
  },
  {
    id: "row", part: "numbers", kind: "native", title: "Summit Travel Partners on DFW-ORD in Sep 2026", min: 1,
    native: { layout: "table", tables: ["gold.fact_agency_sales_monthly"], columns: ["aa_revenue", "market_revenue", "aa_pax", "market_pax"] },
    note: "One row of the sales table. AA revenue sits next to everything the agency sold on that route that month, and share is one divided by the other. Then the seats on that route.",
  },
  {
    id: "seats", part: "numbers", kind: "native", title: "AA's seats on DFW-ORD in Sep 2026, made up", min: 1,
    native: { layout: "table", tables: ["gold.fact_market_capacity"], columns: ["aa_seats", "total_seats", "aa_seat_share", "source"] },
    note: "The seats are made up, and the source column even says synthetic. AA's seats over all the seats is the fair share on that route. Next, AA revenue by month.",
  },
  {
    id: "revenue", part: "numbers", kind: "animated", title: "AA revenue by month, 2025 against 2026", min: 0.75, data: true,
    asset: "11-revenue-by-month-animated.html", thumb: "export/11-revenue-by-month.png",
    note: "This year runs ahead of last except March and April, at {yoy_mar26} and {yoy_apr26}, and the axis doesn't start at zero. The dip is Sunbelt missing and Harbor falling. I planted both. Then four tests the rows pass.",
  },
  {
    id: "checks", part: "numbers", kind: "native", title: "Four tests the sales rows pass before every commit", min: 1,
    native: { layout: "checks", keys: ["sales_row_count", "no_repeated_rows", "sales_have_seats", "aa_within_market"] },
    note: "Four of the eight, a press each. The first one's count already leaves out Sunbelt's missing months. They all pass, and the other four are in the backup. Next, the {kpis} numbers.",
  },
  {
    id: "numbers", part: "numbers", kind: "image", title: "The seven numbers", min: 1.75, data: true,
    asset: "export/09-definitions.png",
    note: "Shares are like batting averages, add up hits and at-bats, never average the averages. In Q3 the {agencies} shares average {avg_of_shares_q3}, but the share of the total is {share_of_total_q3}. Ask where AA's fair share differs, mine's made up.",
  },
  {
    id: "share-fair", part: "numbers", kind: "image", title: "AA share against fair share, Q3 2026", min: 1, data: true,
    asset: "export/12-share-vs-fair.png",
    note: "Fair share is about the same for everyone, since they all sell the same routes and the seat shares are made up. Lone Star's on top at {agency_q3_aa_share_lonestar}, FareHub's last at {agency_q3_aa_share_farehub}. Now why Harbor moved.",
  },
  {
    id: "moved", part: "numbers", kind: "animated", title: "Why Harbor moved", min: 1.5, data: true,
    asset: "08-why-it-moved-animated.html", thumb: "export/08-why-it-moved.png",
    note: "Harbor went from {harbor_revenue_sep25_usd} to {harbor_revenue_sep26_usd}. Volume added {harbor_volume_usd}, mix barely moved, and share took {harbor_share_usd}, more than the whole drop. The made-up seat shares would have predicted {harbor_fair_share_effect_usd}, so seats don't explain it. Now how it's checked.",
  },

  // 4. Checks and misses: how an answer gets checked, the guardrails around it, what the tests found, and what it can't do yet
  {
    id: "sieve-opener", part: "checks", kind: "live", title: "Every number passes through the checks", min: 0.25,
    asset: "hairline/opener-sieve.html", thumb: "hairline/png/sieve.png",
    note: "Every number goes through the checks before you see it. Let it play, then how one answer gets checked.",
  },
  {
    id: "checked", part: "checks", kind: "animated", title: "How an answer gets checked", min: 2,
    asset: "02-answer-checked-animated.html", thumb: "export/02-answer-checked.png",
    note: "The verifier is kind of a newspaper fact-checker with the source documents. A sentence whose number no query returned gets cut, and the app shows the cut in red. Then the guardrails around it.",
  },
  {
    id: "guardrails", part: "checks", kind: "native", title: "Four guardrails around Ask and Delegate", min: 1.5,
    native: {
      layout: "tiles",
      tiles: [
        { head: "No data past the viewer's login", body: "Every query runs with the viewer's own login, so Databricks applies that person's permissions." },
        { head: "No math by the model", body: "SQL does all the arithmetic, and the model only writes the sentences." },
        { head: "No instructions from the data", body: "The Delegate writers get a fact sheet and no tools. A writer ignored an instruction planted in a CRM note." },
        { head: "Nothing goes out unapproved", body: "Nothing is recorded in the CRM until a person approves, and the app never sends an email itself." },
      ],
    },
    note: "Four guardrails, a press each, and each head says what it stops. The planted note is the one I'd tell, the writer just ignored it. Then what the tests found.",
  },
  {
    id: "evals", part: "checks", kind: "native", title: "Genie and the whole app on known answers", min: 1, short: 1.5,
    native: {
      layout: "results",
      items: [
        {
          head: "Genie alone",
          body: "Databricks' own judge graded Genie's answers to questions with known answers, column by column, on {genie_benchmark_date}.",
          result: "{genie_benchmark} right",
          miss: "Two earlier runs that day got {genie_benchmark_earlier}, before I reworded five questions to name their columns.",
        },
        {
          head: "The whole app",
          body: "Ask ran the same questions on Qwen3-Next, and gpt-5-mini graded the answers on {app_model_date}.",
          result: "{app_model_right} of {app_model_questions} right",
          miss: "It got {app_model_partly} partly right and {app_model_wrong} wrong. The verifier passed {app_model_gave_up_passed} answer that gave up, since it had no numbers to check.",
        },
      ],
    },
    note: "Genie on its own got {genie_benchmark}, but only after I reworded five questions. The whole app got {app_model_right}, and the miss I'd point at is the answer that gave up and still passed. Then three more.",
  },
  {
    id: "evals-more", part: "checks", kind: "native", title: "The writers, the nightly numbers and every commit", min: 1,
    native: {
      layout: "results",
      items: [
        {
          head: "Foundry's evaluators",
          body: "They graded {foundry_quality_pages} Delegate pages for groundedness on {foundry_eval_date}.",
          result: "All but {foundry_groundedness_misses}",
          miss: "The prompt shield wrongly refused {foundry_shield_refused} pages until I moved the rules into the agents.",
        },
        {
          head: "Nightly comparison",
          body: "The job compared the {twins_checked} numbers with a Power BI version to a SQL copy of it each night, {nightly_parity_from} to {nightly_parity_to}.",
          result: "{nightly_parity_drift} differ",
        },
        {
          head: "The commit check",
          body: "Before every commit, the known-answer queries run and the tests must pass, or the commit stops.",
          result: "All pass",
        },
      ],
    },
    note: "Foundry graded the Delegate pages, and its prompt shield tripped on my rules until I moved them. The nightly job, {nightly_parity_runs} runs, {nightly_parity_drift} differences. Nothing gets committed unless the tests pass. Then the limits.",
  },
  {
    id: "limits", part: "checks", kind: "native", title: "What it does not do yet", min: 1,
    native: {
      layout: "statement",
      lines: [
        "It does not flag a single corporate's drop yet. It can still answer a question about one.",
        "The seat shares are made up, one per route. The T-100 loader has never run.",
        "The goals are made up and soft, so pace works as a ranking more than a grade.",
        "An account manager cannot mark an answer as wrong yet.",
        "Ask runs inside the App. A version that runs as a Foundry hosted agent is built but not deployed.",
      ],
    },
    note: "The biggest one is that it doesn't flag a single corporate's drop yet, though you can ask about one. The Foundry writers run today, and Ask as a hosted agent is built but not deployed. Then, at AA.",
  },

  // 5. Starting at AA: the same layers on AA's own data, the possibilities on Azure, the first four steps and how we'd know
  {
    id: "at-aa", part: "aa", kind: "image", title: "The same layers at AA", min: 1.5,
    asset: "export/15-at-aa.png",
    note: "At AA it's the same layers, each made-up table next to the feed that would replace it. The hardest is the agency's sales on other airlines, since AA only sees its own. The Microsoft pieces wait on AA's account.",
  },
  {
    id: "azure", part: "aa", kind: "native", title: "Possibilities on Azure", min: 0.75,
    native: {
      layout: "tiles",
      tiles: [
        { head: "Fabric and OneLake", body: "The app would read AA's own sales tables where they already sit, without copying them.", tag: "Possibility" },
        { head: "Dataverse mirror", body: "Dynamics 365 Sales contacts, deals and activities would replace the made-up CRM tables.", tag: "Possibility" },
        { head: "Teams through Copilot Studio", body: "Account managers would ask the same questions in Teams, where they already work.", tag: "Possibility" },
        { head: "Entra ID sign-in", body: "Each person would sign in with their AA account and see only the agencies they cover.", tag: "Possibility" },
      ],
    },
    note: "Each of these is a possibility, tagged that way, and they all wait on AA's own Microsoft account. Teams would put the same questions where account managers already work. Then how I'd start.",
  },
  {
    id: "start", part: "aa", kind: "native", title: "How I would start at AA", min: 1, short: 1,
    native: {
      layout: "statement",
      lines: [
        "Time today's work first: how long a pre-call pack takes, and how many share questions become tickets.",
        "Swap the made-up seat shares for AA's own in the one capacity table. Every number that uses fair share reads it, so that is one change.",
        "Connect AA's own agency sales, and match each number to the reports people use now.",
        "Give account managers a way to mark an answer as wrong, and read every one.",
      ],
    },
    note: "First I'd time today's work, so there's a before. Then I'd swap my made-up seat shares for AA's own in one table, connect AA's agency sales, and add a way to flag a wrong answer. Then, how we'd know.",
  },
  {
    id: "know", part: "aa", kind: "native", title: "How we would know it worked", min: 1,
    native: {
      layout: "tiles",
      tiles: [
        { head: "Account managers using it", body: "How many open it each week, and how many come back the next week." },
        { head: "Prep time per call", body: "Minutes to get ready for an agency call, timed before and after." },
        { head: "Tickets to sales BI", body: "How many share questions still arrive as tickets." },
        { head: "Drafts approved with light edits", body: "How often a person approves a page as written or with small changes." },
      ],
    },
    note: "If it works, account managers come back the next week, prep time per call drops, fewer share questions become tickets, and drafts get approved with light edits. I'd time today first. Then I'll stop for questions.",
  },

  // The thanks, up through the questions
  {
    id: "thanks", part: "close", kind: "native", title: "Thank you", min: 0.25, short: 0.25,
    native: { layout: "close", lines: ["Chirag Lakhanpal", "chirag.lakhanpal.cl@gmail.com", "What would you like to ask?"] },
    note: "Thank them, and leave this up through the questions. If one needs a backup, it's in the outline.",
  },

  // Backup, reached from the notes window's outline: the two stills, figures and words for questions, the tables column by column, the rest
  {
    id: "ask-still", part: "backup", kind: "image", still: true, title: "A good run of the Harbor question", min: 0,
    asset: "export/ask-still.png",
    note: "Tell the room it's a still from an earlier run on the App. The numbers are made up. Losing share cost {harbor_share_usd}. Then pick the next slide from the outline.",
  },
  {
    id: "precall-still", part: "backup", kind: "image", still: true, title: "A good run of the pre-call pack", min: 0,
    asset: "export/precall-still.png",
    note: "Say it's a still of a page the nightly job wrote. The numbers are made up. If asked, fine means {tier_watch_band_pts} or more points from a tier line. Then pick the next slide from the outline.",
  },
  {
    id: "manager", part: "backup", kind: "animated", title: "Account manager: Monday before agency calls", min: 0,
    asset: "05-journey-account-manager-animated.html", thumb: "export/05-journey-account-manager.png",
    note: "For when someone asks how an account manager would use it. On Monday the page is already waiting, numbers, reason, clause and email, where today they build it by hand. Approve or reject, the app sends nothing itself.",
  },
  {
    id: "fair", part: "backup", kind: "image", title: "What fair share means", min: 0, data: true,
    asset: "export/07-fair-share.png",
    note: "Fair share is AA's share of the seats, and these seat shares are made up. On DFW-ORD in Q3, Summit sent {summit_q3_aa_share} to AA against {summit_q3_fair_share}, {summit_q3_gap_usd} above fair share. By passengers it's {summit_q3_pax_share}, nearly the same.",
  },
  {
    id: "planted", part: "backup", kind: "image", title: "What I planted, and what cleaning did", min: 0, data: true,
    asset: "export/14-what-was-planted.png",
    note: "Sunbelt is a missing logbook page, Northstar's zero a page saying no flights today. Pace skips missing months, so Sunbelt's May went {sunbelt_pace_may26_before} to {sunbelt_pace_may26} of pace. Harbor's flagged since the CRM still says On track.",
  },
  {
    id: "checks-all", part: "backup", kind: "native", title: "All eight tests on the data", min: 0,
    native: { layout: "checks" },
    note: "All eight, for when someone asks. {sales_rows} rows is {agencies} agencies by {routes} routes by {months} months, minus Sunbelt's {sunbelt_missing_rows} missing. The same tests run before every commit.",
  },
  {
    id: "words", part: "backup", kind: "native", title: "Five words in plain English", min: 0,
    native: {
      layout: "tiles",
      tiles: [
        { head: "Booking", body: "A company's purchase of one or more tickets, with the route, the day and the fare." },
        { head: "Seat", body: "A seat an airline flies on a route in a month. The seat counts here are made up." },
        { head: "Share", body: "AA revenue divided by everything the agency sold on the same routes." },
        { head: "Fair share", body: "AA's share of the seats on those routes: what a neutral agency would send AA. The seat shares here are made up." },
        { head: "Pace", body: "Revenue so far as a percent of the goal so far. Over a hundred is ahead. The goals are made up." },
      ],
    },
    note: "Five words in plain English, for when someone asks what one means. The seat counts and the goals behind fair share and pace are made up.",
  },
  {
    id: "dashboard", part: "backup", kind: "native", title: "The sales dashboard", min: 0,
    native: {
      layout: "demo",
      demo: { kind: "dashboard" },
      lines: [
        "An AI/BI dashboard on the same metric view stands in for Power BI.",
        "It shows pace, share against fair share, and what moved where.",
        "For why a number moved, ask the app.",
      ],
    },
    note: "Click Open the sales dashboard, it opens in a new tab. It reads the same metric view and stands in for Power BI, and fair share on it uses the made-up seats. Close the tab to come back.",
  },
  {
    id: "choices", part: "backup", kind: "native", title: "What I chose, and what I chose against", min: 0,
    native: {
      layout: "tiles",
      tiles: [
        { head: "A metric view, not a table of shares", body: "Share is a ratio. A table of saved shares is wrong the moment someone groups differently." },
        { head: "Genie inside a harness, not alone", body: "Genie answers numbers. The harness adds the agreements, the reasons, the refusals and the verifier." },
        { head: "A verifier before the person", body: "Matching each number to a query result is cheap and exact, so it runs on every answer." },
        { head: "Math in SQL, words in the model", body: "Arithmetic that must add up runs in the warehouse. The model only writes the words." },
        { head: "Running as the viewer, not as the App", body: "Each query runs as the person asking, which is how an agency portal would show each agency only itself." },
        { head: "Benchmarks with known answers", body: "The benchmark questions have known answers. They run again after a prompt or definition change." },
      ],
    },
    note: "For the data lead's questions, each choice next to what I chose against. The big ones are the metric view, since saved shares break when you group differently, and math in SQL with only the words in the model.",
  },
  {
    id: "dict-facts", part: "backup", kind: "native", title: "Agency sales by route and month, every column", min: 0,
    native: { layout: "table", tables: ["gold.fact_agency_sales_monthly"] },
    note: "The sales table in full, for when someone asks. One row per agency, route and month, {sales_rows} rows in all. Share is AA revenue over market revenue.",
  },
  {
    id: "dict-seats", part: "backup", kind: "native", title: "Seats by route and month, every column, made up", min: 0,
    native: { layout: "table", tables: ["gold.fact_market_capacity"] },
    note: "The seat table in full, all made up, one row per route and month. The projected flag would mark a month borrowed from last year, and it's never set here.",
  },
  {
    id: "dict-agencies", part: "backup", kind: "native", title: "The made-up agencies, column by column", min: 0,
    native: { layout: "table", tables: ["gold.dim_agency"] },
    note: "The {agencies} agencies, column by column, for when someone asks. The agency names and account managers are made up too.",
  },
  {
    id: "dict-routes", part: "backup", kind: "native", title: "The routes, column by column", min: 0,
    native: { layout: "table", tables: ["gold.dim_market"] },
    note: "The {routes} routes, column by column. Each route says whether it starts at an AA hub.",
  },
  {
    id: "dict-goals", part: "backup", kind: "native", title: "Each agency's goal for the year", min: 0,
    native: { layout: "table", tables: ["gold.agency_goals"] },
    note: "The goals here are made up and soft, so pace works as a ranking more than a grade.",
  },
  {
    id: "dict-pace", part: "backup", kind: "native", title: "Pace by agency and month", min: 0,
    native: { layout: "table", tables: ["gold.agency_pace"] },
    note: "The goal so far only grows for months an agency reported, which is why Sunbelt's May reads {sunbelt_pace_may26} of pace.",
  },
  {
    id: "dict-agreements", part: "backup", kind: "native", title: "Where each agreement clause comes from", min: 0,
    native: { layout: "table", tables: ["gold.contract_clauses"], columns: ["clause_id", "agency_id", "file", "page", "section", "quote"] },
    note: "The {agreements} agreements, one row per clause. Each row keeps the file, the page and the clause word for word, so an answer can cite the page. The agreements are made up.",
  },
  {
    id: "dict-clause-terms", part: "backup", kind: "native", title: "What each agreement clause measures", min: 0,
    native: { layout: "table", tables: ["gold.contract_clauses"], columns: ["clause_type", "metric", "operator", "threshold", "threshold_2", "window_quarters", "consequence"] },
    note: "The same clauses, by what each one measures. The agreement watch tests every clause it can measure against every month, and marks the rest not checkable.",
  },
  {
    id: "dict-crm", part: "backup", kind: "native", title: "The CRM stand-in's contacts", min: 0,
    native: { layout: "table", tables: ["gold.crm_contacts"] },
    note: "The CRM stand-in for Dynamics 365, contacts first. The names and emails are made up.",
  },
  {
    id: "dict-deals", part: "backup", kind: "native", title: "The CRM stand-in's deals", min: 0,
    native: { layout: "table", tables: ["gold.crm_opportunities"] },
    note: "The deals. The home page compares the health column with the data, which is how Harbor gets flagged: its renewal still says On track while share fell.",
  },
  {
    id: "dict-activities", part: "backup", kind: "native", title: "The CRM stand-in's activities", min: 0,
    native: { layout: "table", tables: ["gold.crm_activities"] },
    note: "The calls, emails and meetings logged with each agency, all made up, for when someone asks what the CRM keeps.",
  },
  {
    id: "dict-bookings", part: "backup", kind: "native", title: "Corporate bookings, ticket by ticket", min: 0,
    native: {
      layout: "table",
      tables: ["gold.fact_corporate_bookings"],
      columns: ["ticket_number", "corp_id", "booking_date", "travel_date", "origin", "dest", "channel", "fare_usd", "ticket_count", "cabin", "agency_id"],
    },
    note: "Corporate bookings, all made up. Cleaning took {channel_spellings_delivered} channel spellings down to {channel_spellings_cleaned} and dropped {duplicate_tickets} tickets loaded twice. It doesn't flag a single corporate's drop yet, though you can ask about one.",
  },
  {
    id: "dict-corporates", part: "backup", kind: "native", title: "The companies that book, made up", min: 0,
    native: { layout: "table", tables: ["gold.dim_corporate"] },
    note: "The companies behind those bookings, each with its contract dates and yearly commitment, all made up.",
  },
  {
    id: "dict-ops", part: "backup", kind: "native", title: "Why Harbor's September moved, in one row", min: 0,
    native: {
      layout: "table",
      tables: ["ops.decomposition"],
      columns: ["revenue_now", "revenue_prior", "delta_revenue", "volume_effect", "mix_effect", "share_effect", "fair_share_effect", "residual"],
    },
    note: "The decomposition row for Harbor's September. Volume, mix and share add up to the change exactly, so nothing is left over.",
  },
  {
    id: "dict-kpis", part: "backup", kind: "native", title: "How AA share is defined, in one row", min: 0,
    native: { layout: "table", tables: ["ops.kpi_definitions"], columns: ["kpi", "display_name", "definition_en", "owner", "source_columns", "metric_view_expr"] },
    note: "Each of the {kpis} numbers has a row like this one, AA share here. The expression is the one in the metric view that Genie and the dashboard read.",
  },
  {
    id: "dict-twins", part: "backup", kind: "native", title: "AA share as a Power BI measure, and its SQL copy", min: 0,
    native: { layout: "table", tables: ["ops.kpi_definitions"], columns: ["dax_twin", "twin_sql", "twin_version", "twin_sql_retired", "retired_note"] },
    note: "My first SQL twin for AA share counted passengers, and all {parity_rows} agency-months came back red. The retired copy and the reason stay in the row.",
  },
  {
    id: "security", part: "backup", kind: "native", title: "The viewer's login and the App's keys", min: 0,
    native: {
      layout: "tiles",
      tiles: [
        { head: "Runs as the viewer", body: "Genie and every query run with the viewer's own token, never the App's service principal." },
        { head: "Secrets stay out of the code", body: "Keys live in a file git ignores on the laptop, and in a Databricks secret scope for the job and the App." },
      ],
    },
    note: "If it comes up. Genie and every query run with the viewer's token, never the App's own identity. Keys sit in a file git ignores, and in a Databricks secret scope for the job and the App.",
  },
  {
    id: "foundry-eval", part: "backup", kind: "native", title: "Foundry's evaluators on the four writers: the {foundry_eval_date} runs", min: 0,
    native: {
      layout: "tiles",
      tiles: [
        { head: "One nightly run", body: "The four Foundry writers wrote {foundry_nightly_pages} pages, and the verifier checked every sentence." },
        { head: "Quality", body: "Every normal page passed relevance, coherence, fluency and the content harm checks." },
        { head: "The indirect attack check", body: "It flagged the planted instruction, and also {foundry_attack_false_flags} of {foundry_attack_notes} normal CRM correction notes." },
        { head: "Speed", body: "A clean page took {foundry_clean_page_s} seconds. The guardrail refused a jailbreak at the prompt in {foundry_refusal_s} seconds." },
      ],
    },
    note: "How the writers were tested, past what the evals slide says. The attack check flagged the planted instruction and {foundry_attack_false_flags} normal notes too. A clean page took {foundry_clean_page_s} seconds.",
  },
  {
    id: "agents", part: "backup", kind: "native", title: "Four agents on one runtime", min: 0,
    native: {
      layout: "tiles",
      tiles: [
        { head: "Pre-call pack", body: "One page per agency an account manager owns, with a drafted email." },
        { head: "Agreement watch", body: "Every clause it can measure, checked against the month, with a drafted notice or upsell." },
        { head: "Prospect research", body: "Where the headroom is on a route, with public sources quoted and linked." },
        { head: "CRM versus reality", body: "Open deals whose health in the CRM disagrees with the data, with a drafted correction." },
        { head: "What they share", body: "Each runs fixed queries, hands the facts to a writer with no tools, checks every sentence and waits for a person to approve." },
      ],
    },
    note: "There are four agents on one runtime, and each one runs fixed queries, hands the facts to a writer with no tools, checks every sentence, and waits for a person to approve.",
  },
  {
    id: "platform", part: "backup", kind: "native", title: "Free Edition limits", min: 0,
    native: {
      layout: "tiles",
      tiles: [
        { head: "The warehouse sleeps", body: "It stops after ten idle minutes, and Free Edition locks that setting. A keep-warm script runs during a demo." },
        { head: "The App stops after a day", body: "An App stops a day after it starts or deploys, so I start it before a demo." },
        { head: "No App Builder", body: "Genie's App Builder needs preview settings this workspace does not have." },
      ],
    },
    note: "Free Edition limits, if asked. The warehouse sleeps when idle, so a keep-warm script runs during a demo, and the App stops a day after it starts, so I start it before. There's no App Builder.",
  },
];
