export type Scope = { region: string; month: string };

export type Me = {
  email: string | null; user: string | null; name?: string | null; inside_app: boolean; scopes: string[]; backend: string; model: string;
  genie: { space_id: string; url: string } | null; data_through: string; regions: string[]; months: string[];
  links: Record<string, string>;
};

export type EvalQuestion = {
  id: string; question: string; hard: boolean;
  genie: boolean | null; space: "GOOD" | "BAD" | "NEEDS_REVIEW" | null; space_reasons: string[];
  backed: boolean | null; judge: "CORRECT" | "PARTIAL" | "WRONG" | null;
};
export type Evals = {
  questions: EvalQuestion[];
  genie: { run_at: string | null; rate: number | null };
  space: { run_at: string | null; correct: number | null; n: number | null };
  harness: { run_at: string | null; model: string | null; backed: number | null; correct: number | null };
  runs: number;
};

export type Kpis = {
  aa_revenue: number; aa_revenue_prior_year: number | null; yoy_pct: number | null; aa_share_pct: number; fair_share_pct: number;
  share_gap_pts: number; share_gap_usd: number; pace_pct: number | null; ytd_revenue?: number; ytd_goal?: number;
};
export type Mover = { agency_id: number; agency: string; region: string; share_now_pct: number; share_prior_pct: number; share_chg_pts: number; revenue_now: number; yoy_pct: number | null };
export type BehindPace = { agency_id: number; agency: string; pace_pct: number; aa_revenue: number; yoy_pct: number | null };
export type Summary = { region: string; month: string; prior_month: string; kpis: Kpis; movers: Mover[]; behind_pace: BehindPace[]; agency_count: number; headline: string; calls: Call[] };

export type Call = { i: number; tool: string; args: Record<string, unknown>; sql: string | null; rows: number | null; note: string; preview: Record<string, unknown>[]; genie: { conversation_id: string; message_id: string; url: string } | null; ms: number };
export type Sentence = { text: string; status: "verified" | "flagged" | "note"; numbers: { raw: string; source: string | null; fact: string | null }[] };
export type Answer = {
  question: string; text: string; model: string; kind: "numbers" | "why" | "agreement" | "refusal" | "comparison" | string;
  sentences: Sentence[]; removed: { sentence: string; reason: string }[]; could_not_verify: string[]; verified_text: string;
  calls: Call[]; sources: string[]; follow_ups: string[]; genie_conversation_id: string | null;
  timing: { total_ms: number; tools_ms: number }; cached: { recorded: string; model: string } | null; trace_url: string | null;
};
export type Step = { phase: string; text: string; tool?: string; args?: Record<string, unknown>; genie?: { conversation_id: string; message_id: string; url: string }; t_ms: number; done?: boolean; at?: number };
export type ApiError = { code: string; message: string };

export type Brief = {
  run_id: string; region: string; month: string; created_at: string; status: string; model: string; writer: string | null;
  sentences: Sentence[]; removed: { sentence: string; reason: string }[]; verified_text: string; draft: string; calls: Call[];
};
export type Explain = {
  agency: { agency_id: number; agency_name: string }; month: string; prior_month: string;
  summary: Record<string, number>; markets: Record<string, unknown>[]; note: string; could_not_verify: string; calls: Call[];
};
export type Agency = { agency_id: number; agency_name: string; agency_type: string; region: string; account_manager: string };
export type Definitions = {
  kpis: { kpi: string; display_name: string; definition_en: string; metric_view_expr: string; dax_twin: string; twin_sql: string; twin_sql_retired?: string | null; retired_note?: string | null }[];
  parity: { run_id: string; run_at: string; kpis: number; rows: number; drift: number; grid: Record<string, Record<string, string>>; drifting: Record<string, unknown>[]; source: string } | null;
  runs: { run_id: string; run_at: string; kpis: number; rows: number; drift: number }[];
};

export type RunStatus = "running" | "needs_approval" | "approved" | "rejected" | "failed" | "superseded";
export type ItemStatus = "draft" | "approved" | "rejected" | "superseded";
export type AgentScope = { manager?: string; region?: string; month?: string; market?: string };
export type AgentStep = { key: string; title: string; sub: string };
export type Progress = { done: number; total: number; text: string; phase: "facts" | "draft" | "check" | "done" | null; item: string | null };
export type AgentDef = {
  key: string; name: string; summary: string; one_liner: string; cadence: string; steps: AgentStep[];
  reads: string[]; writes: string[]; approver: string; scope_kind: "manager" | "region" | "market";
  last_run: { run_id: string; status: RunStatus; created_at: string } | null; waiting: number; running: { run_id: string; progress: Progress } | null;
  pages: Page[];
};
export type PageVersion = { run_id: string; item_id: string; created_at: string; scope: AgentScope; status: ItemStatus; decided_at: string | null; decided_by: string | null };
/** The unit a person decides on: one per agent and title, its newest version on top and every earlier version as history. */
export type Page = {
  item_id: string; kind: string; title: string; subtitle: string; severity: Severity; summary: string; status: ItemStatus; decided_at: string | null; decided_by: string | null;
  run_id: string; created_at: string; scope: AgentScope; versions: PageVersion[];
};
export type AgentsCatalog = { agents: AgentDef[]; managers: string[]; markets: { market_id: number; market: string }[]; crm_label: string };
export type RunHeader = { run_id: string; agent: string; agent_name: string; scope: AgentScope; status: RunStatus; created_at: string; finished_at: string | null; items: number; needs_approval: number };
export type Severity = "ok" | "watch" | "risk" | null;
export type ItemFact = { name: string; label: string; sql: string | null; source: string | null; rows: Record<string, unknown>[] };
export type ItemSource = { title: string; url: string; published: string | null; snippet: string };
export type ItemAction = { type: "email" | "crm" | "none"; subject: string; body: string; crm: { agency_id: number; activity_type: string; subject: string } | null };
export type ItemSection = { title: string; sentences: Sentence[] };
export type ItemEmail = { to: string; to_name: string; subject: string; sentences: Sentence[] };
export type Item = {
  item_id: string; kind: "page" | "clause" | "prospect" | "mismatch" | string; title: string; subtitle: string; severity: Severity; status: ItemStatus;
  summary: string; sections: ItemSection[]; email: ItemEmail | null; note: string | null; numbers_checked: number;
  sentences: Sentence[]; removed: { sentence: string; reason: string }[]; verified_text: string; draft: string; facts: ItemFact[]; sources: ItemSource[];
  action: ItemAction; decided_at: string | null; decided_by: string | null;
};
export type Run = {
  run_id: string; agent: string; agent_name: string; scope: AgentScope; status: RunStatus; requested_by: string | null; model: string; created_at: string; finished_at: string | null;
  progress: Progress; items: Item[]; error: string | null;
};

export type Turn = {
  role: "user" | "assistant"; text: string; at: number;
  answer?: Answer; brief?: Brief; error?: ApiError; steps?: Step[]; pending?: boolean;
};
export type Conversation = { id: string; title: string; createdAt: number; updatedAt: number; scope: Scope; genieConversationId?: string | null; turns: Turn[] };
