import { describe, expect, it, vi } from "vitest";
import { sessionStore } from "../auth/session-store";
import { apiRequest } from "./http-client";
import { z } from "zod";

describe("apiRequest", () => {
  it("adds tenant and authorization headers", async () => {
    sessionStore.write({ accessToken: "access", refreshToken: "refresh" });
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ ok: true }), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      }),
    );
    vi.stubGlobal("fetch", fetchMock);

    await apiRequest("/documents", { organizationId: "organization" });

    const firstCall = fetchMock.mock.calls[0];
    expect(firstCall).toBeDefined();
    const headers = (firstCall![1] as RequestInit).headers as Headers;
    expect(headers.get("Authorization")).toBe("Bearer access");
    expect(headers.get("X-Organization-Id")).toBe("organization");
  });

  it("rotates the session once and retries an unauthorized request", async () => {
    sessionStore.write({ accessToken: "expired", refreshToken: "refresh" });
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(new Response(null, { status: 401 }))
      .mockResolvedValueOnce(
        new Response(
          JSON.stringify({
            accessToken: "new-access",
            refreshToken: "new-refresh",
          }),
          { status: 200, headers: { "Content-Type": "application/json" } },
        ),
      )
      .mockResolvedValueOnce(
        new Response(JSON.stringify({ value: 42 }), {
          status: 200,
          headers: { "Content-Type": "application/json" },
        }),
      );
    vi.stubGlobal("fetch", fetchMock);

    await expect(apiRequest<{ value: number }>("/documents")).resolves.toEqual({
      value: 42,
    });
    expect(sessionStore.read()?.accessToken).toBe("new-access");
    expect(fetchMock).toHaveBeenCalledTimes(3);
  });

  it("expires the reactive session when refresh is rejected", async () => {
    sessionStore.write({ accessToken: "expired", refreshToken: "invalid" });
    const expired = vi.fn();
    window.addEventListener("rag-copilot:session-expired", expired);
    vi.stubGlobal(
      "fetch",
      vi
        .fn()
        .mockResolvedValueOnce(new Response(null, { status: 401 }))
        .mockResolvedValueOnce(new Response(null, { status: 401 })),
    );

    await expect(apiRequest("/documents")).rejects.toThrow("Tu sesión expiró");
    expect(sessionStore.read()).toBeNull();
    expect(expired).toHaveBeenCalledOnce();
  });

  it("rejects successful responses that violate their runtime contract", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        new Response(JSON.stringify({ total: "not-a-number" }), {
          status: 200,
          headers: { "Content-Type": "application/json" },
        }),
      ),
    );

    await expect(
      apiRequest("/documents", {}, z.object({ total: z.number() })),
    ).rejects.toMatchObject({
      status: 502,
      code: "invalid_api_response",
    });
  });
});
