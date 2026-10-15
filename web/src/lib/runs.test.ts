import { describe, expect, it } from "vitest";
import { decidedLine, draftCount, progressText, scopeLabel, statusLabel, whenLabel } from "./runs";
import type { Item } from "./types";

const item = (status: Item["status"]): Item => ({
  item_id: status, kind: "page", title: "t", subtitle: "s", severity: null, status, sentences: [], removed: [], verified_text: "", draft: "",
  facts: [], sources: [], action: { type: "none", subject: "", body: "", crm: null }, decided_at: "2026-10-14T21:03:10", decided_by: "dana@example.com",
});

describe("runs helpers", () => {
  it("labels every status in plain words", () => {
    expect(statusLabel("running")).toBe("Running");
    expect(statusLabel("needs_approval")).toBe("Needs approval");
    expect(statusLabel("approved")).toBe("Approved");
    expect(statusLabel("rejected")).toBe("Rejected");
    expect(statusLabel("failed")).toBe("Failed");
  });

  it("counts drafts and writes the progress line from the status", () => {
    const items = [item("draft"), item("approved"), item("draft")];
    expect(draftCount(items)).toBe(2);
    expect(progressText({ status: "running", progress: { done: 1, total: 4, text: "" }, items: [] })).toBe("1 of 4 written.");
    expect(progressText({ status: "running", progress: { done: 0, total: 0, text: "" }, items: [] })).toBe("Starting.");
    expect(progressText({ status: "running", progress: { done: 2, total: 4, text: "Writing Harbor's page." }, items: [] })).toBe("Writing Harbor's page.");
    expect(progressText({ status: "needs_approval", progress: { done: 3, total: 3, text: "" }, items })).toBe("2 of 3 waiting for approval.");
    expect(progressText({ status: "approved", progress: { done: 3, total: 3, text: "" }, items: [item("approved")] })).toBe("Every item has been decided.");
    expect(progressText({ status: "failed", progress: { done: 1, total: 3, text: "" }, items: [] })).toBe("This run failed.");
  });

  it("names a scope by its kind", () => {
    expect(scopeLabel({ manager: "Marcus Lee", month: "2026-09" })).toBe("Marcus Lee, September 2026");
    expect(scopeLabel({ region: "East", month: "2026-09" })).toBe("East region, September 2026");
    expect(scopeLabel({ region: "All", month: "2026-09" })).toBe("All regions, September 2026");
    expect(scopeLabel({ market: "CLT-LGA" })).toBe("CLT-LGA");
    expect(scopeLabel({})).toBe("");
  });

  it("writes the decided line and a readable time", () => {
    expect(whenLabel("2026-10-14T21:03:10")).toBe("October 14 at 9:03 PM");
    expect(decidedLine(item("approved"))).toBe("Approved by dana@example.com on October 14 at 9:03 PM.");
    expect(decidedLine({ ...item("rejected"), decided_by: null })).toBe("Rejected on October 14 at 9:03 PM.");
  });
});
