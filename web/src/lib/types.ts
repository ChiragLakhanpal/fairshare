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

export type Turn = {
  role: "user" | "assistant"; text: string; at: number;
  answer?: Answer; brief?: Brief; error?: ApiError; steps?: Step[]; pending?: boolean;
};
export type Conversation = { id: string; title: string; createdAt: number; updatedAt: number; scope: Scope; genieConversationId?: string | null; turns: Turn[] };
