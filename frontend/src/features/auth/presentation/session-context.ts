import { createContext, useContext } from "react";
import type { Credentials, Identity, Membership } from "../domain/identity";

export type SessionStatus = "loading" | "authenticated" | "anonymous";
export type SessionContextValue = {
  status: SessionStatus;
  identity: Identity | null;
  organization: Membership | null;
  login(credentials: Credentials): Promise<void>;
  logout(): Promise<void>;
  selectOrganization(id: string): void;
};

export const SessionContext = createContext<SessionContextValue | null>(null);

export function useSession(): SessionContextValue {
  const context = useContext(SessionContext);
  if (!context)
    throw new Error("useSession must be used inside SessionProvider");
  return context;
}
