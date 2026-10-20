// The deck's slides in the order a talk walks them: the four parts of the main path, then the backup slides, which the
// notes window's outline reaches. min is a slide's minutes on the main path, short its minutes on the short path (only
// the slides on it have one). Assets and thumbs are keys of images and pages in assets.ts; the thumb is the PNG under a
// live or animated frame. Every number is a {placeholder} that SlideView fills from facts.json, and deck.test.ts holds
// every string here to the content rules. A still is a screenshot of the app, so it shows no part label. Notes stay one
// plain line each until the speaker notes are written.
import type { Slide } from "../lib/deck";

/** Names of things that exist today. A tile tagged "Possibility" names none of them. */
export const BUILT = ["Foundry writer", "hosted agent", "Genie", "metric view", "MLflow", "Delegate", "verifier", "harness", "Databricks App", "AI/BI dashboard", "nightly job", "CRM stand-in"];

/** The report that explains the whole project. The start slide links to it once it is published. */
export const REPORT_URL: string | null = null;

const dictNote = "Every column of this table in plain words, with one example, for when someone asks about it.";

export const slides: Slide[] = [
  // 1. The first answer
  {
    id: "title", part: "first", kind: "live", title: "Fairshare: sales answers you can check", min: 0.5, short: 0.5,
    asset: "hairline/title-b-airliner.html", thumb: "hairline/png/title-b.png",
    note: "Say your name and one line about yourself. Then say the agencies, sales, contracts and seats are all made up, and ask them to stop you anywhere.",
  },
  {
    id: "problem", part: "first", kind: "native", title: "Two slow steps today", min: 1, short: 1,
    native: {
      layout: "statement",
      lines: [
        "A share question becomes a ticket to sales BI, and the answer can take days.",
        "Account managers build each pre-call pack by hand, one agency at a time.",
        "How long does a pack take your team today?",
      ],
    },
    note: "Name the two slow steps. Ask the room how long a pre-call pack takes them today, then say what I built.",
  },
  {
    id: "what", part: "first", kind: "native", title: "An app that answers sales questions with numbers you can check", min: 0.5, short: 0.5,
    native: {
      layout: "tiles",
      tiles: [
        { head: "Ask", body: "Ask a question in plain words. Every number in the answer comes from a query, and one click shows its rows." },
        { head: "Delegate", body: "Agents draft the routine pages overnight, like the Monday pre-call pack. A person approves each page before anything goes out." },
      ],
    },
    note: "One line on what it is, then the two modes. Ask answers questions, and Delegate drafts the routine pages. Next comes a live answer.",
  },
  {
    id: "query-opener", part: "first", kind: "live", title: "It starts with a question", min: 0.25,
    asset: "hairline/opener-query.html", thumb: "hairline/png/query.png",
    note: "It starts with a question. Let it play, then go to Ask.",
  },
  {
    id: "ask", part: "first", kind: "native", title: "A live question in Ask", min: 3.5, short: 2.5,
    native: {
      layout: "demo",
      demo: { kind: "ask", question: "Why is Harbor Business Travel down in September?" },
      lines: [
        "It splits the drop into volume, route mix and share.",
        "Click the share effect to see the rows behind it.",
        "The app matches every number to a query before you see it.",
      ],
    },
    note: "Press Enter on the Harbor question and talk through the steps while it runs. Click the share effect to show its rows. Past a minute, go to the still.",
  },
  {
    id: "director", part: "first", kind: "animated", title: "Sales director: a question in the Monday meeting", min: 1.25,
    asset: "04-journey-sales-director-animated.html", thumb: "export/04-journey-sales-director.png",
    note: "Step through what happened behind that answer, one press per step. Then ask where these numbers come from.",
  },

  // 2. The data
  {
    id: "elevator-opener", part: "data", kind: "live", title: "Four floors: as delivered, cleaned, ready to use, and defined once", min: 0.25,
    asset: "hairline/opener-elevator.html", thumb: "hairline/png/elevator.png",
    note: "The data, floor by floor. Let it play.",
  },
  {
    id: "pipeline", part: "data", kind: "animated", title: "Where the numbers come from", min: 1.5,
    asset: "06-data-pipeline-animated.html", thumb: "export/06-data-pipeline.png",
    note: "Step through where the numbers come from: as delivered, cleaned, ready to use, defined once. Say the seat shares are made up.",
  },
  {
    id: "row", part: "data", kind: "native", title: "One row each: Summit Travel Partners on DFW-ORD, Sep 2026", min: 1.75,
    native: { layout: "table", tables: ["gold.fact_agency_sales_monthly", "gold.fact_market_capacity"] },
    note: "One row of sales and one row of seats, each column in plain words next to its value. The seat numbers are made up.",
  },
  {
    id: "coverage", part: "data", kind: "image", title: "Every agency, every month", min: 0.75,
    asset: "export/10-coverage.png",
    note: "Every agency by every month. Sunbelt is missing two months, and Northstar has a true zero that cleaning kept.",
  },
  {
    id: "revenue", part: "data", kind: "image", title: "AA revenue by month, 2025 against 2026", min: 0.75,
    asset: "export/11-revenue-by-month.png",
    note: "AA revenue by month, this year against last. The March and April dip is Sunbelt missing and Harbor falling.",
  },
  {
    id: "planted", part: "data", kind: "image", title: "What I planted, and what cleaning did", min: 2,
    asset: "export/14-what-was-planted.png",
    note: "Four traps I planted and what cleaning did with each, then the two drops the app should catch. A gap is not a zero.",
  },
  {
    id: "checks", part: "data", kind: "native", title: "The basic checks: what each should be, and what it is", min: 0.75,
    native: { layout: "table", tables: ["checks"] },
    note: "Each check says what the number should be and what it is. All of them pass, and a test runs them before every commit.",
  },
  {
    id: "numbers", part: "data", kind: "image", title: "The seven numbers", min: 1.5,
    asset: "export/09-definitions.png",
    note: "Seven numbers, each defined once. Show how fair share is computed, then ask the room where AA's own version differs.",
  },
  {
    id: "share-fair", part: "data", kind: "image", title: "AA share against fair share, Q3 2026", min: 1,
    asset: "export/12-share-vs-fair.png",
    note: "Each agency's AA share against fair share for the quarter, sorted by the gap. Fair share barely moves because the seat shares are made up.",
  },
  {
    id: "moved", part: "data", kind: "animated", title: "Why Harbor moved", min: 1.5,
    asset: "08-why-it-moved-animated.html", thumb: "export/08-why-it-moved.png",
    note: "Step through why Harbor moved: volume, route mix and share. Volume grew, so losing share cost more than the whole drop.",
  },

  // 3. What I built
  {
    id: "stack-opener", part: "built", kind: "live", title: "Five layers under every answer", min: 0.25,
    asset: "hairline/stack.html", thumb: "hairline/png/stack.png",
    note: "What I built, layer by layer. Let it play.",
  },
  {
    id: "system", part: "built", kind: "animated", title: "The system", min: 2.25, short: 1.5,
    asset: "01-system-exploded-animated.html", thumb: "export/01-system-exploded.png",
    note: "Five layers sit under every answer. The blue one is the checks. Before anyone sees a number, the app matches it to the rows of a query.",
  },
  {
    id: "sieve-opener", part: "built", kind: "live", title: "Every number passes through the checks", min: 0.25,
    asset: "hairline/opener-sieve.html", thumb: "hairline/png/sieve.png",
    note: "Every number passes through the checks. Let it play.",
  },
  {
    id: "checked", part: "built", kind: "animated", title: "How an answer gets checked", min: 2,
    asset: "02-answer-checked-animated.html", thumb: "export/02-answer-checked.png",
    note: "Step through how an answer gets checked. Then say the benchmark: Genie alone scored {genie_benchmark} in one run on {genie_benchmark_date}, after five questions named their columns.",
  },
  {
    id: "riffle-opener", part: "built", kind: "live", title: "Pages wait for a person to decide", min: 0.25,
    asset: "hairline/opener-riffle.html", thumb: "hairline/png/riffle.png",
    note: "Pages wait for a person to decide. Let it play.",
  },
  {
    id: "delegate", part: "built", kind: "image", title: "Agents draft, people decide", min: 1.25,
    asset: "export/03-delegate.png",
    note: "Four agents draft pages overnight. The verifier checks every sentence, and nothing goes out until a person approves it.",
  },
  {
    id: "precall", part: "built", kind: "native", title: "The pre-call pack the 6 am job wrote", min: 3, short: 2,
    native: {
      layout: "demo",
      demo: { kind: "precall" },
      lines: [
        "One page per agency, each with a drafted email.",
        "The verifier checked every number on the page against a query.",
        "Nothing is sent or recorded until a person approves it.",
      ],
    },
    note: "Open the pack the 6 am job wrote. Show one page, click a number for its rows, then approve it. If it stalls, go to the still.",
  },
  {
    id: "built-how", part: "built", kind: "native", title: "How I built it", min: 1.25,
    native: {
      layout: "tiles",
      tiles: [
        { head: "Claude Code", body: "I built the app with this AI coding tool. It works under the rules file, the commit check and the hook." },
        { head: "The rules file", body: "CLAUDE.md holds the rules every change follows: numbers only from queries, one definition per number, nothing destructive." },
        { head: "The commit check", body: "Before every commit, the ground-truth queries run and the tests must pass. If either fails, the commit stops." },
        { head: "The safety hook", body: "A hook blocks DROP, TRUNCATE and any DELETE without a WHERE, in edits and in commands." },
      ],
    },
    note: "Built with Claude Code under a rules file. A commit check runs the ground-truth queries and the tests, and a hook blocks destructive commands.",
  },

  // 4. Proof and next
  {
    id: "measured", part: "proof", kind: "native", title: "What I measured, misses included", min: 1.75, short: 1.75,
    native: {
      layout: "tiles",
      tiles: [
        { head: "The App's own model", body: "In one benchmark run on {app_model_date}, Qwen3-Next got {app_model_right} of {app_model_questions} right, {app_model_partly} partly right and {app_model_wrong} wrong. Answers took {app_answer_median_s} seconds at the median and {app_answer_max_s} at the slowest." },
        { head: "What the verifier missed", body: "In the {app_model_date} run, {app_model_gave_up_passed} answer that gave up still passed the verifier, because it had no numbers to check." },
        { head: "Genie alone", body: "It scored {genie_benchmark} in one run on {genie_benchmark_date}, after five questions were reworded to name their columns. Two earlier runs that day scored lower." },
        { head: "The nightly check", body: "From {nightly_parity_from} to {nightly_parity_to}, {nightly_parity_runs} scheduled runs compared the metric view with a SQL copy of the Power BI measure, for {twins_checked} of the {kpis} numbers. They found {nightly_parity_drift} differences." },
      ],
    },
    note: "Say the misses plainly, including the answer that gave up and still passed. Say Genie's score as one run on one day.",
  },
  {
    id: "limits", part: "proof", kind: "native", title: "What it does not do yet", min: 1,
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
    note: "The big one: it does not flag a single corporate's drop yet, though it can answer a question about one.",
  },
  {
    id: "know", part: "proof", kind: "native", title: "How we would know it worked", min: 1,
    native: {
      layout: "tiles",
      tiles: [
        { head: "Account managers using it", body: "How many open it each week, and how many come back the next week." },
        { head: "Prep time per call", body: "Minutes to get ready for an agency call, timed before and after." },
        { head: "Tickets to sales BI", body: "How many share questions still arrive as tickets." },
        { head: "Drafts approved with light edits", body: "How often a person approves a page as written or with small changes." },
      ],
    },
    note: "Four measures, all about people: who uses it, prep time per call, tickets to sales BI, and drafts approved with light edits.",
  },
  {
    id: "at-aa", part: "proof", kind: "image", title: "The same layers at AA", min: 1.5,
    asset: "export/15-at-aa.png",
    note: "The same layers at AA. Each made-up table sits next to the AA feed that would replace it, hardest first.",
  },
  {
    id: "azure", part: "proof", kind: "native", title: "Possibilities on Azure", min: 0.75,
    native: {
      layout: "tiles",
      tiles: [
        { head: "Fabric and OneLake", body: "The app would read AA's own sales tables where they already sit, without copying them.", tag: "Possibility" },
        { head: "Dataverse mirror", body: "Dynamics 365 Sales contacts, deals and activities would replace the made-up CRM tables.", tag: "Possibility" },
        { head: "Teams through Copilot Studio", body: "Account managers would ask the same questions in Teams, where they already work.", tag: "Possibility" },
        { head: "Entra ID sign-in", body: "Each person would sign in with their AA account and see only the agencies they cover.", tag: "Possibility" },
      ],
    },
    note: "Each of these is a possibility and is tagged that way. They wait on AA's own Microsoft account.",
  },
  {
    id: "start", part: "proof", kind: "native", title: "How I would start at AA", min: 1, short: 1,
    native: {
      layout: "statement",
      lines: [
        "Time today's work first: how long a pre-call pack takes, and how many share questions become tickets.",
        "Put AA's own fair share into the metric view. It lives in one place, so that is one change.",
        "Connect AA's own agency sales, and match each number to the reports people use now.",
        "Give account managers a way to mark an answer as wrong, and read every one.",
      ],
    },
    note: "How I would start at AA. Leave this slide up through the questions.",
  },

  // Backup, reached from the notes window's outline
  {
    id: "ask-still", part: "backup", kind: "image", still: true, title: "A good run of the Harbor question", min: 0,
    asset: "export/ask-still.png",
    note: "A screenshot of an earlier run on the App, for when the live answer stalls. Tell the room it is a still. Then pick the next slide from the outline.",
  },
  {
    id: "precall-still", part: "backup", kind: "image", still: true, title: "A good run of the pre-call pack", min: 0,
    asset: "export/precall-still.png",
    note: "A screenshot of an earlier pre-call page from the App, for when the pack will not open. Tell the room it is a still, and point to the checked numbers. Then pick the next slide.",
  },
  {
    id: "manager", part: "backup", kind: "animated", title: "Account manager: Monday before agency calls", min: 0,
    asset: "05-journey-account-manager-animated.html", thumb: "export/05-journey-account-manager.png",
    note: "The account manager's Monday, step by step, for when the room asks how they would use it.",
  },
  {
    id: "fair", part: "backup", kind: "image", title: "What fair share means", min: 0,
    asset: "export/07-fair-share.png",
    note: "How fair share works, for when someone asks. The seat shares are made up, one per route.",
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
    note: "The five words in plain English, for when someone asks what one means.",
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
    note: "The dashboard opens in a new tab. Close the tab to come back to the deck.",
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
    note: "The design choices, each with what I chose against, for the data lead's questions.",
  },
  {
    id: "dict-agencies", part: "backup", kind: "native", title: "The agencies and the routes", min: 0,
    native: { layout: "table", tables: ["gold.dim_agency", "gold.dim_market"] }, note: dictNote,
  },
  {
    id: "dict-goals", part: "backup", kind: "native", title: "Goals and pace", min: 0,
    native: { layout: "table", tables: ["gold.agency_goals", "gold.agency_pace"] }, note: dictNote,
  },
  {
    id: "dict-agreements", part: "backup", kind: "native", title: "The agreements, clause by clause", min: 0,
    native: { layout: "table", tables: ["gold.contract_clauses"] }, note: dictNote,
  },
  {
    id: "dict-crm", part: "backup", kind: "native", title: "The CRM stand-in", min: 0,
    native: { layout: "table", tables: ["gold.crm_contacts", "gold.crm_opportunities", "gold.crm_activities"] }, note: dictNote,
  },
  {
    id: "dict-bookings", part: "backup", kind: "native", title: "Corporate bookings", min: 0,
    native: { layout: "table", tables: ["gold.fact_corporate_bookings", "gold.dim_corporate"] }, note: dictNote,
  },
  {
    id: "dict-ops", part: "backup", kind: "native", title: "The app's own tables", min: 0,
    native: { layout: "table", tables: ["ops.decomposition", "ops.kpi_definitions"] }, note: dictNote,
  },
  {
    id: "security", part: "backup", kind: "native", title: "Who can see what", min: 0,
    native: {
      layout: "tiles",
      tiles: [
        { head: "Runs as the viewer", body: "Genie and every query run with the viewer's own token, never the App's service principal." },
        { head: "Writers with no tools", body: "The writers get a fact sheet and nothing else. A writer ignored an instruction planted in a CRM note." },
        { head: "A person presses send", body: "Approving can record one CRM row and open a mail draft. The app itself sends nothing." },
        { head: "Secrets stay out of the code", body: "Keys live in a file git ignores on the laptop, and in a Databricks secret scope for the job and the App." },
      ],
    },
    note: "Who can see what, if asked: each query runs as the viewer, the writers have no tools, and a person sends everything.",
  },
  {
    id: "foundry-eval", part: "backup", kind: "native", title: "Foundry's evaluators on the four writers", min: 0,
    native: {
      layout: "tiles",
      tiles: [
        { head: "One nightly run", body: "The four Foundry writers wrote {foundry_nightly_pages} pages, and the verifier checked every sentence." },
        { head: "Quality", body: "Every normal page passed relevance, coherence, fluency and the content harm checks. Groundedness failed on {foundry_groundedness_misses} of the {foundry_quality_pages} pages." },
        { head: "The prompt shield", body: "It refused {foundry_shield_refused} of {foundry_shield_pages} normal pages in the first runs. Moving the rules into the agents fixed it." },
        { head: "The indirect attack check", body: "It flagged the planted instruction, and also {foundry_attack_false_flags} of {foundry_attack_notes} normal CRM correction notes." },
        { head: "Speed", body: "A clean page took {foundry_clean_page_s} seconds. The guardrail refused a jailbreak at the prompt in {foundry_refusal_s} seconds." },
      ],
    },
    note: "Foundry's own evaluators on the four writers, for when someone asks how the agents were tested.",
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
    note: "The four agents share one runtime: fixed queries, a writer with no tools, the verifier, and a person's approval.",
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
    note: "Free Edition limits, if asked: the warehouse sleeps, the App stops after a day, and there is no App Builder.",
  },
];
