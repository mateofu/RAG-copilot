import {
  useCallback,
  useEffect,
  useMemo,
  useState,
  type PropsWithChildren,
} from "react";
import {
  SESSION_EXPIRED_EVENT,
  sessionStore,
} from "../../../core/auth/session-store";
import type { Identity, Membership } from "../domain/identity";
import { HttpAuthRepository } from "../infrastructure/http-auth-repository";
import { SessionContext, type SessionStatus } from "./session-context";

const repository = new HttpAuthRepository();
const ORGANIZATION_KEY = "rag-copilot.organization";

export function SessionProvider({ children }: PropsWithChildren) {
  const [status, setStatus] = useState<SessionStatus>("loading");
  const [identity, setIdentity] = useState<Identity | null>(null);
  const [organization, setOrganization] = useState<Membership | null>(null);

  const applyIdentity = useCallback((next: Identity) => {
    const preferred = sessionStorage.getItem(ORGANIZATION_KEY);
    const selected =
      next.memberships.find((item) => item.organizationId === preferred) ??
      next.memberships[0] ??
      null;
    setIdentity(next);
    setOrganization(selected);
    if (selected)
      sessionStorage.setItem(ORGANIZATION_KEY, selected.organizationId);
    setStatus("authenticated");
  }, []);

  useEffect(() => {
    if (!sessionStore.read()) {
      setStatus("anonymous");
      return;
    }
    repository
      .getIdentity()
      .then(applyIdentity)
      .catch(() => {
        sessionStore.clear();
        setStatus("anonymous");
      });
  }, [applyIdentity]);

  useEffect(() => {
    const expire = () => {
      setIdentity(null);
      setOrganization(null);
      setStatus("anonymous");
    };
    window.addEventListener(SESSION_EXPIRED_EVENT, expire);
    return () => window.removeEventListener(SESSION_EXPIRED_EVENT, expire);
  }, []);

  const login = useCallback(
    async (credentials: { email: string; password: string }) => {
      const tokens = await repository.login(credentials);
      sessionStore.write(tokens);
      try {
        applyIdentity(await repository.getIdentity());
      } catch (error) {
        sessionStore.clear();
        throw error;
      }
    },
    [applyIdentity],
  );

  const logout = useCallback(async () => {
    const tokens = sessionStore.read();
    try {
      if (tokens) await repository.logout(tokens.refreshToken);
    } finally {
      sessionStore.clear();
      sessionStorage.removeItem(ORGANIZATION_KEY);
      setIdentity(null);
      setOrganization(null);
      setStatus("anonymous");
    }
  }, []);

  const selectOrganization = useCallback(
    (id: string) => {
      const selected =
        identity?.memberships.find((item) => item.organizationId === id) ??
        null;
      setOrganization(selected);
      if (selected)
        sessionStorage.setItem(ORGANIZATION_KEY, selected.organizationId);
    },
    [identity],
  );

  const value = useMemo(
    () => ({
      status,
      identity,
      organization,
      login,
      logout,
      selectOrganization,
    }),
    [status, identity, organization, login, logout, selectOrganization],
  );

  return (
    <SessionContext.Provider value={value}>{children}</SessionContext.Provider>
  );
}
