import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { Minus, Plus, Trash2 } from "lucide-react";
import clothingFallback from "../assets/images/clothing-fallback.svg";
import Header from "../components/Header";
import Footer from "../components/Footer";
import {
  cartUpdatedEventName,
  getCart,
  removeFromCart,
  updateCartQuantity,
  type CartItem,
} from "../lib/cart";

export default function Cart() {
  const [items, setItems] = useState<CartItem[]>(getCart);

  useEffect(() => {
    const refreshCart = () => setItems(getCart());
    window.addEventListener(cartUpdatedEventName(), refreshCart);
    window.addEventListener("storage", refreshCart);

    return () => {
      window.removeEventListener(cartUpdatedEventName(), refreshCart);
      window.removeEventListener("storage", refreshCart);
    };
  }, []);

  const total = items.reduce((sum, item) => sum + item.product.price * item.quantity, 0);

  return (
    <>
      <Header />
      <main className="min-h-screen bg-linear-to-br from-background to-Alt_background px-4 py-10 sm:px-6 sm:py-14 lg:px-8">
        <section className="mx-auto max-w-5xl">
          <div className="mb-8">
            <p className="text-sm font-semibold uppercase tracking-[0.2em] text-primary">{"Your selection"}</p>
            <h1 className="mt-2 font-primaryFont text-3xl font-semibold text-main_text sm:text-4xl">{"Shopping cart"}</h1>
          </div>

          {items.length === 0 ? (
            <div className="rounded-2xl border border-divider bg-white px-6 py-12 text-center shadow-sm">
              <p className="font-primaryFont text-xl font-semibold text-main_text">{"Your cart is empty"}</p>
              <p className="mt-2 text-sm text-text">{"Explore the collection and add a style you love."}</p>
              <Link to="/" className="mt-6 inline-flex min-h-11 items-center justify-center rounded-lg bg-primary px-5 py-2.5 font-semibold text-white transition hover:bg-primary-dark">
                Explore designs
              </Link>
            </div>
          ) : (
            <div className="grid gap-6 md:grid-cols-[1fr_18rem] md:items-start">
              <div className="space-y-4">
                {items.map(({ product, quantity }) => (
                  <article key={product.name} className="flex gap-4 rounded-xl border border-divider bg-white p-3 shadow-sm sm:gap-5 sm:p-4">
                    <img
                      src={product.image}
                      alt={product.imageAlt}
                      referrerPolicy="no-referrer"
                      onError={(event) => {
                        event.currentTarget.onerror = null;
                        event.currentTarget.src = clothingFallback;
                      }}
                      className="h-28 w-24 shrink-0 rounded-lg bg-Alt_background object-cover sm:h-36 sm:w-28"
                    />
                    <div className="flex min-w-0 flex-1 flex-col">
                      <div className="flex items-start justify-between gap-2">
                        <div className="min-w-0">
                          <h2 className="font-primaryFont text-base font-semibold text-main_text sm:text-lg">{product.name}</h2>
                          <p className="mt-1 line-clamp-2 text-xs leading-5 text-text sm:text-sm">{product.description}</p>
                        </div>
                        <button
                          type="button"
                          onClick={() => removeFromCarproduct.name}
                          aria-label={`Remove ${product.name} from cart`}
                          className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full text-muted transition hover:bg-red-50 hover:text-sale"
                        >
                          <Trash2 size={18} aria-hidden="true" />
                        </button>
                      </div>
                      <div className="mt-auto flex flex-wrap items-end justify-between gap-3 pt-3">
                        <div className="inline-flex items-center rounded-lg border border-divider">
                          <button type="button" onClick={() => updateCartQuantity(product.name, quantity - 1)} aria-label={`Decrease ${product.name} quantity`} className="flex h-9 w-9 items-center justify-center text-text transition hover:bg-background">
                            <Minus size={15} aria-hidden="true" />
                          </button>
                          <span className="min-w-8 text-center text-sm font-medium text-main_text">{quantity}</span>
                          <button type="button" onClick={() => updateCartQuantity(product.name, quantity + 1)} aria-label={`Increase ${product.name} quantity`} className="flex h-9 w-9 items-center justify-center text-text transition hover:bg-background">
                            <Plus size={15} aria-hidden="true" />
                          </button>
                        </div>
                        <p className="font-semibold text-primary">&#8377;{(product.price * quantity).toLocaleString("en-IN")}</p>
                      </div>
                    </div>
                  </article>
                ))}
              </div>

              <aside className="rounded-xl border border-divider bg-white p-5 shadow-sm">
                <h2 className="font-primaryFont text-xl font-semibold text-main_text">Order summary</h2>
                <div className="mt-5 flex justify-between border-b border-divider pb-4 text-sm text-text">
                  <span>Subtotal ({items.reduce((count, item) => count + item.quantity, 0)} items)</span>
                  <span>&#8377;{total.toLocaleString("en-IN")}</span>
                </div>
                <div className="flex justify-between py-4 font-semibold text-main_text">
                  <span>Total</span>
                  <span>&#8377;{total.toLocaleString("en-IN")}</span>
                </div>
                <button type="button" disabled className="min-h-12 w-full cursor-not-allowed rounded-lg bg-gray-200 px-4 py-3 font-semibold text-gray-500">
                  Checkout coming soon
                </button>
              </aside>
            </div>
          )}
        </section>
      </main>
      <Footer />
    </>
  );
}
