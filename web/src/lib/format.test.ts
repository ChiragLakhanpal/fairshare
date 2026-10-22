import { describe, expect, it } from "vitest";
import { fairShareLine, greeting } from "./format";

describe("greeting", () => {
  it("follows the clock and takes a name", () => {
    expect(greeting(null, new Date(2026, 9, 14, 9))).toBe("Good morning.");
    expect(greeting("Matthew", new Date(2026, 9, 14, 15))).toBe("Good afternoon, Matthew.");
    expect(greeting(undefined, new Date(2026, 9, 14, 19))).toBe("Good evening.");
  });
});

describe("the breakdown's line on fair share under a why answer", () => {
  it("says a month whose seats repeat last year's has no seat comparison, and gives no dollar figure for it", () => {
    expect(fairShareLine({ seats_projected: true, fair_share_now_pct: 52.0, fair_share_prior_pct: 52.4, fair_share_effect: null }))
      .toBe("This month's seats repeat the same month last year until the DOT publishes them, so there is no seat comparison.");
  });
  it("still says how fair share moved, and what the seat shares alone are worth, for a month the DOT has published", () => {
    expect(fairShareLine({ seats_projected: false, fair_share_now_pct: 40.1, fair_share_prior_pct: 40.1, fair_share_effect: 0 }))
      .toBe("Fair share did not move, so AA's own capacity explains none of it.");
    expect(fairShareLine({ seats_projected: false, fair_share_now_pct: 54.3, fair_share_prior_pct: 53.7, fair_share_effect: 2420 }))
      .toBe("Fair share moved up 0.6 points. Changes in AA's seat shares alone are worth $2K.");
    expect(fairShareLine({ fair_share_now_pct: 54.3, fair_share_prior_pct: 53.7, fair_share_effect: 2420 }), "a row from before the flag")
      .toBe("Fair share moved up 0.6 points. Changes in AA's seat shares alone are worth $2K.");
  });
});
