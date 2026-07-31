import { config } from "../config";
import { sessionStore, type Tokens } from "../auth/session-store";
import { ApiError } from "./api-error";

type RequestOptions = RequestInit & {
  organizationId?: string;
  retry?: boolean;
};
type ErrorPayload = { detail?: { code?: string; message?: string } };

let refreshPromise: Promise<Tokens> | null = null;

async function refreshSession(): Promise<Tokens> {
  const current = sessionStore.read();
  if (!current) throw new ApiError(401, "session_expired", "Tu sesión expiró.");
  const response = await fetch(`${config.apiBaseUrl}/auth/refresh`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ refreshToken: current.refreshToken }),
  });
  if (!response.ok) {
    sessionStore.expire();
    throw new ApiError(
      401,
      "session_expired",
      "Tu sesión expiró. Ingresa nuevamente.",
    );
  }
  const payload = (await response.json()) as {
    accessToken: string;
    refreshToken: string;
  };
  const tokens = {
    accessToken: payload.accessToken,
    refreshToken: payload.refreshToken,
  };
  sessionStore.write(tokens);
  return tokens;
}

export async function apiRequest<T>(
  path: string,
  options: RequestOptions = {},
): Promise<T> {
  const { organizationId, retry = true, headers, ...init } = options;
  const tokens = sessionStore.read();
  const requestHeaders = new Headers(headers);
  if (!(init.body instanceof FormData))
    requestHeaders.set("Content-Type", "application/json");
  if (tokens)
    requestHeaders.set("Authorization", `Bearer ${tokens.accessToken}`);
  if (organizationId) requestHeaders.set("X-Organization-Id", organizationId);

  const response = await fetch(`${config.apiBaseUrl}${path}`, {
    ...init,
    headers: requestHeaders,
  });
  if (response.status === 401 && tokens && retry) {
    refreshPromise ??= refreshSession().finally(() => {
      refreshPromise = null;
    });
    await refreshPromise;
    return apiRequest<T>(path, { ...options, retry: false });
  }
  if (!response.ok) {
    let payload: ErrorPayload = {};
    try {
      payload = (await response.json()) as ErrorPayload;
    } catch {
      // The API may be unavailable or return a non-JSON proxy response.
    }
    throw new ApiError(
      response.status,
      payload.detail?.code ?? "request_failed",
      payload.detail?.message ?? "No fue posible completar la solicitud.",
    );
  }
  if (response.status === 204) return undefined as T;
  return response.json() as Promise<T>;
}
