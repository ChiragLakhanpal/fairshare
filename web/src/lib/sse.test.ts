import { describe, expect, it } from "vitest";
import { parseSse } from "./sse";

const stream = [
  "id: 1\r\nevent: status\r\ndata: {\"type\":\"status\",\"phase\":\"sql\"}\r\n\r\n",
  ": ping\r\n\r\n",
  "id: 2\r\nevent: answer\r\ndata: {\"text\":\"Harbor sold $330K.\"}\r\n\r\n",
  "id: 3\nevent: done\ndata: {\"t_ms\":12}\n\n",
].join("");

function chunks(s: string, size: number): string[] {
  const out: string[] = [];
  for (let i = 0; i < s.length; i += size) out.push(s.slice(i, i + size));
  return out;
}

describe("parseSse", () => {
  it("yields ordered events whatever the chunk boundaries", () => {
    for (const size of [1, 3, 7, 50, 1000]) {
      const seen: { event: string; data: unknown }[] = [];
      const push = parseSse((e) => seen.push(e));
      for (const c of chunks(stream, size)) push(c);
      push(null);
      expect(seen.map((e) => e.event)).toEqual(["status", "answer", "done"]);
      expect(seen[1].data).toEqual({ text: "Harbor sold $330K." });
      expect(seen[2].data).toEqual({ t_ms: 12 });
    }
  });

  it("ignores comments and keeps multi-line data", () => {
    const seen: { event: string; data: unknown }[] = [];
    const push = parseSse((e) => seen.push(e));
    push("event: answer\ndata: {\"a\":\ndata: 1}\n\n");
    push(null);
    expect(seen).toEqual([{ event: "answer", data: { a: 1 } }]);
  });
});
