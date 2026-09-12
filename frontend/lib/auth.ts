// Session storage helpers. This is a real browser app (not a sandboxed
// artifact), so localStorage is the right place for the session JWT.

export type User = {
  id: string;
  email: string;
  github_login?: string | null;
  plan?: string;
  is_admin?: boolean;
  is_agency?: boolean;
  notify_daily_status?: boolean;
  privacy_policy_version?: string | null;
  terms_version?: string | null;
  legal_consent_accepted_at?: string | null;
  consent_required?: boolean;
};

const TOKEN_KEY = "autofix_token";
const USER_KEY = "autofix_user";

/**
 * Ensure a session JWT exists — resolves if a token is already stored.
 * There is no anonymous/demo session: users sign in with GitHub and the
 * dashboard redirects to /login when no session exists.
 */
export async function ensureSession(): Promise<void> {
  if (typeof window === "undefined") return;
  // No-op: callers use getToken()/isAuthed() to gate the dashboard.
}

export function storeSession(token: string, user: User): void {
  if (typeof window === "undefined") return;
  localStorage.setItem(TOKEN_KEY, token);
  localStorage.setItem(USER_KEY, JSON.stringify(user));
}

export function getToken(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem(TOKEN_KEY);
}

export function getUser(): User | null {
  if (typeof window === "undefined") return null;
  const raw = localStorage.getItem(USER_KEY);
  if (!raw) return null;
  try {
    return JSON.parse(raw) as User;
  } catch {
    return null;
  }
}

export function clearSession(): void {
  if (typeof window === "undefined") return;
  localStorage.removeItem(TOKEN_KEY);
  localStorage.removeItem(USER_KEY);
}

export function isAuthed(): boolean {
  return !!getToken();
}
