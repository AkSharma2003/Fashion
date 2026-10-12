const API_BASE = import.meta.env.VITE_API_URL ?? "";
export const CUSTOMER_AUTH_CHANGE_EVENT = "wearverse:customer-auth-change";
const CUSTOMER_ACCESS_TOKEN_KEY = "wearverse_access_token";
const CUSTOMER_DATA_KEY = "wearverse_customer";

export interface Customer {
  id: string;
  full_name: string;
  email: string;
  phone_number: string;
}

interface CustomerAuthResponse {
  access_token: string;
  token_type: string;
  customer: Customer;
}

interface CustomerRegistration {
  full_name: string;
  email: string;
  phone_number: string;
  password: string;
}

async function sendCustomerAuthRequest(
  path: string,
  body: Record<string, string>,
): Promise<CustomerAuthResponse> {
  let response: Response;
  try {
    response = await fetch(`${API_BASE}/api/v1/auth/customer/${path}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
  } catch {
    throw new Error(
      "Can't reach the WearVerse API. Start the backend on port 8000 and make sure PostgreSQL is running.",
    );
  }

  const result = await response.json().catch(() => null) as
    | CustomerAuthResponse
    | { detail?: string }
    | null;

  if (!response.ok) {
    if (response.status >= 500 && (!result || !("detail" in result))) {
      throw new Error(
        "The API could not complete the request. Check that PostgreSQL is running and the database migration has been applied.",
      );
    }
    throw new Error(
      result && "detail" in result && result.detail
        ? result.detail
        : "We couldn't connect to your account. Please try again.",
    );
  }

  if (!result || !("access_token" in result) || !("customer" in result)) {
    throw new Error("The server returned an invalid account response.");
  }

  return result;
}

export function registerCustomer(data: CustomerRegistration) {
  return sendCustomerAuthRequest("register", data);
}

export function loginCustomer(identifier: string, password: string) {
  return sendCustomerAuthRequest("login", { identifier, password });
}

export function saveCustomerSession(auth: CustomerAuthResponse, rememberMe = false) {
  const persistentStorage = rememberMe ? window.localStorage : window.sessionStorage;
  const temporaryStorage = rememberMe ? window.sessionStorage : window.localStorage;

  temporaryStorage.removeItem(CUSTOMER_ACCESS_TOKEN_KEY);
  temporaryStorage.removeItem(CUSTOMER_DATA_KEY);
  persistentStorage.setItem(CUSTOMER_ACCESS_TOKEN_KEY, auth.access_token);
  persistentStorage.setItem(CUSTOMER_DATA_KEY, JSON.stringify(auth.customer));
  window.dispatchEvent(new Event(CUSTOMER_AUTH_CHANGE_EVENT));
}

export function hasCustomerSession() {
  return Boolean(getCustomerAccessToken());
}

export function getCustomerAccessToken() {
  return window.localStorage.getItem(CUSTOMER_ACCESS_TOKEN_KEY) ||
    window.sessionStorage.getItem(CUSTOMER_ACCESS_TOKEN_KEY);
}

export function getCustomerSession(): Customer | null {
  const rawCustomer = window.localStorage.getItem(CUSTOMER_DATA_KEY) ||
    window.sessionStorage.getItem(CUSTOMER_DATA_KEY);
  if (!rawCustomer) return null;

  try {
    return JSON.parse(rawCustomer) as Customer;
  } catch {
    return null;
  }
}

export async function updateCustomerProfile(profile: Omit<Customer, "id">) {
  const token = getCustomerAccessToken();
  if (!token) throw new Error("Please sign in again to update your profile.");

  const response = await fetch(`${API_BASE}/api/v1/auth/customer/me`, {
    method: "PATCH",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify(profile),
  });
  const result = await response.json().catch(() => null) as Customer | { detail?: string } | null;

  if (!response.ok) {
    throw new Error(
      result && "detail" in result && result.detail
        ? result.detail
        : "Couldn't save your profile. Please try again.",
    );
  }
  if (!result || !("id" in result)) throw new Error("The server returned an invalid profile.");

  const serialized = JSON.stringify(result);
  const storage = window.localStorage.getItem(CUSTOMER_ACCESS_TOKEN_KEY)
    ? window.localStorage
    : window.sessionStorage;
  storage.setItem(CUSTOMER_DATA_KEY, serialized);
  window.dispatchEvent(new Event(CUSTOMER_AUTH_CHANGE_EVENT));
  return result;
}

export function clearCustomerSession() {
  window.localStorage.removeItem(CUSTOMER_ACCESS_TOKEN_KEY);
  window.localStorage.removeItem(CUSTOMER_DATA_KEY);
  window.sessionStorage.removeItem(CUSTOMER_ACCESS_TOKEN_KEY);
  window.sessionStorage.removeItem(CUSTOMER_DATA_KEY);
  window.dispatchEvent(new Event(CUSTOMER_AUTH_CHANGE_EVENT));
}
