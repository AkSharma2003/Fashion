import { useState, type FormEvent } from "react";
import Header from "../components/Header";
import Footer from "../components/Footer";
import { errorMessage, post } from "../lib/api/client";

export default function Contact() {
  const [notice, setNotice] = useState("");
  const [error, setError] = useState("");
  const [sending, setSending] = useState(false);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = event.currentTarget;
    const data = new FormData(form);
    setNotice("");
    setError("");
    setSending(true);
    try {
      const phone = String(data.get("phone") ?? "").replace(/\D/g, "");
      await post("/store/contact", { name: String(data.get("name") ?? "").trim(), email: String(data.get("email") ?? "").trim(),
        phone: phone || undefined, message: String(data.get("message") ?? "").trim() });
      form.reset();
      setNotice("Thank you! Your message has reached the shop. We usually reply within one working day.");
    } catch (caught) {
      setError(errorMessage(caught, "Could not send your message. Please try again."));
    } finally {
      setSending(false);
    }
  }

  return (
    <>
      <Header />
      <main className="min-h-[calc(100svh-5rem)] bg-linear-to-br from-background to-Alt_background px-4 py-10 sm:px-6 sm:py-14">
        <div className="mx-auto grid w-full max-w-5xl gap-8 md:grid-cols-[0.85fr_1.15fr] md:gap-12">
          <section className="pt-2">
            <p className="text-sm font-semibold uppercase tracking-[0.2em] text-primary">We’re here to help</p>
            <h1 className="sr-only">Contact us</h1>
            <p className="mt-4 max-w-md leading-7 text-text">
              Have a question about an order, a product, or sizing? Send us a message and our team will get back to you.
            </p>
          </section>

          <section className="rounded-2xl border border-divider bg-white p-5 shadow-lg sm:p-8">
            <h2 className="font-primaryFont text-2xl font-semibold text-main_text">Send a message</h2>
            <form className="mt-6 space-y-5" onSubmit={handleSubmit}>
              <div>
                <label htmlFor="contact-name" className="mb-2 block text-sm font-medium text-main_text">Your name</label>
                <input id="contact-name" name="name" type="text" autoComplete="name" required className="min-h-12 w-full rounded-lg border border-divider px-4 py-3 text-base text-main_text outline-none focus:border-primary focus:ring-2 focus:ring-primary/20" />
              </div>
              <div>
                <label htmlFor="contact-email" className="mb-2 block text-sm font-medium text-main_text">Email address</label>
                <input id="contact-email" name="email" type="email" autoComplete="email" required className="min-h-12 w-full rounded-lg border border-divider px-4 py-3 text-base text-main_text outline-none focus:border-primary focus:ring-2 focus:ring-primary/20" />
              </div>
              <div>
                <label htmlFor="contact-phone" className="mb-2 block text-sm font-medium text-main_text">Mobile number (optional)</label>
                <input id="contact-phone" name="phone" type="tel" inputMode="numeric" pattern="\d{10}" maxLength={10} autoComplete="tel" className="min-h-12 w-full rounded-lg border border-divider px-4 py-3 text-base text-main_text outline-none focus:border-primary focus:ring-2 focus:ring-primary/20" />
              </div>
              <div>
                <label htmlFor="contact-message" className="mb-2 block text-sm font-medium text-main_text">How can we help?</label>
                <textarea id="contact-message" name="message" rows={5} required minLength={5} maxLength={2000} className="w-full resize-y rounded-lg border border-divider px-4 py-3 text-base text-main_text outline-none focus:border-primary focus:ring-2 focus:ring-primary/20" />
              </div>
              <button type="submit" disabled={sending} className="disabled:opacity-60 min-h-12 w-full rounded-lg bg-primary px-4 py-3 font-semibold text-white transition hover:bg-primary-dark focus:outline-none focus:ring-2 focus:ring-primary focus:ring-offset-2">
                {sending ? "Sending…" : "Send message"}
              </button>
              {notice && <p role="status" className="rounded-lg bg-green-50 px-3 py-2 text-sm text-green-800">{notice}</p>}
              {error && <p role="alert" className="rounded-lg bg-red-50 px-3 py-2 text-sm text-red-700">{error}</p>}
            </form>
          </section>
        </div>
      </main>
      <Footer />
    </>
  );
}
