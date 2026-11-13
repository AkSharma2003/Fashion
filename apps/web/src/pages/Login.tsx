import { STORE_NAME } from "../lib/brand";
import { FormEvent, useEffect, useRef, useState } from "react";
import { Link, useLocation, useSearchParams } from "react-router-dom";
import { Eye, EyeOff } from "lucide-react";
import Header from "../components/Header";
import Footer from "../components/Footer";
import { apiData, ApiError, errorMessage, post } from "../lib/api/client";
import { clearSession, getCustomerToken, saveSession, setCustomerToken, staffHome } from "../lib/auth/session";
import { clearLocalShopping, mergeOnSignIn } from "../lib/shoppingSync";
import { logoutCustomer, publishProfile } from "../lib/customer";

/** One sign-in for everybody. The server says whether the account is shop staff or a website customer;
 *  staff go to the screen for their role, customers to their account. */

type StaffResult = { kind: "staff"; access_token: string; refresh_token: string; token_type: string;
  is_active: boolean; role: string | null; full_name: string };
type CustomerResult = { kind: "customer"; access_token: string };
type NeedsPhone = { kind: "needs_phone"; email: string; full_name: string };


type GoogleId = {
  accounts: { id: {
    initialize: (o: { client_id: string; callback: (r: { credential: string }) => void }) => void;
    renderButton: (el: HTMLElement, o: Record<string, unknown>) => void;
  } };
};
declare global { interface Window { google?: GoogleId } }

function loadGoogleScript(): Promise<void> {
  if (window.google?.accounts?.id) return Promise.resolve();
  return new Promise((resolve, reject) => {
    const existing = document.getElementById("google-gsi") as HTMLScriptElement | null;
    const script = existing ?? Object.assign(document.createElement("script"), {
      id: "google-gsi", src: "https://accounts.google.com/gsi/client", async: true, defer: true });
    script.addEventListener("load", () => resolve());
    script.addEventListener("error", () => reject(new Error("Could not load Google sign-in.")));
    if (!existing) document.head.appendChild(script);
  });
}

const inputClass = "min-h-12 w-full rounded-lg border border-gray-300 px-4 py-3 text-base text-gray-900 outline-none transition placeholder:text-gray-400 focus:border-primary focus:ring-2 focus:ring-primary/20";

