const ACCESS_TOKEN_KEY = "wearverse.access_token";
const REFRESH_TOKEN_KEY = "wearverse.refresh_token";
const CUSTOMER_TOKEN_KEY = "wearverse.customer_token";

export interface LoginResponse {
  access_token: string;
  refresh_token: string;
  token_type: "bearer" | string;
  is_active: boolean;
}

function safeGet(store: Storage, key: string): string | null {
  try {
    return store.getItem(key);
  } catch {
    return null;
  }
}

function safeSet(store: Storage, key: string, value: string | null): void {
  try {
    if (value === null) store.removeItem(key);
    else store.setItem(key, value);
  } catch {
    // storage blocked (private window): the session just won't survive a reload
  }
}

/** Staff tokens. The POS keeps its login in localStorage so a counter survives a restart while offline. */
export function saveSession(tokens: LoginResponse, remember = false): void {
  const store = remember ? localStorage : sessionStorage;
  safeSet(store, ACCESS_TOKEN_KEY, tokens.access_token);
  safeSet(store, REFRESH_TOKEN_KEY, tokens.refresh_token);
}

export function getAccessToken(): string | null {
  return safeGet(sessionStorage, ACCESS_TOKEN_KEY) ?? safeGet(localStorage, ACCESS_TOKEN_KEY);
}

export function getRefreshToken(): string | null {
  return safeGet(sessionStorage, REFRESH_TOKEN_KEY) ?? safeGet(localStorage, REFRESH_TOKEN_KEY);
}

export function setAccessToken(token: string): void {
  if (safeGet(localStorage, ACCESS_TOKEN_KEY)) safeSet(localStorage, ACCESS_TOKEN_KEY, token);
  else safeSet(sessionStorage, ACCESS_TOKEN_KEY, token);
}

export function clearSession(): void {
  for (const store of [sessionStorage, localStorage]) {
    safeSet(store, ACCESS_TOKEN_KEY, null);
    safeSet(store, REFRESH_TOKEN_KEY, null);
  }
}

/** Website customer login (separate from staff). */
export function getCustomerToken(): string | null {
  return safeGet(localStorage, CUSTOMER_TOKEN_KEY);
}

export function setCustomerToken(token: string | null): void {
  safeSet(localStorage, CUSTOMER_TOKEN_KEY, token);
}
