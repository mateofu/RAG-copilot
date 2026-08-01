import { apiRequest } from "../../../core/http/http-client";
import type { Tokens } from "../../../core/auth/session-store";
import type { AuthRepository } from "../application/auth-repository";
import type { Credentials, Identity } from "../domain/identity";
import { identitySchema, tokenSchema } from "./auth-schemas";

type TokenDto = { accessToken: string; refreshToken: string };

export class HttpAuthRepository implements AuthRepository {
  async login(credentials: Credentials): Promise<Tokens> {
    return apiRequest<TokenDto>(
      "/auth/login",
      { method: "POST", body: JSON.stringify(credentials) },
      tokenSchema,
    );
  }

  getIdentity(): Promise<Identity> {
    return apiRequest<Identity>("/auth/me", {}, identitySchema);
  }

  logout(refreshToken: string): Promise<void> {
    return apiRequest<void>("/auth/logout", {
      method: "POST",
      body: JSON.stringify({ refreshToken }),
    });
  }
}
