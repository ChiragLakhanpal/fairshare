// The browser's memory: conversations in localStorage per viewer, the sidebar's collapsed state, and whether the
// summary is unfolded. One small store on useSyncExternalStore; no state library.
import { useSyncExternalStore } from "react";
import type { Conversation, Scope, Turn } from "./types";

export type { Conversation, Scope, Turn };

export type State = { conversations: Conversation[]; activeId: string | null; summaryExpanded: boolean; sidebarCollapsed: boolean };

type Storage = { getItem(k: string): string | null; setItem(k: string, v: string): void; removeItem(k: string): void };
const KEY = "fairshare.conversations";
const SIDEBAR = "fairshare.sidebar";
const MAX = 50;
const DAY = 86_400_000;

function read<T>(storage: Storage, key: string, fallback: T): T {
  try {
    const raw = storage.getItem(key);
    return raw ? (JSON.parse(raw) as T) : fallback;
  } catch {
    return fallback;
  }
}
function write(storage: Storage, key: string, value: unknown) {
  try {
    storage.setItem(key, JSON.stringify(value));
  } catch {
    /* private mode or a full quota: the app still works for the session */
  }
}

export function createStore(storage: Storage) {
  let state: State = {
    conversations: read<Conversation[]>(storage, KEY, []),
    activeId: null,
    summaryExpanded: true,
    sidebarCollapsed: read<boolean>(storage, SIDEBAR, false),
  };
  const listeners = new Set<() => void>();
  const set = (patch: Partial<State>) => {
    state = { ...state, ...patch };
    if (patch.conversations) write(storage, KEY, state.conversations);
    if (patch.sidebarCollapsed !== undefined) write(storage, SIDEBAR, state.sidebarCollapsed);
    listeners.forEach((l) => l());
  };
  const update = (id: string, fn: (c: Conversation) => Conversation) =>
    set({ conversations: state.conversations.map((c) => (c.id === id ? fn(c) : c)).sort((a, b) => b.updatedAt - a.updatedAt) });

  return {
    get: () => state,
    subscribe: (l: () => void) => {
      listeners.add(l);
      return () => listeners.delete(l);
    },
    startConversation(question: string, scope: Scope): string {
      const now = Date.now();
      const id = now.toString(36) + Math.random().toString(36).slice(2, 7);
      const c: Conversation = { id, title: question.trim().slice(0, 60), createdAt: now, updatedAt: now, scope, turns: [{ role: "user", text: question, at: now }] };
      set({ conversations: [c, ...state.conversations].slice(0, MAX), activeId: id, summaryExpanded: false });
      return id;
    },
    addTurn(id: string, turn: Turn) {
      update(id, (c) => ({ ...c, updatedAt: Date.now(), turns: [...c.turns, turn] }));
    },
    patchTurn(id: string, index: number, patch: Partial<Turn>) {
      update(id, (c) => ({ ...c, turns: c.turns.map((t, i) => (i === index ? { ...t, ...patch } : t)) }));
    },
    setGenieConversation(id: string, genieConversationId: string | null) {
      update(id, (c) => ({ ...c, genieConversationId }));
    },
    setActive(id: string | null) {
      set({ activeId: id, summaryExpanded: id === null });
    },
    newChat() {
      set({ activeId: null, summaryExpanded: true });
    },
    remove(id: string) {
      set({ conversations: state.conversations.filter((c) => c.id !== id), activeId: state.activeId === id ? null : state.activeId });
    },
    setSummaryExpanded(v: boolean) {
      set({ summaryExpanded: v });
    },
    setSidebarCollapsed(v: boolean) {
      set({ sidebarCollapsed: v });
    },
  };
}
export type Store = ReturnType<typeof createStore>;

export function groupByRecency(list: Conversation[], now = Date.now()) {
  const groups: { label: string; items: Conversation[] }[] = [
    { label: "Today", items: [] }, { label: "Yesterday", items: [] }, { label: "Last week", items: [] }, { label: "Older", items: [] },
  ];
  const startOfDay = (t: number) => Math.floor(t / DAY) * DAY;
  const today = startOfDay(now);
  for (const c of [...list].sort((a, b) => b.updatedAt - a.updatedAt)) {
    const day = startOfDay(c.updatedAt);
    const bucket = day >= today ? 0 : day >= today - DAY ? 1 : day >= today - 7 * DAY ? 2 : 3;
    groups[bucket].items.push(c);
  }
  return groups.filter((g) => g.items.length > 0);
}

const browserStorage: Storage = typeof localStorage !== "undefined" ? localStorage : { getItem: () => null, setItem: () => {}, removeItem: () => {} };
export const store = createStore(browserStorage);

export function useStore<T>(select: (s: State) => T): T {
  return useSyncExternalStore(store.subscribe, () => select(store.get()), () => select(store.get()));
}
