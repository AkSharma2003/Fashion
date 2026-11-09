import { FormEvent, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { Eye, EyeOff } from "lucide-react";
import Header from "../components/Header";
import Footer from "../components/Footer";
import { api, errorMessage, post } from "../lib/api/client";
import { clearSession, setCustomerToken } from "../lib/auth/session";

/** Website registration: details → 6-digit code sent to the e-mail (and SMS) → account created → signed in. */

const inputClass = "min-h-12 w-full rounded-lg border border-gray-300 px-4 py-3 text-base text-gray-900 outline-none transition placeholder:text-gray-400 focus:border-primary focus:ring-2 focus:ring-primary/20";
const REGISTER = "/customers/customers/website/register";
const VERIFY = "/customers/customers/website/verify-otp";

export default function Signin() {
  const navigate = useNavigate();
  const [form, setForm] = useState({ full_name: "", email: "", phone_number: "", password: "" });
  const [showPassword, setShowPassword] = useState(false);
  const [step, setStep] = useState<"details" | "otp">("details");
  const [otp, setOtp] = useState("");
  const [error, setError] = useState("");
  const [info, setInfo] = useState("");
  const [loading, setLoading] = useState(false);

  const set = (k: keyof typeof form, v: string) => setForm({ ...form, [k]: v });

  async function sendCode(event?: FormEvent<HTMLFormElement>) {
    event?.preventDefault();
    setError("");
    setInfo("");
    if (!/^\d{10}$/.test(form.phone_number)) { setError("Enter a 10-digit mobile number."); return; }
    setLoading(true);
    try {
      await api(REGISTER, { method: "POST", body: JSON.stringify({
        full_name: form.full_name.trim(), email: form.email.trim(), phone_number: form.phone_number, password: form.password }) });
      setStep("otp");
      setOtp("");
      setInfo(`We sent a 6-digit code to ${form.email.trim()}. It expires in 5 minutes.`);
    } catch (caught) {
      setError(errorMessage(caught, "Could not send the code. Please try again."));
    } finally {
      setLoading(false);
    }
  }

  async function verify(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError("");
    setLoading(true);
    try {
      await api(VERIFY, { method: "POST", body: JSON.stringify({ email: form.email.trim(), otp }) });
      // Account is ready: sign in straight away.
      const r = await post<{ kind: string; access_token: string }>("/auth/sign-in", { login: form.email.trim(), password: form.password });
      clearSession();
      setCustomerToken(r.access_token);
      navigate("/account", { replace: true });
    } catch (caught) {
      setError(errorMessage(caught, "Could not verify the code. Please try again."));
    } finally {
      setLoading(false);
    }
  }

  return (
    <>
      <Header />
      <main className="flex min-h-[calc(100svh-5rem)] items-start justify-center bg-linear-to-br from-background to-Alt_background px-3 py-6 sm:items-center sm:px-4 sm:py-12">
        <section className="w-full max-w-md rounded-xl border border-gray-100 bg-white p-5 shadow-xl sm:rounded-2xl sm:p-9">
          <div className="mb-6 text-center sm:mb-8">
            <p className="mb-2 text-sm font-semibold uppercase tracking-[0.2em] text-primary">Join WearVerse</p>
            <h1 className="text-2xl font-bold text-gray-900 sm:text-3xl">
              {step === "details" ? "Create your account" : "Enter the code"}
            </h1>
            <p className="mt-2 text-sm text-gray-600">
              {step === "details" ? "Create an account to save your favorites and orders." : info}
            </p>
          </div>

          {step === "details" ? (
            <form className="space-y-5" onSubmit={sendCode}>
              <div>
                <label htmlFor="name" className="mb-2 block text-sm font-medium text-gray-700">Full name</label>
                <input id="name" type="text" autoComplete="name" required minLength={2} maxLength={100}
                  value={form.full_name} onChange={(e) => set("full_name", e.target.value)} placeholder="Your name" className={inputClass} />
              </div>
              <div>
                <label htmlFor="signup-email" className="mb-2 block text-sm font-medium text-gray-700">Email address</label>
                <input id="signup-email" type="email" autoComplete="email" required
                  value={form.email} onChange={(e) => set("email", e.target.value)} placeholder="you@example.com" className={inputClass} />
              </div>
              <div>
                <label htmlFor="signup-phone" className="mb-2 block text-sm font-medium text-gray-700">Mobile number</label>
                <input id="signup-phone" type="tel" autoComplete="tel" inputMode="numeric" required maxLength={10}
                  value={form.phone_number} onChange={(e) => set("phone_number", e.target.value.replace(/\D/g, ""))}
                  placeholder="10-digit mobile number" className={inputClass} />
              </div>
              <div>
                <div className="mb-2 flex items-center justify-between">
                  <label htmlFor="signup-password" className="text-sm font-medium text-gray-700">Password</label>
                  <button type="button" onClick={() => setShowPassword((v) => !v)} aria-controls="signup-password" aria-pressed={showPassword}
                    className="inline-flex items-center gap-1.5 text-sm font-medium text-primary hover:underline">
                    {showPassword ? <EyeOff size={16} aria-hidden="true" /> : <Eye size={16} aria-hidden="true" />}
                    {showPassword ? "Hide" : "Show"}
                  </button>
                </div>
                <input id="signup-password" type={showPassword ? "text" : "password"} autoComplete="new-password" minLength={8} maxLength={128} required
                  value={form.password} onChange={(e) => set("password", e.target.value)} placeholder="At least 8 characters" className={inputClass} />
              </div>

              {error && <p role="alert" className="rounded-lg bg-red-50 px-3 py-2 text-sm text-red-700">{error}</p>}

              <button type="submit" disabled={loading}
                className="min-h-12 w-full rounded-lg bg-primary px-4 py-3 font-semibold text-white transition hover:bg-primary-dark focus:outline-none focus:ring-2 focus:ring-primary focus:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-60">
                {loading ? "Sending code…" : "Create account"}
              </button>
            </form>
          ) : (
            <form className="space-y-5" onSubmit={verify}>
              <div>
                <label htmlFor="otp" className="mb-2 block text-sm font-medium text-gray-700">6-digit code</label>
                <input id="otp" type="text" inputMode="numeric" autoComplete="one-time-code" required pattern="\d{6}" maxLength={6}
                  value={otp} onChange={(e) => setOtp(e.target.value.replace(/\D/g, ""))} placeholder="123456"
                  className={`${inputClass} text-center text-xl tracking-[0.4em]`} />
              </div>

              {error && <p role="alert" className="rounded-lg bg-red-50 px-3 py-2 text-sm text-red-700">{error}</p>}

              <button type="submit" disabled={loading || otp.length !== 6}
                className="min-h-12 w-full rounded-lg bg-primary px-4 py-3 font-semibold text-white transition hover:bg-primary-dark disabled:cursor-not-allowed disabled:opacity-60">
                {loading ? "Checking…" : "Verify and continue"}
              </button>
              <div className="flex justify-between text-sm">
                <button type="button" onClick={() => { setStep("details"); setError(""); }} className="font-medium text-gray-600 hover:underline">
                  Change details
                </button>
                <button type="button" disabled={loading} onClick={() => void sendCode()} className="font-medium text-primary hover:underline disabled:opacity-60">
                  Send a new code
                </button>
              </div>
            </form>
          )}

          <p className="mt-6 text-center text-sm text-gray-600">
            Already have an account?{" "}
            <Link to="/login" className="font-semibold text-primary hover:underline">Sign in</Link>
          </p>
        </section>
      </main>
      <Footer />
    </>
  );
}
