import { readSse } from "./sse";
import type { Agency, AgentScope, AgentsCatalog, Answer, ApiError, Brief, Definitions, Evals, Explain, Item, Me, Run, Scope, Step, Summary } from "./types";

async function get<T>(url: string): Promise<T> {
  const r = await fetch(url, { headers: { Accept: "application/json" } });
  if (!r.ok) throw await asError(r);
  return (await r.json()) as T;
}
async function post<T>(url: string, body: unknown): Promise<T> {
  const r = await fetch(url, { method: "POST", headers: { "Content-Type": "application/json", Accept: "application/json" }, body: JSON.stringify(body) });
  if (!r.ok) throw await asError(r);
  return (await r.json()) as T;
}
async function asError(r: Response): Promise<ApiError> {
  try {
    const j = (await r.json()) as ApiError & Record<string, unknown>;
    return { ...j, code: j.code ?? String(r.status), message: j.message ?? r.statusText };
  } catch {
    return { code: String(r.status), message: r.statusText };
  }
}

export const api = {
  me: () => get<Me>("/api/me"),
  agencies: () => get<Agency[]>("/api/agencies"),
  summary: (s: Scope) => get<Summary>(`/api/summary?region=${encodeURIComponent(s.region)}&month=${encodeURIComponent(s.month)}`),
  explain: (agency_id: number, month: string) => get<Explain>(`/api/explain?agency_id=${agency_id}&month=${encodeURIComponent(month)}`),
  agreements: (agency_id: number | null, topic: string) =>
    get<{ hits: { file: string; page: number; text: string; score: number }[] }>(`/api/agreements?topic=${encodeURIComponent(topic)}${agency_id ? `&agency_id=${agency_id}` : ""}`),
  definitions: () => get<Definitions>("/api/definitions"),
  evals: () => get<Evals>("/api/evals"),
  brief: (s: Scope, writer: "guarded" | "unguarded" | "template" = "guarded") => post<Brief>("/api/brief", { ...s, writer }),
  approveBrief: (run_id: string, text?: string) => post<Brief>(`/api/brief/${run_id}/approve`, text ? { text } : {}),
  getBrief: (run_id: string) => get<Brief>(`/api/brief/${run_id}`),
  agents: () => get<AgentsCatalog>("/api/agents"),
  runAgent: (key: string, scope: AgentScope, writer?: "guarded" | "template") => post<Run>(`/api/agents/${encodeURIComponent(key)}/run`, { scope, ...(writer ? { writer } : {}) }),
  run: (run_id: string) => get<Run>(`/api/agents/runs/${encodeURIComponent(run_id)}`),
  approveItem: (run_id: string, item_id: string, text?: string) => post<Item>(`/api/agents/runs/${encodeURIComponent(run_id)}/items/${encodeURIComponent(item_id)}/approve`, text ? { text } : {}),
  rejectItem: (run_id: string, item_id: string) => post<Item>(`/api/agents/runs/${encodeURIComponent(run_id)}/items/${encodeURIComponent(item_id)}/reject`, {}),
};

export type AskHandlers = { onStep: (s: Step) => void; onTool?: (c: unknown) => void; onAnswer: (a: Answer) => void; onError: (e: ApiError) => void };

/** The browser's record of the previous answer, so "what checks did you perform?" is answered without re-running a query. */
export type LastAnswer = { calls: Record<string, unknown>[]; removed: { sentence: string; reason: string }[]; verified_numbers: number; sources: string[] };
export function lastAnswerOf(a: Answer | undefined | null): LastAnswer | null {
  if (!a || a.kind === "meta" || a.kind === "general") return null;
  const shown = a.sentences.filter((s) => s.status !== "flagged");
  return {
    calls: a.calls.slice(0, 20).map((c) => ({ tool: c.tool, args: c.args, sql: c.sql, rows: c.rows, note: c.note, genie: c.genie })),
    removed: a.removed.slice(0, 20), verified_numbers: shown.reduce((n, s) => n + (s.numbers?.length ?? 0), 0), sources: a.sources.slice(0, 20),
  };
}

export async function ask(
  body: { question: string; history: { role: "user" | "assistant"; text: string }[]; genie_conversation_id?: string | null; scope?: Scope; last_answer?: LastAnswer | null },
  h: AskHandlers,
  signal: AbortSignal,
): Promise<void> {
  const r = await fetch("/api/ask", { method: "POST", headers: { "Content-Type": "application/json", Accept: "text/event-stream" }, body: JSON.stringify(body), signal });
  if (!r.ok) {
    h.onError(await asError(r));
    return;
  }
  await readSse(r, (e) => {
    const d = e.data as Record<string, unknown>;
    if (e.event === "status") h.onStep(d as unknown as Step);
    else if (e.event === "tool") h.onTool?.(d);
    else if (e.event === "answer") h.onAnswer(d as unknown as Answer);
    else if (e.event === "error") h.onError(d as unknown as ApiError);
  });
}
