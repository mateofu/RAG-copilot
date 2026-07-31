import { describe, expect, it } from "vitest";
import { sessionStore } from "./session-store";

describe("sessionStore", () => {
  it("persists tokens only in session storage", () => {
    sessionStore.write({ accessToken: "access", refreshToken: "refresh" });

    expect(sessionStore.read()).toEqual({
      accessToken: "access",
      refreshToken: "refresh",
    });
    expect(localStorage.length).toBe(0);
  });

  it("removes malformed sessions", () => {
    sessionStorage.setItem("rag-copilot.session", "not-json");

    expect(sessionStore.read()).toBeNull();
    expect(sessionStorage.length).toBe(0);
  });
});
