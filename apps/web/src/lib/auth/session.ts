const ACCESS_TOKEN_KEY = "fashionos.access_token";
const REFRESH_TOKEN_KEY = "fashionos.refresh_token";

export interface LoginResponse {
  access_token: string;
  refresh_token: string;
  token_type: "bearer" | string;
  is_active: boolean;
}

/** Keep tokens for this browser tab/session rather than persisting them indefinitely. */
export function saveSession(tokens: LoginResponse): void {
  sessionStorage.setItem(ACCESS_TOKEN_KEY, tokens.access_token);
  sessionStorage.setItem(REFRESH_TOKEN_KEY, tokens.refresh_token);
}

export function getAccessToken(): string | null {
  return sessionStorage.getItem(ACCESS_TOKEN_KEY);
}

export function getRefreshToken(): string | null {
  return sessionStorage.getItem(REFRESH_TOKEN_KEY);
}

export function clearSession(): void {
  sessionStorage.removeItem(ACCESS_TOKEN_KEY);
  sessionStorage.removeItem(REFRESH_TOKEN_KEY);
}
