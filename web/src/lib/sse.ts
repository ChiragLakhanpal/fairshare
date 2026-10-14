// Server-Sent Events over fetch (POST bodies, AbortController). EventSource cannot POST, so the stream is read by hand.
export type SseEvent = { event: string; data: unknown; id?: string };

export function parseSse(onEvent: (e: SseEvent) => void): (chunk: string | null) => void {
  let buf = "";
  let event = "";
  let id: string | undefined;
  let data: string[] = [];

  const flush = () => {
    if (event) {
      const raw = data.join("\n");
      let parsed: unknown = null;
      try {
        parsed = raw ? JSON.parse(raw) : null;
      } catch {
        parsed = raw;
      }
      onEvent({ event, data: parsed, id });
    }
    event = "";
    id = undefined;
    data = [];
  };

  const line = (l: string) => {
    if (l === "") return flush();
    if (l.startsWith(":")) return;
    const i = l.indexOf(":");
    const field = i < 0 ? l : l.slice(0, i);
    let value = i < 0 ? "" : l.slice(i + 1);
    if (value.startsWith(" ")) value = value.slice(1);
    if (field === "event") event = value;
    else if (field === "data") data.push(value);
    else if (field === "id") id = value;
  };

  return (chunk) => {
    if (chunk === null) {
      if (buf) line(buf.replace(/\r$/, ""));
      buf = "";
      flush();
      return;
    }
    buf += chunk;
    for (;;) {
      const m = /\r\n|\n|\r/.exec(buf);
      if (!m) break;
      if (m[0] === "\r" && m.index === buf.length - 1) break; // a \r at the end may be half of \r\n
      line(buf.slice(0, m.index));
      buf = buf.slice(m.index + m[0].length);
    }
  };
}

export async function readSse(res: Response, onEvent: (e: SseEvent) => void): Promise<void> {
  if (!res.body) throw new Error("The server sent no stream.");
  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  const push = parseSse(onEvent);
  for (;;) {
    const { value, done } = await reader.read();
    if (done) break;
    push(decoder.decode(value, { stream: true }));
  }
  push(null);
}