export default function Login() {
  const location = useLocation();
  const [params] = useSearchParams();

  const [login, setLogin] = useState("");
  const [password, setPassword] = useState("");
  const [remember, setRemember] = useState(false);
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const googleBox = useRef<HTMLDivElement>(null);
  const [googleReady, setGoogleReady] = useState<"loading" | "on" | "off">("loading");
  const [googleCredential, setGoogleCredential] = useState<string | null>(null);
  const [needsPhone, setNeedsPhone] = useState<NeedsPhone | null>(null);
  const [phone, setPhone] = useState("");

  const next = params.get("next") || (location.state as { from?: { pathname?: string } } | null)?.from?.pathname || "";

  function finishStaff(r: StaffResult) {
    if (!r.is_active) throw new Error("This account is inactive. Contact the shop owner.");
    const home = staffHome(r.role);
    // Only roles with back office may be sent back to a back-office page they came from.
    const destination = (next.startsWith("/backoffice") || next === "/pos") && home !== "/me" ? next : home;
    logoutCustomer();
    // The POS keeps its login across restarts so the counter can bill offline.
    saveSession(r, remember || destination === "/pos");
    window.location.replace(destination);      // fresh page: nothing from the previous user stays in memory
  }

  async function finishCustomer(r: CustomerResult) {
    // Someone else was signed in on this browser: their bag must not join this account. A guest's picks do join.
    if (getCustomerToken()) clearLocalShopping();
    clearSession();
    publishProfile(null);           // forget any earlier customer's cached name/photo
    setCustomerToken(r.access_token);
    await mergeOnSignIn();          // guest bag + wishlist join the account's saved ones
    // Customers land on the home page (or the page they were on, e.g. checkout).
    const destination = next && !next.startsWith("/backoffice") && next !== "/pos" ? next : "/";
    window.location.replace(destination);
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError("");
    setLoading(true);
    try {
      const r = await post<StaffResult | CustomerResult>("/auth/sign-in", { login: login.trim(), password });
      if (r.kind === "staff") finishStaff(r);
      else await finishCustomer(r);
    } catch (caught) {
      setError(caught instanceof ApiError && caught.status === 401
        ? "Phone/e-mail or password is incorrect."
        : errorMessage(caught, "Unable to sign in. Please try again."));
    } finally {
      setLoading(false);
    }
  }

  async function sendGoogle(credential: string, phoneNumber?: string) {
    setError("");
    setLoading(true);
    try {
      const r = await post<CustomerResult | NeedsPhone>("/auth/google", { credential, phone_number: phoneNumber });
      if (r.kind === "needs_phone") {
        setGoogleCredential(credential);
        setNeedsPhone(r);
      } else {
        await finishCustomer(r);
      }
    } catch (caught) {
      setError(errorMessage(caught, "Google sign-in failed. Please try again."));
    } finally {
      setLoading(false);
    }
  }

  // Google's own button (Google Identity Services) when the shop has set GOOGLE_CLIENT_ID on the API.
  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const cfg = await apiData<{ enabled: boolean; client_id: string | null }>("/auth/google/config");
        if (!cfg.enabled || !cfg.client_id) { if (!cancelled) setGoogleReady("off"); return; }
        await loadGoogleScript();
        if (cancelled || !googleBox.current || !window.google) return;
        window.google.accounts.id.initialize({ client_id: cfg.client_id, callback: (resp) => void sendGoogle(resp.credential) });
        window.google.accounts.id.renderButton(googleBox.current, {
          theme: "outline", size: "large", text: "continue_with", shape: "rectangular",
          width: Math.min(googleBox.current.offsetWidth || 360, 400) });
        setGoogleReady("on");
      } catch {
        if (!cancelled) setGoogleReady("off");
      }
    })();
    return () => { cancelled = true; };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return (
    <>
      <Header />

      <main className="flex min-h-[calc(100svh-5rem)] items-start justify-center bg-linear-to-br from-background to-Alt_background px-3 py-6 sm:items-center sm:px-4 sm:py-12">
        <section className="w-full max-w-md rounded-xl border border-gray-100 bg-white p-5 shadow-xl sm:rounded-2xl sm:p-9">
          <div className="mb-6 text-center sm:mb-8">
            <p className="mb-2 text-sm font-semibold uppercase tracking-[0.2em] text-primary">Welcome back</p>
            <h1 className="text-2xl font-bold text-gray-900 sm:text-3xl">Sign in to {STORE_NAME}</h1>
            <p className="mt-2 text-sm text-gray-600">Enter your details to access your account.</p>
          </div>

          {needsPhone ? (
            <form className="space-y-5" onSubmit={(e) => { e.preventDefault(); if (googleCredential) void sendGoogle(googleCredential, phone); }}>
              <p className="rounded-lg bg-gray-50 px-3 py-2 text-sm text-gray-700">
                Signed in with Google as <b>{needsPhone.email}</b>. Add your mobile number once so we can send order
                updates.
              </p>
              <div>
                <label htmlFor="google-phone" className="mb-2 block text-sm font-medium text-gray-700">Mobile number</label>
                <input id="google-phone" type="tel" inputMode="numeric" pattern="\d{10}" maxLength={10} required
                  value={phone} onChange={(e) => setPhone(e.target.value.replace(/\D/g, ""))}
                  placeholder="10-digit mobile number" className={inputClass} />
              </div>
              {error && <p role="alert" className="rounded-lg bg-red-50 px-3 py-2 text-sm text-red-700">{error}</p>}
              <button type="submit" disabled={loading || phone.length !== 10}
                className="min-h-12 w-full rounded-lg bg-primary px-4 py-3 font-semibold text-white transition hover:bg-primary-dark disabled:cursor-not-allowed disabled:opacity-60">
                {loading ? "Saving…" : "Continue"}
              </button>
              <button type="button" onClick={() => { setNeedsPhone(null); setGoogleCredential(null); setError(""); }}
                className="w-full text-sm font-medium text-gray-600 hover:underline">Back</button>
            </form>
          ) : (
            <>
              <form onSubmit={handleSubmit} className="space-y-5">
                <div>
                  <label htmlFor="login" className="mb-2 block text-sm font-medium text-gray-700">Phone number or e-mail</label>
                  <input id="login" name="login" type="text" autoComplete="username" minLength={3} maxLength={255} required
                    value={login} onChange={(e) => setLogin(e.target.value)}
                    placeholder="Enter your phone number or e-mail" className={inputClass} />
                </div>

                <div>
                  <div className="mb-2 flex items-center justify-between">
                    <label htmlFor="password" className="text-sm font-medium text-gray-700">Password</label>
                    <button type="button" onClick={() => setShowPassword((v) => !v)} aria-controls="password" aria-pressed={showPassword}
                      className="inline-flex items-center gap-1.5 text-sm font-medium text-primary hover:underline">
                      {showPassword ? <EyeOff size={16} aria-hidden="true" /> : <Eye size={16} aria-hidden="true" />}
                      {showPassword ? "Hide" : "Show"}
                    </button>
                  </div>
                  <input id="password" name="password" type={showPassword ? "text" : "password"} autoComplete="current-password" required
                    value={password} onChange={(e) => setPassword(e.target.value)}
                    placeholder="Enter your password" className={inputClass} />
                </div>

                <label className="flex items-center text-sm text-gray-600">
                  <input type="checkbox" checked={remember} onChange={(e) => setRemember(e.target.checked)}
                    className="h-4 w-4 rounded border-gray-300 accent-primary focus:ring-primary" />
                  <span className="ml-2">Remember me</span>
                </label>

                {error && <p role="alert" className="rounded-lg bg-red-50 px-3 py-2 text-sm text-red-700">{error}</p>}

                <button type="submit" disabled={loading}
                  className="min-h-12 w-full rounded-lg bg-primary px-4 py-3 font-semibold text-white transition hover:bg-primary-dark focus:outline-none focus:ring-2 focus:ring-primary focus:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-60">
                  {loading ? "Signing in…" : "Sign in"}
                </button>
              </form>

              <div className="my-6 flex items-center gap-4">
                <div className="h-px flex-1 bg-gray-200" />
                <span className="text-xs font-medium uppercase tracking-wider text-gray-400">or</span>
                <div className="h-px flex-1 bg-gray-200" />
              </div>

              {/* Google renders its button here when sign-in with Google is set up. */}
              <div ref={googleBox} className={`flex min-h-12 justify-center ${googleReady === "on" ? "" : "hidden"}`} />
              {googleReady !== "on" && (
                <button type="button" disabled={googleReady === "loading"}
                  onClick={() => setError("Sign in with Google is not set up for this shop yet. Please use your phone number or e-mail.")}
                  className="flex min-h-12 w-full items-center justify-center gap-3 rounded-lg border border-gray-300 px-4 py-3 font-semibold text-gray-700 transition hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-primary focus:ring-offset-2 disabled:opacity-60">
                  <svg aria-hidden="true" viewBox="0 0 48 48" className="h-5 w-5">
                    <path fill="#FFC107" d="M43.6 24.5c0-1.4-.1-2.8-.4-4.1H24v7.8h11a9.4 9.4 0 0 1-4.1 6.2v5.1h6.6c3.9-3.6 6.1-8.8 6.1-15Z" />
                    <path fill="#4CAF50" d="M24 44c5.5 0 10.1-1.8 13.5-4.8l-6.6-5.1c-1.8 1.2-4.1 2-6.9 2-5.3 0-9.8-3.6-11.4-8.4H5.8v5.3A20 20 0 0 0 24 44Z" />
                    <path fill="#1976D2" d="M12.6 27.7a12 12 0 0 1 0-7.4V15H5.8a20 20 0 0 0 0 17.9l6.8-5.2Z" />
                    <path fill="#EA4335" d="M24 11.9c3 0 5.7 1 7.8 3.1l5.9-5.9C34.1 5.8 29.5 4 24 4A20 20 0 0 0 5.8 15l6.8 5.3c1.6-4.8 6.1-8.4 11.4-8.4Z" />
                  </svg>
                  Continue with Google
                </button>
              )}

              <p className="mt-6 text-center text-sm text-gray-600">
                New to {STORE_NAME}?{" "}
                <Link to="/signin" className="font-semibold text-primary hover:underline">Create an account</Link>
              </p>
            </>
          )}
        </section>
      </main>

      <Footer />
    </>
  );
}
