import { describe, expect, it } from "vitest";
import { greeting } from "./format";

describe("greeting", () => {
  it("follows the clock and takes a name", () => {
    expect(greeting(null, new Date(2026, 9, 14, 9))).toBe("Good morning.");
    expect(greeting("Matthew", new Date(2026, 9, 14, 15))).toBe("Good afternoon, Matthew.");
    expect(greeting(undefined, new Date(2026, 9, 14, 19))).toBe("Good evening.");
  });
});
