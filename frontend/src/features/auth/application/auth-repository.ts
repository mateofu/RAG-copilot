import type { Tokens } from "../../../core/auth/session-store";
import type { Credentials, Identity } from "../domain/identity";

export interface AuthRepository {
  login(credentials: Credentials): Promise<Tokens>;
  getIdentity(): Promise<Identity>;
  logout(refreshToken: string): Promise<void>;
}
