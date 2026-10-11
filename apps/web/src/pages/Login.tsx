import { FormEvent, useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import Header from "../components/Header";
import Footer from "../components/Footer";
import { api, ApiError } from "../lib/api/client";
import { LoginResponse, saveSession } from "../lib/auth/session";

export default function Login() {
  const navigate = useNavigate();
  const location = useLocation();
  const [phoneNumber, setPhoneNumber] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError("");
    setLoading(true);

    try {
      const result = await api<LoginResponse>("/auth/login", {
        method: "POST",
        body: JSON.stringify({
          phone_number: phoneNumber.trim(),
          password,
        }),
      });

      if (!result.access_token || !result.refresh_token) {
        throw new Error("Login response did not include the required tokens.");
      }
      if (!result.is_active) {
        throw new Error("This account is inactive. Contact the shop owner.");
      }

      saveSession(result);
      const destination = (location.state as { from?: { pathname?: string } } | null)?.from?.pathname;
      navigate(destination || "/backoffice", { replace: true });
    } catch (caught) {
      if (caught instanceof ApiError && caught.status === 401) {
        setError("Phone number or password is incorrect.");
      } else {
        setError(caught instanceof Error ? caught.message : "Unable to sign in. Please try again.");
      }
    } finally {
      setLoading(false);
    }
  }

  return (
    <>
      <Header />
      <main className="min-h-[70vh] bg-linear-to-br from-background to-Alt_background px-4 py-12">
        <section className="mx-auto w-full max-w-md rounded-xl border border-gray-200 bg-white p-6 shadow-sm sm:p-8">
          <h1 className="text-2xl font-semibold text-[#111111]">Sign in to FashionOS</h1>
          <p className="mt-2 text-sm text-gray-600">Use your registered staff phone number and password.</p>

          <form onSubmit={handleSubmit} className="mt-6 space-y-5">
            <div>
              <label htmlFor="phone-number" className="mb-2 block text-sm font-medium text-gray-700">
                Phone number
              </label>
              <input
                id="phone-number"
                name="phone_number"
                type="tel"
                autoComplete="username"
                inputMode="tel"
                minLength={10}
                maxLength={15}
                required
                value={phoneNumber}
                onChange={(event) => setPhoneNumber(event.target.value)}
                className="w-full rounded-lg border border-gray-300 px-4 py-3 outline-none transition focus:border-[#111111] focus:ring-1 focus:ring-[#111111]"
                placeholder="Enter phone number"
              />
            </div>

            <div>
              <label htmlFor="password" className="mb-2 block text-sm font-medium text-gray-700">
                Password
              </label>
              <input
                id="password"
                name="password"
                type="password"
                autoComplete="current-password"
                minLength={4}
                maxLength={20}
                required
                value={password}
                onChange={(event) => setPassword(event.target.value)}
                className="w-full rounded-lg border border-gray-300 px-4 py-3 outline-none transition focus:border-[#111111] focus:ring-1 focus:ring-[#111111]"
                placeholder="Enter password"
              />
            </div>

            {error && (
              <p role="alert" className="rounded-lg bg-red-50 px-3 py-2 text-sm text-red-700">
                {error}
              </p>
            )}

            <button
              type="submit"
              disabled={loading}
              className="min-h-11 w-full rounded-lg bg-[#111111] px-4 py-3 font-medium text-white transition hover:bg-black disabled:cursor-not-allowed disabled:opacity-60"
            >
              {loading ? "Signing in…" : "Sign in"}
            </button>
          </form>
        </section>
      </main>
      <Footer />
    </>
  );
}
