import { useEffect, useState } from "react";
import { apiData } from "./api/client";
import { getCustomerToken, setCustomerToken } from "./auth/session";
import { clearLocalShopping, mergeOnSignIn, syncedThisVisit } from "./shoppingSync";

/** The signed-in website customer: profile, photo, address book. */

export type CustomerProfile = {
  id: string; full_name: string; email: string | null; phone_number: string;
  profile_photo_url: string | null; is_verified: boolean; member_since: string | null;
};

export type Address = {
  id: string; name: string; phone: string; line1: string; line2: string | null; landmark: string | null;
  city: string; state: string; pincode: string; kind: "HOME" | "WORK" | "OTHER"; is_default: boolean;
};

export type AddressInput = Omit<Address, "id" | "is_default"> & { is_default?: boolean };

const CACHE_KEY = "wearverse.customer_profile";
const EVENT = "wearverse:profile-updated";
const API_BASE = (import.meta.env.VITE_API_URL ?? "").replace(/\/$/, "");

/** Call the API as the customer (their token, not a staff token). */
export function customerApi<T>(path: string, init: RequestInit = {}): Promise<T> {
  const headers = new Headers(init.headers);
  const token = getCustomerToken();
  if (token) headers.set("Authorization", `Bearer ${token}`);
  if (init.body !== undefined && !(init.body instanceof FormData)) headers.set("Content-Type", "application/json");
  return apiData<T>(path, { ...init, headers });
}

/** Photos saved by the API in local development come back as "/media/..." paths. */
export function mediaUrl(url: string | null | undefined): string | null {
  if (!url) return null;
  return url.startsWith("/") ? `${API_BASE}${url}` : url;
}

export function initials(name: string | null | undefined): string {
  const parts = (name ?? "").trim().split(/\s+/).filter(Boolean);
  return (parts[0]?.[0] ?? "?").toUpperCase();
}

function readCache(): CustomerProfile | null {
  try {
    const raw = localStorage.getItem(CACHE_KEY);
    return raw ? (JSON.parse(raw) as CustomerProfile) : null;
  } catch {
    return null;
  }
}

/** Save the latest profile and tell the header (and other tabs of this page) to refresh. */
export function publishProfile(p: CustomerProfile | null): void {
  try {
    if (p) localStorage.setItem(CACHE_KEY, JSON.stringify(p));
    else localStorage.removeItem(CACHE_KEY);
  } catch {
    // storage blocked: header just loads it again
  }
  window.dispatchEvent(new CustomEvent(EVENT, { detail: p }));
}

export function logoutCustomer(): void {
  setCustomerToken(null);
  publishProfile(null);
  clearLocalShopping();           // bag and wishlist stay on the account, not in this browser
}

/** Profile of the signed-in customer (cached so the header avatar shows at once). */
export function useCustomerProfile() {
  const token = getCustomerToken();
  const [profile, setProfile] = useState<CustomerProfile | null>(() => (token ? readCache() : null));

  useEffect(() => {
    const on = (e: Event) => setProfile((e as CustomEvent<CustomerProfile | null>).detail);
    window.addEventListener(EVENT, on);
    if (token) {
      // First page of a signed-in visit: bring the account's bag and wishlist into this browser.
      if (!syncedThisVisit()) void mergeOnSignIn();
      customerApi<CustomerProfile>("/store/me")
        .then(publishProfile)
        .catch((err: { status?: number }) => {
          // Expired or invalid login: sign out quietly.
          if (err?.status === 401) logoutCustomer();
        });
    }
    return () => window.removeEventListener(EVENT, on);
  }, [token]);

  return { profile, signedIn: Boolean(token) };
}

export const INDIAN_STATES = [
  "Andaman and Nicobar Islands", "Andhra Pradesh", "Arunachal Pradesh", "Assam", "Bihar", "Chandigarh", "Chhattisgarh",
  "Dadra and Nagar Haveli and Daman and Diu", "Delhi", "Goa", "Gujarat", "Haryana", "Himachal Pradesh",
  "Jammu and Kashmir", "Jharkhand", "Karnataka", "Kerala", "Ladakh", "Lakshadweep", "Madhya Pradesh", "Maharashtra",
  "Manipur", "Meghalaya", "Mizoram", "Nagaland", "Odisha", "Puducherry", "Punjab", "Rajasthan", "Sikkim",
  "Tamil Nadu", "Telangana", "Tripura", "Uttar Pradesh", "Uttarakhand", "West Bengal",
];

export function addressLines(a: Pick<Address, "line1" | "line2" | "landmark" | "city" | "state" | "pincode">): string {
  return [a.line1, a.line2, a.landmark ? `Near ${a.landmark}` : null, `${a.city}, ${a.state} ${a.pincode}`]
    .filter(Boolean).join(", ");
}
