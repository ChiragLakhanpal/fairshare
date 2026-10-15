import { beforeEach, describe, expect, it } from "vitest";
import { createStore, groupByRecency, type Conversation } from "./store";

const DAY = 86_400_000;
const now = Date.parse("2026-10-14T15:00:00Z");

function conv(id: string, updatedAt: number): Conversation {
  return { id, title: id, createdAt: updatedAt, updatedAt, scope: { region: "All", month: "2026-09" }, turns: [] };
}

describe("groupByRecency", () => {
  it("buckets Today, Yesterday, Last week and Older, newest first", () => {
    const list = [conv("a", now - 1000), conv("b", now - DAY), conv("c", now - 3 * DAY), conv("d", now - 20 * DAY), conv("e", now - 10)];
    const groups = groupByRecency(list, now);
    expect(groups.map((g) => [g.label, g.items.map((c) => c.id)])).toEqual([
      ["Today", ["e", "a"]],
      ["Yesterday", ["b"]],
      ["Last week", ["c"]],
      ["Older", ["d"]],
    ]);
  });
});

describe("store", () => {
  const mem = new Map<string, string>();
  const storage = {
    getItem: (k: string) => mem.get(k) ?? null,
    setItem: (k: string, v: string) => void mem.set(k, v),
    removeItem: (k: string) => void mem.delete(k),
  };
  beforeEach(() => mem.clear());

  it("starts on the summary with no conversation and persists what changes", () => {
    const s = createStore(storage);
    expect(s.get().summaryExpanded).toBe(true);
    expect(s.get().activeId).toBeNull();
    const id = s.startConversation("Why is Harbor down?", { region: "All", month: "2026-09" });
    expect(s.get().activeId).toBe(id);
    expect(s.get().summaryExpanded).toBe(false);
    s.addTurn(id, { role: "assistant", text: "Harbor lost share.", at: now });
    const again = createStore(storage);
    expect(again.get().conversations[0].turns.map((t) => t.text)).toEqual(["Why is Harbor down?", "Harbor lost share."]);
    expect(again.get().conversations[0].title).toBe("Why is Harbor down?");
  });

  it("keeps at most fifty conversations and a remembered sidebar state", () => {
    const s = createStore(storage);
    for (let i = 0; i < 55; i++) s.startConversation(`q${i}`, { region: "All", month: "2026-09" });
    expect(s.get().conversations.length).toBe(50);
    expect(s.get().conversations[0].title).toBe("q54");
    s.setSidebarCollapsed(true);
    expect(createStore(storage).get().sidebarCollapsed).toBe(true);
  });

  it("new chat returns to the summary and folding is explicit", () => {
    const s = createStore(storage);
    const id = s.startConversation("q", { region: "All", month: "2026-09" });
    s.setSummaryExpanded(true);
    expect(s.get().summaryExpanded).toBe(true);
    s.newChat();
    expect(s.get().activeId).toBeNull();
    expect(s.get().summaryExpanded).toBe(true);
    expect(s.get().conversations[0].id).toBe(id);
  });

  it("a turn still pending in storage becomes an error after a reload", () => {
    const s = createStore(storage);
    const id = s.startConversation("q", { region: "All", month: "2026-09" });
    s.addTurn(id, { role: "assistant", text: "", at: now, pending: true, steps: [] });
    const again = createStore(storage).get().conversations[0].turns[1];
    expect(again.pending).toBe(false);
    expect(again.error?.code).toBe("reload");
  });
});
