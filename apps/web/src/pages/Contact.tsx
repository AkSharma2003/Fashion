import { useState, type FormEvent } from "react";
import Header from "../components/Header";
import Footer from "../components/Footer";

export default function Contact() {
  const [notice, setNotice] = useState("");

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setNotice("The contact form is not connected yet, so your message was not sent.");
  }

  return (
    <>
      <Header />
      <main className="min-h-[calc(100svh-5rem)] bg-linear-to-br from-background to-Alt_background px-4 py-10 sm:px-6 sm:py-14">
        <div className="mx-auto grid w-full max-w-5xl gap-8 md:grid-cols-[0.85fr_1.15fr] md:gap-12">
          <section className="pt-2">
            <p className="text-sm font-semibold uppercase tracking-[0.2em] text-primary">We’re here to help</p>
            <h1 className="mt-3 font-primaryFont text-3xl font-semibold text-main_text sm:text-4xl">
              Contact Us
            </h1>
            <p className="mt-4 max-w-md leading-7 text-text">
              Have a question about an order, a product, or sizing? Send us a message and our team will be ready to help once support messages are connected.
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
                <label htmlFor="contact-message" className="mb-2 block text-sm font-medium text-main_text">How can we help?</label>
                <textarea id="contact-message" name="message" rows={5} required className="w-full resize-y rounded-lg border border-divider px-4 py-3 text-base text-main_text outline-none focus:border-primary focus:ring-2 focus:ring-primary/20" />
              </div>
              <button type="submit" className="min-h-12 w-full rounded-lg bg-primary px-4 py-3 font-semibold text-white transition hover:bg-primary-dark focus:outline-none focus:ring-2 focus:ring-primary focus:ring-offset-2">
                Send message
              </button>
              {notice && <p role="status" className="text-sm text-sale">{notice}</p>}
            </form>
          </section>
        </div>
      </main>
      <Footer />
    </>
  );
}
