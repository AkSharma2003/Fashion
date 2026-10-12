import Header from "../components/Header";
import Footer from "../components/Footer";
import { Link, useNavigate } from "react-router-dom";
import { useState, type FormEvent } from "react";
import { Eye, EyeOff } from "lucide-react";
import { registerCustomer, saveCustomerSession } from "../lib/api/customerAuth";

export default function Signin() {
  const [showPassword, setShowPassword] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState("");
  const navigate = useNavigate();

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError("");
    setIsSubmitting(true);

    const formData = new FormData(event.currentTarget);
    try {
      const auth = await registerCustomer({
        full_name: String(formData.get("name") ?? ""),
        email: String(formData.get("email") ?? ""),
        phone_number: String(formData.get("phone") ?? ""),
        password: String(formData.get("password") ?? ""),
      });
      saveCustomerSession(auth);
      navigate("/", { replace: true });
    } catch (submitError) {
      setError(submitError instanceof Error ? submitError.message : "Unable to create your account. Please try again.");
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <>
      <Header />
      <main className="flex min-h-[calc(100svh-5rem)] items-start justify-center bg-linear-to-br from-background to-Alt_background px-3 py-6 sm:items-center sm:px-4 sm:py-12">
        <section className="w-full max-w-md rounded-xl border border-gray-100 bg-white p-5 shadow-xl sm:rounded-2xl sm:p-9">
          <div className="mb-6 text-center sm:mb-8">
            <p className="mb-2 text-sm font-semibold uppercase tracking-[0.2em] text-primary">
              {"Join WearVerse"}
            </p>
            <h1 className="text-2xl font-bold text-gray-900 sm:text-3xl">{"Create your account"}</h1>
            <p className="mt-2 text-sm text-gray-600">
              {"Create an account to save your favorites and orders."}
            </p>
          </div>

          <form className="space-y-5" onSubmit={handleSubmit}>
            <div>
              <label htmlFor="name" className="mb-2 block text-sm font-medium text-gray-700">
                {"Full name"}
              </label>
              <input
                id="name"
                name="name"
                type="text"
                autoComplete="name"
                required
                placeholder={"Your name"}
                className="min-h-12 w-full rounded-lg border border-gray-300 px-4 py-3 text-base text-gray-900 outline-none transition placeholder:text-gray-400 focus:border-primary focus:ring-2 focus:ring-primary/20"
              />
            </div>

            <div>
              <label htmlFor="signup-email" className="mb-2 block text-sm font-medium text-gray-700">
                {"Email address"}
              </label>
              <input
                id="signup-email"
                name="email"
                type="email"
                autoComplete="email"
                required
                placeholder="you@example.com"
                className="min-h-12 w-full rounded-lg border border-gray-300 px-4 py-3 text-base text-gray-900 outline-none transition placeholder:text-gray-400 focus:border-primary focus:ring-2 focus:ring-primary/20"
              />
            </div>

            <div>
              <label htmlFor="signup-phone" className="mb-2 block text-sm font-medium text-gray-700">
                {"Mobile number"}
              </label>
              <input
                id="signup-phone"
                name="phone"
                type="tel"
                autoComplete="tel"
                inputMode="tel"
                required
                placeholder={"Enter your mobile number"}
                className="min-h-12 w-full rounded-lg border border-gray-300 px-4 py-3 text-base text-gray-900 outline-none transition placeholder:text-gray-400 focus:border-primary focus:ring-2 focus:ring-primary/20"
              />
            </div>

            <div>
              <div className="mb-2 flex items-center justify-between">
                <label htmlFor="signup-password" className="text-sm font-medium text-gray-700">
                  {"Password"}
                </label>
                <button
                  type="button"
                  onClick={() => setShowPassword((visible) => !visible)}
                  aria-controls="signup-password"
                  aria-pressed={showPassword}
                  className="inline-flex items-center gap-1.5 text-sm font-medium text-primary hover:underline"
                >
                  {showPassword ? <EyeOff size={16} aria-hidden="true" /> : <Eye size={16} aria-hidden="true" />}
                  {showPassword ? "Hide" : "Show"}
                </button>
              </div>
              <input
                id="signup-password"
                name="password"
                type={showPassword ? "text" : "password"}
                autoComplete="new-password"
                minLength={8}
                required
                placeholder={"At least 8 characters"}
                className="min-h-12 w-full rounded-lg border border-gray-300 px-4 py-3 text-base text-gray-900 outline-none transition placeholder:text-gray-400 focus:border-primary focus:ring-2 focus:ring-primary/20"
              />
            </div>

            <button
              type="submit"
              disabled={isSubmitting}
              className="min-h-12 w-full rounded-lg bg-primary px-4 py-3 font-semibold text-white transition hover:bg-primary-dark focus:outline-none focus:ring-2 focus:ring-primary focus:ring-offset-2"
            >
              {isSubmitting ? "Creating account..." : "Create account"}
            </button>
            {error && <p className="text-sm text-sale" role="alert">{error}</p>}
          </form>

          <p className="mt-6 text-center text-sm text-gray-600">
            {"Already have an account?"}{" "}
            <Link to="/login" className="font-semibold text-primary hover:underline">
              {"Sign in"}
            </Link>
          </p>
        </section>
      </main>
      <Footer />
    </>
  );
}
