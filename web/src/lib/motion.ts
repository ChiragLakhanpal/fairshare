// The app's motion vocabulary in one place: enter with ease-out in about a fifth of a second, leave faster, springs with
// no bounce for anything that changes position, and a number that moves to its new value instead of jumping. The pure
// parts are tested in motion.test.ts; every component that uses them also checks useReducedMotion first.
import { useEffect, useRef, useState } from "react";
import type { DelegateView, Mode } from "./store";

export const SPRING = { type: "spring" as const, bounce: 0, duration: 0.35 };
export const EASE_OUT: [number, number, number, number] = [0.2, 0.8, 0.2, 1];
export const EASE_IN: [number, number, number, number] = [0.4, 0, 1, 1];
export const ENTER = { duration: 0.22, ease: EASE_OUT };
export const LEAVE = { duration: 0.12, ease: EASE_IN };

/** Which side a view comes in from: Delegate sits to the right of Ask in the switch, so it arrives from the right. */
export function slideDirection(mode: Mode): 1 | -1 {
  return mode === "delegate" ? 1 : -1;
}

/** How deep a Delegate view is: the overview, one agent, one page. Deeper views arrive from the right. */
export function depthOf(v: DelegateView): 0 | 1 | 2 {
  return v.agent ? (v.itemId ? 2 : 1) : 0;
}

/** A view arriving or leaving: a short move along a takeoff diagonal, in from one side and slightly below, out the other
 * way and slightly above. `custom` is the direction, +1 from the right. */
export function slideVariants(reduced: boolean | null) {
  if (reduced) return { initial: { opacity: 1 }, animate: { opacity: 1 }, exit: { opacity: 1, transition: { duration: 0 } } };
  return {
    initial: (dir: number) => ({ opacity: 0, x: 12 * dir, y: 6 }),
    animate: { opacity: 1, x: 0, y: 0, transition: ENTER },
    exit: (dir: number) => ({ opacity: 0, x: -8 * dir, y: -4, transition: LEAVE }),
  };
}

/** A row or a tile settling into place. */
export const rise = { initial: { opacity: 0, y: 6 }, animate: { opacity: 1, y: 0 } };

/** The delay before the i-th row rises, so a list reads top to bottom; it stops growing after eight rows. */
export function stagger(i: number, step = 0.035, max = 8): number {
  return Math.min(i, max) * step;
}

export const easeOut = (t: number) => 1 - Math.pow(1 - t, 3);

/** Where a number is between its old and new value at progress t, fastest at the start. */
export function tweenAt(from: number, to: number, t: number): number {
  return from + (to - from) * easeOut(Math.min(1, Math.max(0, t)));
}

/** A number that moves to its new value over `ms` instead of jumping. The first value shows at once; nothing counts up
 * from zero. With `enabled` false (reduced motion) it jumps. */
export function useTween(value: number | null, ms = 450, enabled = true): number | null {
  const [shown, setShown] = useState(value);
  const shownRef = useRef(value);
  useEffect(() => {
    const from = shownRef.current;
    if (!enabled || value === null || from === null || from === value) {
      shownRef.current = value;
      setShown(value);
      return;
    }
    const t0 = performance.now();
    let raf = 0;
    const tick = (now: number) => {
      const t = Math.min(1, (now - t0) / ms);
      const v = t >= 1 ? value : tweenAt(from, value, t);
      shownRef.current = v;
      setShown(v);
      if (t < 1) raf = requestAnimationFrame(tick);
    };
    raf = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf);
  }, [value, ms, enabled]);
  return shown;
}
