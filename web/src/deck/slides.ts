// The deck's slides in the order a talk walks them: the four parts of the main path, then the backup slides, which the
// notes window's outline reaches. min is a slide's minutes on the main path, short its minutes on the short path (only
// the slides on it have one). Assets and thumbs are keys of images and pages in assets.ts; the thumb is the PNG under a
// live or animated frame. Every number is a {placeholder} that SlideView fills from facts.json, and deck.test.ts holds
// every string here to the content rules. A still is a screenshot of the app, so it shows no part label. A note is what
// the speaker says on the slide, under 40 words and in the way he talks; the notes window fills in its numbers.
import type { Slide } from "../lib/deck";

/** Names of things that exist today. A tile tagged "Possibility" names none of them. */
export const BUILT = ["Foundry writer", "hosted agent", "Genie", "metric view", "MLflow", "Delegate", "verifier", "harness", "Databricks App", "AI/BI dashboard", "nightly job", "CRM stand-in"];

/** The report that explains the whole project. The start slide links to it once it is published. */
export const REPORT_URL: string | null = null;

export const slides: Slide[] = [
  // 1. The first answer
  {
    id: "title", part: "first", kind: "live", title: "Fairshare: sales answers you can check", min: 0.5, short: 0.5,
    asset: "hairline/title-b-airliner.html", thumb: "hairline/png/title-b.png",
    note: "Name and one line on me. Before anyone asks, all the data here is made up, the agencies, the sales, the contracts, the seats and so on. Please stop me anywhere. Then what I heard in round one.",
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
    note: "So there are two slow steps, a share question turns into a ticket to sales BI, and account managers build pre-call packs by hand. Ask the sales director how long a pack takes today. Then what I built.",
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
    note: "It's one app with two modes. In Ask you type a question in plain words, and every number links to its query. Delegate drafts routine pages overnight for a person to approve. I'd like to show you Ask live.",
  },
  {
    id: "query-opener", part: "first", kind: "live", title: "It starts with a question", min: 0.25,
    asset: "hairline/opener-query.html", thumb: "hairline/png/query.png",
    note: "It starts with a question, the kind that comes up in a Monday sales meeting. Let it play a few seconds.",
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
    note: "Click Ask it live, click the box, Enter, talk through the steps. Click the share effect, {harbor_share_usd}. Fair share is made up. A removed sentence had a number no query returned. Past a minute, the still. Back: sidebar.",
  },
  {
    id: "director", part: "first", kind: "animated", title: "Sales director: a question in the Monday meeting", min: 1.25,
    asset: "04-journey-sales-director-animated.html", thumb: "export/04-journey-sales-director.png",
    note: "Behind that answer, one press per step. Genie ran the query as me, SQL split the change, the model wrote only the words, and the verifier checked every number. So where does the data come from?",
  },

  // 2. The data
  {
    id: "elevator-opener", part: "data", kind: "live", title: "Four floors: as delivered, cleaned, ready to use, and defined once", min: 0.25,
    asset: "hairline/opener-elevator.html", thumb: "hairline/png/elevator.png",
    note: "Part two, the data. Four floors, from the files as they came in up to each number defined once. Let it play.",
  },
  {
    id: "pipeline", part: "data", kind: "animated", title: "Where the numbers come from", min: 1.5,
    asset: "06-data-pipeline-animated.html", thumb: "export/06-data-pipeline.png",
    note: "Four sources, and the seat shares are made up, one per route. Bronze is as delivered, silver cleaned, gold is {sales_rows} rows, one per agency, route and month. On top, {kpis} numbers, each defined once. Then one actual row.",
  },
  {
    id: "row", part: "data", kind: "native", title: "One row each: Summit Travel Partners on DFW-ORD, Sep 2026", min: 1.75,
    native: { layout: "table", tables: ["gold.fact_agency_sales_monthly", "gold.fact_market_capacity"] },
    note: "AA revenue sits next to everything the agency sold on that route that month, and share is one divided by the other. The seat row is made up, it even says synthetic. Next, every agency by every month.",
  },
  {
    id: "coverage", part: "data", kind: "image", title: "Every agency, every month", min: 0.75,
    asset: "export/10-coverage.png",
    note: "{agency_months_present} of {agency_months_total} agency-months have rows. The holes are Sunbelt, which sent nothing in March and April 2026. Northstar's {northstar_zero_route} in {northstar_zero_month} is a true zero, they sold the route, just none on AA. Revenue shows them next.",
  },
  {
    id: "revenue", part: "data", kind: "image", title: "AA revenue by month, 2025 against 2026", min: 0.75,
    asset: "export/11-revenue-by-month.png",
    note: "This year runs ahead of last except March and April, at {yoy_mar26} and {yoy_apr26}, and the axis doesn't start at zero. The dip is Sunbelt missing and Harbor falling, while the others grew. I planted both of those.",
  },
  {
    id: "planted", part: "data", kind: "image", title: "What I planted, and what cleaning did", min: 2,
    asset: "export/14-what-was-planted.png",
    note: "Sunbelt is a missing logbook page, Northstar's zero a page saying no flights today. Pace skips missing months, so Sunbelt's May went {sunbelt_pace_may26_before} to {sunbelt_pace_may26} of pace. Harbor's flagged since the CRM still says On track. Then the checks.",
  },
  {
    id: "checks", part: "data", kind: "native", title: "The basic checks: what each should be, and what it is", min: 0.75,
    native: { layout: "table", tables: ["checks"] },
    note: "{sales_rows} rows is {agencies} agencies by {routes} routes by {months} months, minus Sunbelt's {sunbelt_missing_rows} missing. Every check passes, and the same checks run as a test before every commit. Next, the {kpis} numbers.",
  },
  {
    id: "numbers", part: "data", kind: "image", title: "The seven numbers", min: 1.5,
    asset: "export/09-definitions.png",
    note: "Shares are like batting averages, add up hits and at-bats, never average the averages. In Q3 the {agencies} shares average {avg_of_shares_q3}, but the share of the total is {share_of_total_q3}. Ask where AA's fair share differs, mine's made up.",
  },
  {
    id: "share-fair", part: "data", kind: "image", title: "AA share against fair share, Q3 2026", min: 1,
    asset: "export/12-share-vs-fair.png",
    note: "Fair share is about the same for everyone, since they all sell the same routes and the seat shares are made up. Lone Star's on top at {agency_q3_aa_share_lonestar}, FareHub's last at {agency_q3_aa_share_farehub}. Now why Harbor moved.",
  },
  {
    id: "moved", part: "data", kind: "animated", title: "Why Harbor moved", min: 1.5,
    asset: "08-why-it-moved-animated.html", thumb: "export/08-why-it-moved.png",
    note: "Harbor went from {harbor_revenue_sep25_usd} to {harbor_revenue_sep26_usd}. Volume added {harbor_volume_usd}, mix barely moved, and share took {harbor_share_usd}, more than the whole drop. The made-up seat shares would have predicted {harbor_fair_share_effect_usd}, so seats don't explain it. Now what I built.",
  },

  // 3. What I built
  {
    id: "stack-opener", part: "built", kind: "live", title: "Five layers under every answer", min: 0.25,
    asset: "hairline/stack.html", thumb: "hairline/png/stack.png",
    note: "Part three, what I built, five layers under every answer. Let it play, pointing does nothing in the deck.",
  },
  {
    id: "system", part: "built", kind: "animated", title: "The system", min: 2.25, short: 1.5,
    asset: "01-system-exploded-animated.html", thumb: "export/01-system-exploded.png",
    note: "Five layers, one press each. The data's made up, Ask runs on Genie and Qwen3-Next, Delegate on Foundry writers. Blue is the checks: every number matched to a query, and a person approves what goes out.",
  },
  {
    id: "sieve-opener", part: "built", kind: "live", title: "Every number passes through the checks", min: 0.25,
    asset: "hairline/opener-sieve.html", thumb: "hairline/png/sieve.png",
    note: "Every number goes through the checks before you see it. Let it play.",
  },
  {
    id: "checked", part: "built", kind: "animated", title: "How an answer gets checked", min: 2,
    asset: "02-answer-checked-animated.html", thumb: "export/02-answer-checked.png",
    note: "The verifier is kind of a newspaper fact-checker with the source documents. A sentence whose number no query returned gets cut from the answer. Genie alone scored {genie_benchmark} in one run on {genie_benchmark_date}, after five questions named their columns.",
  },
  {
    id: "riffle-opener", part: "built", kind: "live", title: "Pages wait for a person to decide", min: 0.25,
    asset: "hairline/opener-riffle.html", thumb: "hairline/png/riffle.png",
    note: "That's Ask. The other mode is Delegate, where pages wait for a person to decide. Let it play.",
  },
  {
    id: "delegate", part: "built", kind: "image", title: "Agents draft, people decide", min: 1.25,
    asset: "export/03-delegate.png",
    note: "Every night the job runs four agents. Fixed queries pull the facts, a Foundry writer drafts from only those, and the verifier checks every number. Nothing is logged or sent until a person approves. Let me open one.",
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
    note: "Open the pack, pick FareHub Online or Lone Star, the nightly job wrote it. Click a number for its rows, then Approve. If asked, fine means {tier_watch_band_pts} or more points from a tier line. Past a minute, the still.",
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
    note: "I built this with Claude Code. The sales director's post called vibe coding a plus, and what keeps it in line is the rules file, a commit check and a hook that blocks destructive SQL. Then, what I measured.",
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
    note: "I'll start with the misses. On {app_model_date} the App's model got {app_model_right} of {app_model_questions} right, and {app_model_gave_up_passed} answer that gave up still passed the verifier, because it had no numbers to check. Genie's {genie_benchmark} was one run, on {genie_benchmark_date}.",
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
    note: "The biggest one is that it doesn't flag a single corporate's drop yet, though you can ask about one. The Foundry writers run today, and Ask as a hosted agent is built but not deployed. Then, how we'd know.",
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
    note: "If it works, account managers come back the next week, prep time per call drops, fewer share questions become tickets, and drafts get approved with light edits. I'd time today first. Now, the same layers at AA.",
  },
  {
    id: "at-aa", part: "proof", kind: "image", title: "The same layers at AA", min: 1.5,
    asset: "export/15-at-aa.png",
    note: "At AA it's the same layers, each made-up table next to the feed that would replace it. The hardest is the agency's sales on other airlines, since AA only sees its own. The Microsoft pieces wait on AA's account.",
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
    note: "Each of these is a possibility, tagged that way, and they all wait on AA's own Microsoft account. Teams would put the same questions where account managers already work. Then how I'd start.",
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
    note: "First I'd time today's work, so there's a before. Then I'd swap AA's own fair share in for my made-up one, one change, connect AA's agency sales, and add a way to flag a wrong answer. Leave this up.",
  },

  // Backup, reached from the notes window's outline
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
    id: "fair", part: "backup", kind: "image", title: "What fair share means", min: 0,
    asset: "export/07-fair-share.png",
    note: "Fair share is AA's share of the seats, and these seat shares are made up. On DFW-ORD in Q3, Summit sent {summit_q3_aa_share} to AA against {summit_q3_fair_share}, {summit_q3_gap_usd} above fair share. By passengers it's {summit_q3_pax_share}, nearly the same.",
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
    id: "dict-agencies", part: "backup", kind: "native", title: "The agencies and the routes", min: 0,
    native: { layout: "table", tables: ["gold.dim_agency", "gold.dim_market"] },
    note: "The {agencies} agencies and {routes} routes, column by column, for when someone asks. The agency names and account managers are made up too. Each route says whether it starts at an AA hub.",
  },
  {
    id: "dict-goals", part: "backup", kind: "native", title: "Goals and pace", min: 0,
    native: { layout: "table", tables: ["gold.agency_goals", "gold.agency_pace"] },
    note: "The goals here are made up and soft, so pace works as a ranking. The goal so far only grows for months an agency reported, which is why Sunbelt's May reads {sunbelt_pace_may26} of pace.",
  },
  {
    id: "dict-agreements", part: "backup", kind: "native", title: "The agreements, clause by clause", min: 0,
    native: { layout: "table", tables: ["gold.contract_clauses"] },
    note: "The {agreements} agreements, one row per clause. Each row keeps the file, the page and the clause word for word, so an answer can cite the page. The agreements are made up.",
  },
  {
    id: "dict-crm", part: "backup", kind: "native", title: "The CRM stand-in", min: 0,
    native: { layout: "table", tables: ["gold.crm_contacts", "gold.crm_opportunities", "gold.crm_activities"] },
    note: "The CRM stand-in for Dynamics 365. Names and emails are made up. The home page compares the health column with the data, which is how Harbor gets flagged: its renewal still says On track while share fell.",
  },
  {
    id: "dict-bookings", part: "backup", kind: "native", title: "Corporate bookings", min: 0,
    native: { layout: "table", tables: ["gold.fact_corporate_bookings", "gold.dim_corporate"] },
    note: "Corporate bookings and the companies, all made up. Cleaning took {channel_spellings_delivered} channel spellings down to {channel_spellings_cleaned} and dropped {duplicate_tickets} tickets loaded twice. It doesn't flag a single corporate's drop yet, though you can ask about one.",
  },
  {
    id: "dict-ops", part: "backup", kind: "native", title: "The app's own tables", min: 0,
    native: { layout: "table", tables: ["ops.decomposition", "ops.kpi_definitions"] },
    note: "The decomposition row here is Harbor's September, and nothing is left over, so volume, mix and share add up exactly. My first SQL twin for AA share counted passengers, and all {parity_rows} agency-months came back red.",
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
    note: "Who sees what, if it comes up. Every query runs with the viewer's own token, so you only see what you're allowed to. The writers get a fact sheet and no tools, and the app never sends anything itself.",
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
    note: "How the writers were tested, if asked. Groundedness failed on {foundry_groundedness_misses} of {foundry_quality_pages} pages, the prompt shield refused {foundry_shield_refused} normal pages until I moved the rules into the agents, and the attack check flagged {foundry_attack_false_flags} normal notes too.",
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
