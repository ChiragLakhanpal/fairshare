// The deck's slides in the order a talk walks them: the welcome and the agenda, the five topics, the thanks, and then the backup slides,
// which the notes window's outline reaches. A slide's part is open (the welcome and the agenda), one of the five topics, close (the thanks)
// or backup. min is a slide's minutes on the main path, short its minutes on the short path (only the slides on it have one). Assets and
// thumbs are keys of images and pages in assets.ts; the thumb is the PNG under a live or animated frame. Every number is a {placeholder}
// that SlideView fills from facts.json, and deck.test.ts holds every string here to the content rules and the copy rules. A still is a
// screenshot of the app with its own top bar, so it gets no frame at all. A note is what the speaker says on the slide, under 40 words and
// in the way he talks: its point, the number to say, where the presses fall, and a handoff that reads right on either path, since the
// notes window shows the same note on both. The notes window fills in its numbers.
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
    byline: ["Chirag Lakhanpal", "Analyst/Sr Analyst, Sales AI & Innovation", "The agencies and their sales are made up, and the seats are real T-100 data."],
    note: "Say my name and one line about me. Before anyone asks, the agencies, their sales, the contracts and the CRM are made up, and the seats are real T-100 data. Then I walk through the plan.",
  },
  {
    id: "agenda", part: "open", kind: "native", title: "Share questions and pre-call packs, in five parts", min: 0.5, short: 0.5,
    native: { layout: "agenda" },
    note: "Here's the plan, five parts, a press each. Stop me anywhere, I'd rather take questions as we go. First is what I heard in round one.",
  },

  // 1. Two slow steps
  {
    id: "problem", part: "steps", kind: "native", title: "Two slow steps I heard about in round one", min: 1, short: 1,
    native: {
      layout: "statement",
      lines: [
        "A share question becomes a ticket to sales BI, and the answer can take days.",
        "Account managers build each pre-call pack by hand, one agency at a time.",
      ],
      ask: "How long does a pack take your team today?",
    },
    note: "A press each. A share question turns into a ticket to sales BI, and account managers build every pre-call pack by hand. Third press, ask the sales director how long a pack takes. Then what I built.",
  },

  // 2. Ask and Delegate: Ask live and what happened behind its answer, then Delegate live
  {
    id: "what", part: "modes", kind: "native", title: "One app with a mode for each slow step", min: 0.5, short: 0.5,
    native: {
      layout: "tiles",
      tiles: [
        { head: "Ask", body: "Ask a question in plain words. Every number in the answer comes from a query, and one click shows its rows." },
        { head: "Delegate", body: "Agents draft the routine pages at 6 am, like the Monday pre-call pack. A person approves each page before anything goes out." },
      ],
    },
    note: "One app, two modes, a press each. In Ask you type a question, and every number links to its query. Delegate drafts routine pages at 6 am for a person to approve. Let me show you Ask live.",
  },
  {
    id: "query-opener", part: "modes", kind: "live", title: "Before the live Harbor question", min: 0.25,
    asset: "hairline/opener-query.html", thumb: "hairline/png/query.png",
    note: "It starts with a question, the kind that comes up in a Monday sales meeting. Let it play a few seconds, then ask it live.",
  },
  {
    id: "ask", part: "modes", kind: "native", title: "Asking about Harbor's September, live", min: 3.5, short: 2.5,
    native: {
      layout: "demo",
      demo: { kind: "ask", question: "Why is Harbor Business Travel down in September?" },
      lines: [
        "It splits the drop into volume, the shift between routes, and AA's share.",
        "One click on the share effect shows the rows behind it.",
        "The app matches every number to a query before you see it.",
      ],
    },
    note: "Three presses, then Ask it live, the box, Enter. Click the share effect, {harbor_share_usd}. The breakdown says September's seats are last year's. Past a minute, use the still. Back through the sidebar, then behind the answer if there's time.",
  },
  {
    id: "director", part: "modes", kind: "animated", title: "What ran behind the Harbor answer", min: 1.25, data: true,
    asset: "04-journey-sales-director-animated.html", thumb: "export/04-journey-sales-director.png",
    note: "That same answer takes seven presses. Genie runs the query as the viewer, SQL splits the change, the model only writes the words, and the verifier checks every number. Next is the other mode, Delegate.",
  },
  {
    id: "riffle-opener", part: "modes", kind: "live", title: "Delegate's pages wait for an account manager", min: 0.25,
    asset: "hairline/opener-riffle.html", thumb: "hairline/png/riffle.png",
    note: "The other mode is Delegate, where the pages wait for an account manager to decide. Let it play a few seconds, then how the agents work.",
  },
  {
    id: "delegate", part: "modes", kind: "animated", title: "What the 6 am job does before anyone decides", min: 1.25,
    asset: "03-delegate-animated.html", thumb: "export/03-delegate.png",
    note: "Six presses. At 6 am three agents run, SQL pulls the facts, a Foundry writer drafts from them, and the verifier checks every number. Nothing reaches the CRM or Outlook until a person approves. Let me open one.",
  },
  {
    id: "precall", part: "modes", kind: "native", title: "The pre-call pack the 6 am job wrote", min: 3, short: 2,
    native: {
      layout: "demo",
      demo: { kind: "precall" },
      lines: [
        "The pack has one page per agency, each with a drafted email.",
        "The verifier checked every number on the page against a query.",
        "Approving logs the activity in the CRM stand-in and opens the email, which the account manager sends.",
      ],
    },
    note: "Three presses, then open the pack and pick FareHub or Lone Star. Click a number for its rows, then Approve. Fine means {tier_watch_band_pts} or more points from a tier line. Past a minute, use the still. Then the layers.",
  },

  // 3. Where the numbers come from: the layers, the data and one row of it, the tests it passes, the seven numbers, why Harbor fell
  {
    id: "stack-opener", part: "numbers", kind: "live", title: "The five layers under Ask and Delegate", min: 0.25,
    asset: "hairline/stack.html", thumb: "hairline/png/stack.png",
    note: "Now where the numbers come from, and first the five layers under every answer. Let it play a few seconds, then the layers one at a time.",
  },
  {
    id: "system", part: "numbers", kind: "animated", title: "Fairshare's five layers, with the checks in blue", min: 2.25, short: 1.5,
    asset: "01-system-exploded-animated.html", thumb: "export/01-system-exploded.png",
    note: "A press per layer from the top, and blue is the checks. Ask runs on Genie and Qwen3-Next, Delegate's writers run in Foundry, and only the seats are real. Then where the data comes from, if there's time.",
  },
  {
    id: "elevator-opener", part: "numbers", kind: "live", title: "Four floors under the seven numbers", min: 0.25,
    asset: "hairline/opener-elevator.html", thumb: "hairline/png/elevator.png",
    note: "There are four floors, the files as they came in, cleaned, ready to use, and each number defined once at the top. Let it play, then the floors one by one.",
  },
  {
    id: "pipeline", part: "numbers", kind: "animated", title: "Where the seven numbers come from", min: 1.5, data: true,
    asset: "06-data-pipeline-animated.html", thumb: "export/06-data-pipeline.png",
    note: "Four sources come first, and only the seats are real. Then a press each for bronze as delivered, silver cleaned, gold at {sales_rows} rows, the {kpis} numbers, who reads them, and Unity Catalog. Next, one actual row.",
  },
  {
    id: "row", part: "numbers", kind: "native", title: "Summit Travel Partners on DFW-ORD in Sep 2026", min: 1,
    native: { layout: "table", tables: ["gold.fact_agency_sales_monthly"], columns: ["aa_revenue", "market_revenue", "aa_pax", "market_pax"] },
    note: "One press brings in Summit's row of the sales table. AA revenue is beside everything Summit sold on that route that month, and AA share is one over the other. Next are the seats on that route.",
  },
  {
    id: "seats", part: "numbers", kind: "native", title: "AA's seats on DFW-ORD in Jul 2026, from T-100", min: 1,
    native: { layout: "table", tables: ["gold.fact_market_capacity"], columns: ["aa_seats", "total_seats", "aa_seat_share", "source"] },
    note: "One press brings in July's row, the newest month the DOT has published, and its source column names T-100. AA's seats over all the seats is the fair share on that route. Next is AA revenue by month.",
  },
  {
    id: "revenue", part: "numbers", kind: "animated", title: "AA revenue by month, and the March and April dip", min: 0.75, data: true,
    asset: "11-revenue-by-month-animated.html", thumb: "export/11-revenue-by-month.png",
    note: "This year beats last except March and April, {yoy_mar26} and {yoy_apr26}, and the axis starts above zero. Then a press each, Sunbelt sent nothing, Harbor fell, and the other agencies grew in total. Next, four tests the rows pass.",
  },
  {
    id: "checks", part: "numbers", kind: "native", title: "Four tests the sales rows pass before every commit", min: 1,
    native: { layout: "checks", keys: ["sales_row_count", "no_repeated_rows", "sales_have_seats", "aa_within_market"] },
    note: "Four of the eight, a press each, and every one passes. The row count already takes out Sunbelt's {sunbelt_missing_rows} missing rows, and the other four are in the backup. Next, what goes into each of the {kpis} numbers.",
  },
  {
    id: "numbers", part: "numbers", kind: "animated", title: "Three of the seven numbers, and what goes into each", min: 1, data: true,
    asset: "09a-numbers-share-animated.html", thumb: "export/09a-numbers-share.png",
    note: "A press each, Harbor's September is the example, and September's seats are last year's. Last press, shares are worked out per query, since averaging the agencies' Q3 shares gives {avg_of_shares_q3}, not the true {share_of_total_q3}. Then the other four.",
  },
  {
    id: "gaps", part: "numbers", kind: "animated", title: "The other four numbers, and what goes into each", min: 1, data: true,
    asset: "09b-numbers-gaps-animated.html", thumb: "export/09b-numbers-gaps.png",
    note: "The other four, a press each. Harbor's gap is {harbor_gap_pts_sep26} points, or {harbor_gap_usd_sep26}, on last year's seats, and revenue is {harbor_yoy_sep26} on last September. Pace counts only reported months. Last, where they're defined. Then every agency against fair share.",
  },
  {
    id: "share-fair", part: "numbers", kind: "animated", title: "AA share against fair share, Q3 2026", min: 1, data: true,
    asset: "12-share-vs-fair-animated.html", thumb: "export/12-share-vs-fair.png",
    note: "Fair share first, then why it barely moves, since every agency spreads its sales over the same routes in similar proportions. Then AA share, Lone Star on top at {agency_q3_aa_share_lonestar}, FareHub last at {agency_q3_aa_share_farehub}. Then why Harbor fell.",
  },
  {
    id: "moved", part: "numbers", kind: "animated", title: "Why Harbor fell in September", min: 1.5, data: true,
    asset: "08-why-it-moved-animated.html", thumb: "export/08-why-it-moved.png",
    note: "A press per bar, from {harbor_revenue_sep25_usd} to {harbor_revenue_sep26_usd}. Volume added {harbor_volume_usd}, the shift between routes barely moved it, and share was {harbor_share_usd}, more than the whole drop. Seats predict {harbor_fair_share_effect_usd}, since September's seats are last year's. Then the checks.",
  },

  // 4. Checks and misses: how an answer gets checked, the guardrails around it, what the tests found, and what it can't do yet
  {
    id: "sieve-opener", part: "checks", kind: "live", title: "Checks on every number in Ask and Delegate", min: 0.25,
    asset: "hairline/opener-sieve.html", thumb: "hairline/png/sieve.png",
    note: "Every number goes through the checks before anyone sees it. Let it play a few seconds, then how one answer gets checked.",
  },
  {
    id: "checked", part: "checks", kind: "animated", title: "How the verifier checks an Ask answer", min: 2,
    asset: "02-answer-checked-animated.html", thumb: "export/02-answer-checked.png",
    note: "The account manager asks, the app holds the answer back, and the verifier cuts any sentence whose number no query returned, and the app shows the cut in red. Last press, the foundations under it. Then the guardrails.",
  },
  {
    id: "guardrails", part: "checks", kind: "native", title: "Four guardrails around Ask and Delegate", min: 1.5,
    native: {
      layout: "tiles",
      tiles: [
        { head: "No data past the viewer's login", body: "Every query runs with the viewer's own login, so Databricks applies that person's permissions." },
        { head: "No math by the model", body: "SQL does all the arithmetic, and the model only writes the sentences." },
        { head: "No instructions from the data", body: "The Delegate writers get a fact sheet and no tools. A writer ignored an instruction I planted in a CRM note." },
        { head: "Nothing goes out unapproved", body: "The app records nothing in the CRM until a person approves, and it never sends an email itself." },
      ],
    },
    note: "Four guardrails, a press each, and each head says what it stops. When the third comes in, tell how a writer ignored the instruction I planted in a CRM note. Then what the tests found.",
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
    note: "Genie alone got {genie_benchmark} after I reworded five questions. Next press, the app got {app_model_right} of {app_model_questions}, and the miss I'd point at is the answer that gave up and still passed. Then three more tests, if there's time.",
  },
  {
    id: "evals-more", part: "checks", kind: "native", title: "Foundry's evaluators, the 6 am job and every commit", min: 1,
    native: {
      layout: "results",
      items: [
        {
          head: "Foundry's evaluators",
          body: "They graded {foundry_quality_pages} Delegate pages for groundedness on {foundry_eval_date}.",
          result: "All but {foundry_groundedness_misses}",
          miss: "The prompt shield refused {foundry_shield_refused} legitimate pages until I moved the rules into the agents.",
        },
        {
          head: "The 6 am comparison",
          body: "From {nightly_parity_from} to {nightly_parity_to}, the job compared the metric view's numbers with a SQL copy of each Power BI measure.",
          result: "All {twins_checked} match",
        },
        {
          head: "The commit check",
          body: "Before each commit, a hook runs the SQL behind every known answer and the Python tests, and any failure stops the commit.",
          result: "All pass",
        },
      ],
    },
    note: "A press each. Foundry's prompt shield refused pages that carried my rules until I moved them into the agents. The 6 am comparison ran {nightly_parity_runs} times with {nightly_parity_drift} differences, and a failing test stops any commit. Then the limits.",
  },
  {
    id: "limits", part: "checks", kind: "native", title: "What Fairshare can't do yet", min: 1,
    native: {
      layout: "statement",
      lines: [
        "It does not flag a single corporate's drop yet.",
        "The two newest months of seats are last year's until the DOT publishes.",
        "The goals are made up and soft, so pace is a ranking more than a grade.",
        "An account manager cannot mark an answer as wrong yet.",
        "Ask as a Foundry hosted agent is built but not deployed.",
      ],
    },
    note: "Five limits, a press each. When the first comes in, stress that it doesn't flag a single corporate's drop yet, though you can ask about one. The Foundry writers do run today. Then the same layers at AA.",
  },

  // 5. Starting at AA: the same layers on AA's own data, the possibilities on Azure, the first four steps and how we'd know
  {
    id: "at-aa", part: "aa", kind: "animated", title: "Fairshare's layers at AA, and the feeds they'd need", min: 1.5,
    asset: "15-at-aa-animated.html", thumb: "export/15-at-aa.png",
    note: "Three presses mark what runs today, what's built but not deployed, and what waits on AA's Microsoft account. Then the feeds, hardest first, the agency's sales on other airlines, since AA only sees its own. Then the Azure pieces.",
  },
  {
    id: "azure", part: "aa", kind: "native", title: "What waits on AA's Microsoft account", min: 0.75,
    native: {
      layout: "tiles",
      tiles: [
        { head: "Fabric and OneLake", body: "The app would read AA's own sales tables in place, without copying them.", tag: "Possibility" },
        { head: "Dataverse mirror", body: "Dynamics 365 Sales contacts, deals and activities would replace the made-up CRM tables.", tag: "Possibility" },
        { head: "Teams through Copilot Studio", body: "Account managers would ask the same questions in Teams, where they already work.", tag: "Possibility" },
        { head: "Entra ID sign-in", body: "Each person would sign in with their AA account and see only the agencies they cover.", tag: "Possibility" },
      ],
    },
    note: "Four possibilities, a press each, and none of them is built, they all wait on AA's Microsoft account. With Teams, account managers would ask the same questions where they already work. Then how I'd start.",
  },
  {
    id: "start", part: "aa", kind: "native", title: "Bringing Fairshare to AA, in four steps", min: 1, short: 1,
    native: {
      layout: "statement",
      lines: [
        "Time today's work first: how long a pre-call pack takes, and how many share questions become tickets.",
        "Add AA's own schedule to the one seat table that fair share reads, for the newest months and the partner flights T-100 leaves out.",
        "Connect AA's own agency sales, and match each number to the reports people use now.",
        "Give account managers a way to mark an answer as wrong, and read every one.",
      ],
    },
    note: "First I'd time today's work, so there's a before, then a press each for AA's own schedule, AA's agency sales and a way to flag a wrong answer. Then how we'd know it worked, if there's time.",
  },
  {
    id: "know", part: "aa", kind: "native", title: "How AA would know Fairshare worked", min: 1,
    native: {
      layout: "tiles",
      tiles: [
        { head: "Account managers using it", body: "How many open it each week, and how many come back the next week." },
        { head: "Prep time per call", body: "Minutes to get ready for an agency call, timed before and after." },
        { head: "Tickets to sales BI", body: "How many share questions still arrive as tickets." },
        { head: "Drafts approved with small edits", body: "How often a person approves a page as written or with small edits." },
      ],
    },
    note: "A press each. If it works, account managers come back the next week, prep time per call drops, fewer share questions turn into tickets, and people approve drafts with small edits. That's why I'd time today first. Then questions.",
  },

  // The thanks, up through the questions
  {
    id: "thanks", part: "close", kind: "native", title: "Thank you", min: 0.25, short: 0.25,
    native: { layout: "close", lines: ["Chirag Lakhanpal", "chirag.lakhanpal.cl@gmail.com", "What would you like to ask?"] },
    note: "Thank them and leave this up through the questions. If a question needs a backup slide, it's in the outline.",
  },

  // Backup, reached from the notes window's outline: the two stills, figures and words for questions, the tables column by column, the rest
  {
    id: "ask-still", part: "backup", kind: "image", still: true, title: "A good run of the Harbor question", min: 0,
    asset: "export/ask-still.png",
    note: "Say it's a still from before the T-100 seats, with made-up sales, so its fair share is out of date. The share effect is {harbor_share_usd}, more than the whole drop. Then pick the next slide from the outline.",
  },
  {
    id: "precall-still", part: "backup", kind: "image", still: true, title: "A good run of the pre-call pack", min: 0,
    asset: "export/precall-still.png",
    note: "Say it's a still from the 6 am job, before the T-100 seats, so its fair share is out of date. Fine means {tier_watch_band_pts} or more points from a tier line. Then pick the next slide from the outline.",
  },
  {
    id: "manager", part: "backup", kind: "animated", title: "An account manager's Monday before agency calls", min: 0,
    asset: "05-journey-account-manager-animated.html", thumb: "export/05-journey-account-manager.png",
    note: "For when someone asks how an account manager would use it, a press per step. On Monday the page is already waiting with the numbers, the reason, the clause and the email, where today they build it by hand.",
  },
  {
    id: "fair", part: "backup", kind: "image", title: "Summit's fair share on DFW-ORD in Q3", min: 0, data: true,
    asset: "export/07-fair-share.png",
    note: "Fair share is AA's share of the seats, from T-100, and August and September repeat last year. On DFW-ORD in Q3, Summit sent {summit_q3_aa_share} to AA against {summit_q3_fair_share}, below fair share. By passengers it's {summit_q3_pax_share}, nearly the same.",
  },
  {
    id: "planted", part: "backup", kind: "image", title: "What I planted, and what cleaning did", min: 0, data: true,
    asset: "export/14-what-was-planted.png",
    note: "Sunbelt's missing months never came in, and Northstar's zero came in as a zero. Pace skips missing months, so Sunbelt's May pace went from {sunbelt_pace_may26_before} to {sunbelt_pace_may26}. The home page flags Harbor because the CRM still says On track.",
  },
  {
    id: "checks-all", part: "backup", kind: "native", title: "All eight tests on the data", min: 0,
    native: { layout: "checks" },
    note: "All eight, for when someone asks. {sales_rows} rows is {agencies} agencies by {routes} routes by {months} months, minus Sunbelt's {sunbelt_missing_rows} missing. The same tests run before every commit.",
  },
  {
    id: "words", part: "backup", kind: "native", title: "Booking, seat, share, fair share and pace, in plain words", min: 0,
    native: {
      layout: "tiles",
      tiles: [
        { head: "Booking", body: "A company's purchase of one or more tickets, with the route, the day and the fare." },
        { head: "Seat", body: "A seat an airline flies on a route in a month. The seat counts here are the DOT's T-100 data." },
        { head: "Share", body: "AA revenue divided by everything the agency sold on the same routes." },
        { head: "Fair share", body: "AA's share of the seats on those routes, which is what a neutral agency would send AA. The seat shares here come from T-100." },
        { head: "Pace", body: "Revenue so far as a percent of the goal so far. Over a hundred is ahead. The goals are made up." },
      ],
    },
    note: "Five words in plain English, for when someone asks what one means. The goals behind pace are made up, and the seat counts behind fair share are the DOT's.",
  },
  {
    id: "dashboard", part: "backup", kind: "native", title: "The AI/BI dashboard on the same metric view", min: 0,
    native: {
      layout: "demo",
      demo: { kind: "dashboard" },
      lines: [
        "It stands in for Power BI and reads the same metric view as Ask.",
        "It shows pace, AA share against fair share, and the share gap by market.",
        "For why a number moved, ask the app.",
      ],
    },
    note: "Click Open the sales dashboard, and it opens in a new tab. It reads the same metric view and stands in for Power BI, and fair share on it uses the T-100 seats. Close the tab to come back.",
  },
  {
    id: "choices", part: "backup", kind: "native", title: "What I chose for Fairshare, and what I chose against", min: 0,
    native: {
      layout: "tiles",
      tiles: [
        { head: "A metric view over a table of shares", body: "Share is a ratio, so a saved share goes wrong as soon as someone groups the rows another way." },
        { head: "Genie inside the app's agent", body: "Genie alone answers with numbers. The app's agent adds the agreements, the reasons, the refusals and the verifier." },
        { head: "A verifier before the person", body: "Matching each number to a query result is cheap and exact, so it runs on every answer." },
        { head: "Math in SQL, words in the model", body: "Arithmetic that must add up runs in the warehouse. The model only writes the words." },
        { head: "Every query as the viewer", body: "The App never queries as itself, which is how an agency portal would show each agency only its own numbers." },
        { head: "Benchmarks with known answers", body: "Each benchmark question has a known answer, and I run the questions again after any prompt or definition change." },
      ],
    },
    note: "For the data lead, each choice next to what I chose against. The big ones are the metric view, since saved shares go wrong when you group differently, and math in SQL with only the words in the model.",
  },
  {
    id: "dict-facts", part: "backup", kind: "native", title: "Agency sales by route and month, every column", min: 0,
    native: { layout: "table", tables: ["gold.fact_agency_sales_monthly"] },
    note: "The sales table in full, for when someone asks. One row per agency, route and month, {sales_rows} rows in all. Share is AA revenue over market revenue.",
  },
  {
    id: "dict-seats", part: "backup", kind: "native", title: "Seats by route and month, every column, from T-100", min: 0,
    native: { layout: "table", tables: ["gold.fact_market_capacity"] },
    note: "The seat table in full, T-100 data, one row per route and month. The projected flag marks August and September, which repeat last year until the DOT publishes them.",
  },
  {
    id: "dict-agencies", part: "backup", kind: "native", title: "The made-up agencies, column by column", min: 0,
    native: { layout: "table", tables: ["gold.dim_agency"] },
    note: "The {agencies} agencies, column by column, for when someone asks. The agency names and account managers are made up too.",
  },
  {
    id: "dict-routes", part: "backup", kind: "native", title: "The routes and their AA hubs, column by column", min: 0,
    native: { layout: "table", tables: ["gold.dim_market"] },
    note: "The {routes} routes, column by column. Each route says whether it starts at an AA hub.",
  },
  {
    id: "dict-goals", part: "backup", kind: "native", title: "Each agency's made-up goal for the year", min: 0,
    native: { layout: "table", tables: ["gold.agency_goals"] },
    note: "The goals here are made up and soft, so pace is a ranking more than a grade.",
  },
  {
    id: "dict-pace", part: "backup", kind: "native", title: "Pace by agency and month", min: 0,
    native: { layout: "table", tables: ["gold.agency_pace"] },
    note: "The goal so far only grows for months an agency reported, which is why Sunbelt's May pace reads {sunbelt_pace_may26}.",
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
    note: "The deals. The home page compares the health column with the data, and that's how it flags Harbor, whose renewal still says On track while share fell.",
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
      columns: ["booking_id", "ticket_number", "corp_id", "booking_date", "travel_date", "origin", "dest", "channel", "fare_usd", "ticket_count", "cabin", "agency_id"],
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
    note: "The decomposition row for Harbor's September. Volume, mix and share add up to the change exactly, so nothing is left over. The seat check is zero, since September's seats are last year's.",
  },
  {
    id: "dict-ops-shares", part: "backup", kind: "native", title: "AA share and fair share in Harbor's September row", min: 0,
    native: {
      layout: "table",
      tables: ["ops.decomposition"],
      columns: ["aa_share_now", "aa_share_prior", "fair_share_now", "fair_share_prior", "market_now", "market_prior"],
    },
    note: "The shares behind that row. AA share went from {harbor_share_sep25} to {harbor_share_sep26} while fair share stayed near {harbor_fair_share_sep26}, and Harbor sold more overall, which is the volume effect.",
  },
  {
    id: "dict-kpis", part: "backup", kind: "native", title: "How AA share is defined, in one row", min: 0,
    native: { layout: "table", tables: ["ops.kpi_definitions"], columns: ["kpi", "display_name", "definition_en", "owner", "source_columns", "metric_view_expr"] },
    note: "Each of the {kpis} numbers has a row like this one, AA share here. The expression is the one in the metric view that Genie and the dashboard read.",
  },
  {
    id: "dict-twins", part: "backup", kind: "native", title: "AA share as a Power BI measure, and its SQL copy", min: 0,
    native: { layout: "table", tables: ["ops.kpi_definitions"], columns: ["dax_twin", "twin_sql", "twin_version", "twin_sql_retired", "retired_note"] },
    note: "My first SQL copy of AA share counted passengers, and {parity_red} of {parity_rows} agency-months disagreed with the metric view. The retired copy and the reason stay in the row.",
  },
  {
    id: "security", part: "backup", kind: "native", title: "The viewer's login and the App's keys", min: 0,
    native: {
      layout: "tiles",
      tiles: [
        { head: "Genie as the viewer", body: "The App runs Genie with the viewer's own token, which keeps Genie free on Free Edition and lets Unity Catalog row filters apply." },
        { head: "Keys out of the code", body: "The laptop keeps keys in a file git ignores, and the job and the App read them from a Databricks secret scope." },
      ],
    },
    note: "If security comes up, Genie runs as the viewer, never the App, which keeps it free on Free Edition. The keys are in a file git ignores, or in a secret scope for the job and the App.",
  },
  {
    id: "foundry-eval", part: "backup", kind: "native", title: "Foundry's evaluators on the four writers, {foundry_eval_date}", min: 0,
    native: {
      layout: "tiles",
      tiles: [
        { head: "One run of the nightly job", body: "Three of the four writers wrote {foundry_nightly_pages} pages, and the verifier checked every sentence." },
        { head: "Quality", body: "Every normal page passed relevance, coherence, fluency and the content harm checks." },
        { head: "The indirect attack check", body: "It flagged the planted instruction, and also {foundry_attack_false_flags} of {foundry_attack_notes} normal CRM correction notes." },
        { head: "Speed", body: "A clean page took {foundry_clean_page_s} seconds. The guardrail refused a jailbreak at the prompt in {foundry_refusal_s} seconds." },
      ],
    },
    note: "More on the Foundry writers than the evals slides give, for when someone asks. The attack check flagged the planted instruction and {foundry_attack_false_flags} normal notes too, and a clean page took {foundry_clean_page_s} seconds.",
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
    note: "Four agents on one runtime. The 6 am job runs three of them, and prospect research runs when someone picks a market. Each one waits for a person to approve.",
  },
  {
    id: "platform", part: "backup", kind: "native", title: "Databricks Free Edition limits", min: 0,
    native: {
      layout: "tiles",
      tiles: [
        { head: "The warehouse stops when idle", body: "It stops after ten idle minutes, and Free Edition locks that setting. A keep-warm script runs during a demo." },
        { head: "The App stops after a day", body: "An App stops a day after it starts or deploys, so I start it before a demo." },
        { head: "No App Builder", body: "Genie's App Builder needs preview settings this workspace does not have." },
      ],
    },
    note: "Free Edition limits, if asked. The warehouse stops when idle, so a keep-warm script runs during a demo, and the App stops a day after it starts, so I start it before. There's no App Builder.",
  },
];
