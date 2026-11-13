const ACCESS_TOKEN_KEY = "wearverse.access_token";
const REFRESH_TOKEN_KEY = "wearverse.refresh_token";
const CUSTOMER_TOKEN_KEY = "wearverse.customer_token";
const STAFF_ROLE_KEY = "wearverse.staff_role";

/** Roles that use the back office. Everyone else (Employee) only has their own profile. */
export const BACK_OFFICE_ROLES = ["Owner", "Admin", "Manager", "Cashier", "Accountant", "OnlineStaff", "Supervisor"];

export interface LoginResponse {
  access_token: string;
  refresh_token: string;
  token_type: "bearer" | string;
  is_active: boolean;
  role?: string | null;
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
  safeSet(store, STAFF_ROLE_KEY, tokens.role ?? null);
}

/** Role saved at sign-in (for links only; the server always checks the real role). */
export function getStaffRole(): string | null {
  return safeGet(sessionStorage, STAFF_ROLE_KEY) ?? safeGet(localStorage, STAFF_ROLE_KEY);
}

/** Where a staff member's own home is: their work screen, or their profile for roles without back office. */
export function staffHome(role: string | null | undefined): string {
  if (!role || !BACK_OFFICE_ROLES.includes(role)) return "/me";
  return ({ Cashier: "/pos", OnlineStaff: "/backoffice/online-orders", Supervisor: "/backoffice/fall-pico",
            Accountant: "/backoffice/tally" } as Record<string, string>)[role] ?? "/backoffice";
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
    safeSet(store, STAFF_ROLE_KEY, null);
  }
}

/** Website customer login (separate from staff). */
export function getCustomerToken(): string | null {
  return safeGet(localStorage, CUSTOMER_TOKEN_KEY);
}

export function setCustomerToken(token: string | null): void {
  safeSet(localStorage, CUSTOMER_TOKEN_KEY, token);
}
