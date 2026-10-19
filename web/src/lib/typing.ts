// An answer types itself out once it has been checked, the way a streamed reply reads, without ever showing a sentence
// before the verifier has seen it. The text is split around its checked numbers (proseParts); a string part is cut
// mid-way as the budget grows, a number appears whole the moment the budget reaches its end. Pure functions here, the
// hook below drives them with requestAnimationFrame.
import { useEffect, useState } from "react";
import type { ProsePart } from "./runs";

const len = (p: ProsePart) => (typeof p === "string" ? p.length : p.raw.length);

/** Every character the parts hold, numbers included. */
export function charCount(parts: ProsePart[]): number {
  return parts.reduce((n, p) => n + len(p), 0);
}

/** The parts visible with `budget` characters revealed. */
export function revealParts(parts: ProsePart[], budget: number): ProsePart[] {
  const out: ProsePart[] = [];
  let left = budget;
  for (const p of parts) {
    if (left <= 0) break;
    const n = len(p);
    if (typeof p === "string") {
      out.push(n <= left ? p : p.slice(0, left));
    } else if (n <= left) {
      out.push(p);
    } else break;
    left -= n;
  }
  return out;
}

/** How long typing `chars` characters takes: half a second at least, about 90 characters a tenth of a second after
 * that, and never more than two and a half seconds, so a long page does not make anyone wait. */
export function typingDuration(chars: number): number {
  return Math.min(2500, Math.max(500, Math.round(chars * 1.1)));
}

/** The number of characters revealed so far, climbing from zero to `total` over typingDuration(total). A change of
 * `key` restarts it; with `enabled` false everything shows at once. */
export function useTyping(total: number, key: string, enabled = true): { shown: number; done: boolean } {
  const [shown, setShown] = useState(enabled ? 0 : total);
  // no "already started" guard here: React's strict mode runs an effect twice on mount, and a guard would leave the
  // second run without an animation frame, so the text would never finish typing in development
  useEffect(() => {
    if (!enabled) {
      setShown(total);
      return;
    }
    const ms = typingDuration(total);
    const t0 = performance.now();
    let raf = 0;
    const tick = (now: number) => {
      const t = Math.min(1, (now - t0) / ms);
      setShown(Math.round(total * t));
      if (t < 1) raf = requestAnimationFrame(tick);
    };
    setShown(0);
    raf = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf);
  }, [total, key, enabled]);
  return { shown: enabled ? shown : total, done: !enabled || shown >= total };
}
