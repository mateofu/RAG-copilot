export type Tokens = {
  accessToken: string;
  refreshToken: string;
};

const STORAGE_KEY = "rag-copilot.session";
export const SESSION_EXPIRED_EVENT = "rag-copilot:session-expired";

export const sessionStore = {
  read(): Tokens | null {
    const value = sessionStorage.getItem(STORAGE_KEY);
    if (!value) return null;
    try {
      return JSON.parse(value) as Tokens;
    } catch {
      sessionStorage.removeItem(STORAGE_KEY);
      return null;
    }
  },
  write(tokens: Tokens): void {
    sessionStorage.setItem(STORAGE_KEY, JSON.stringify(tokens));
  },
  clear(): void {
    sessionStorage.removeItem(STORAGE_KEY);
  },
  expire(): void {
    sessionStorage.removeItem(STORAGE_KEY);
    window.dispatchEvent(new Event(SESSION_EXPIRED_EVENT));
  },
};
