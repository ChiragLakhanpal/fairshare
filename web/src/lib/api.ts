import { readSse } from "./sse";
import type { Agency, Answer, ApiError, Brief, Definitions, Explain, Me, Scope, Step, Summary } from "./types";

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
    const j = (await r.json()) as ApiError;
    return { code: j.code ?? String(r.status), message: j.message ?? r.statusText };
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
  brief: (s: Scope, writer: "guarded" | "unguarded" | "template" = "guarded") => post<Brief>("/api/brief", { ...s, writer }),
  approveBrief: (run_id: string) => post<{ run_id: string; status: string }>(`/api/brief/${run_id}/approve`, {}),
  getBrief: (run_id: string) => get<Brief>(`/api/brief/${run_id}`),
};

export type AskHandlers = { onStep: (s: Step) => void; onTool?: (c: unknown) => void; onAnswer: (a: Answer) => void; onError: (e: ApiError) => void };

export async function ask(
  body: { question: string; history: { role: "user" | "assistant"; text: string }[]; genie_conversation_id?: string | null; scope?: Scope },
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
