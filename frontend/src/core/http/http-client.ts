import { config } from "../config";
import { sessionStore, type Tokens } from "../auth/session-store";
import { ApiError } from "./api-error";
import { z, type ZodType } from "zod";

type RequestOptions = RequestInit & {
  organizationId?: string;
  retry?: boolean;
};
type ErrorPayload = { detail?: { code?: string; message?: string } };

let refreshPromise: Promise<Tokens> | null = null;
const tokenSchema = z.object({
  accessToken: z.string().min(1),
  refreshToken: z.string().min(1),
});

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
  let refreshPayload: unknown;
  try {
    refreshPayload = await response.json();
  } catch {
    sessionStore.expire();
    throw new ApiError(
      502,
      "invalid_api_response",
      "La API devolvió una sesión ilegible.",
    );
  }
  const payload = tokenSchema.safeParse(refreshPayload);
  if (!payload.success) {
    sessionStore.expire();
    throw new ApiError(
      502,
      "invalid_api_response",
      "La API devolvió una sesión inválida.",
    );
  }
  const tokens = {
    accessToken: payload.data.accessToken,
    refreshToken: payload.data.refreshToken,
  };
  sessionStore.write(tokens);
  return tokens;
}

export async function apiRequest<T>(
  path: string,
  options: RequestOptions = {},
  schema?: ZodType<T>,
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
    return apiRequest<T>(path, { ...options, retry: false }, schema);
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
  let payload: unknown;
  try {
    payload = await response.json();
  } catch {
    throw new ApiError(
      502,
      "invalid_api_response",
      "La API devolvió una respuesta ilegible.",
    );
  }
  if (!schema) return payload as T;
  const parsed = schema.safeParse(payload);
  if (!parsed.success) {
    throw new ApiError(
      502,
      "invalid_api_response",
      "La API devolvió datos con un formato inesperado.",
    );
  }
  return parsed.data;
}
