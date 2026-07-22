import { describe, expect, it } from "vitest";
import { normalizeUrl, parseFavoriteRequest } from "../src/validation";

describe("validation", () => {
  it("accepts valid favorite requests", () => {
    expect(parseFavoriteRequest({ item_id: "x_abcd1234", daily_page: "2026-07-22" }).item_id).toBe("x_abcd1234");
  });

  it("rejects missing item ids", () => {
    expect(() => parseFavoriteRequest({ daily_page: "2026-07-22" })).toThrow();
  });

  it("normalizes x mirror urls", () => {
    expect(normalizeUrl("https://fxtwitter.com/a/status/1?utm_source=x")).toBe("https://x.com/a/status/1");
  });
});

