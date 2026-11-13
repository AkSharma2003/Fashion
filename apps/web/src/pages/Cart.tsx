import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { Minus, Plus, X } from "lucide-react";
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

const rupees = (n: number) => `₹${Math.round(n).toLocaleString("en-IN")}`;

/** Bag: compact item rows and a price summary (MRP, discount, total). */
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
  const totalMrp = items.reduce((sum, item) => sum + Math.max(item.product.mrp ?? 0, item.product.price) * item.quantity, 0);
  const itemCount = items.reduce((count, item) => count + item.quantity, 0);
  const needSize = items.some((i) => !i.variantId);

  return (
    <>
      <Header />
      <main className="min-h-screen bg-background px-3 py-6 sm:px-6 sm:py-10 lg:px-8">
        <section className="mx-auto max-w-5xl">
          <h1 className="sr-only">Shopping bag</h1>

          {items.length === 0 ? (
            <div className="mx-auto max-w-md bg-white px-6 py-12 text-center">
              <p className="text-lg font-semibold text-main_text">Your bag is empty</p>
              <p className="mt-1 text-sm text-muted">Add a style you love and it will show up here.</p>
              <Link to="/" className="mt-6 inline-flex min-h-11 items-center justify-center rounded bg-primary px-6 text-sm font-semibold uppercase tracking-wide text-white hover:bg-primary-dark">
                Continue shopping
              </Link>
            </div>
          ) : (
            <div className="grid gap-5 md:grid-cols-[minmax(0,1fr)_20rem] md:items-start">
              <div className="space-y-3">
                {items.map(({ product, quantity, variantId, size, color, stockQuantity }) => {
                  const mrp = product.mrp && product.mrp > product.price ? product.mrp : 0;
                  return (
                    <article key={`${product.id ?? product.name}::${variantId ?? ""}::${size ?? ""}::${color ?? ""}`}
                      className="relative flex gap-3 border border-divider bg-white p-3">
                      <Link to={product.id ? `/product/${product.id}` : "#"} className="shrink-0">
                        <img src={product.image} alt={product.imageAlt} referrerPolicy="no-referrer"
                          onError={(event) => { event.currentTarget.onerror = null; event.currentTarget.src = clothingFallback; }}
                          className="aspect-[3/4] w-20 bg-Alt_background object-cover object-top sm:w-24" />
                      </Link>
                      <div className="min-w-0 flex-1 pr-7">
                        <h2 className="truncate text-sm font-semibold text-main_text">{product.name}</h2>
                        <p className="truncate text-xs text-muted">{product.description}</p>
                        <div className="mt-2 flex flex-wrap items-center gap-2 text-xs font-semibold text-main_text">
                          {size && <span className="rounded bg-Alt_background px-2 py-1">Size: {size}</span>}
                          {color && <span className="rounded bg-Alt_background px-2 py-1">{color}</span>}
                          <span className="inline-flex items-center rounded bg-Alt_background">
                            <button type="button" onClick={() => updateCartQuantity(product.name, quantity - 1, variantId)}
                              aria-label={`Decrease ${product.name} quantity`} className="flex h-6 w-6 items-center justify-center">
                              <Minus size={12} aria-hidden="true" />
                            </button>
                            <span className="min-w-8 text-center">Qty: {quantity}</span>
                            <button type="button" disabled={stockQuantity !== undefined && quantity >= stockQuantity}
                              onClick={() => updateCartQuantity(product.name, quantity + 1, variantId)}
                              aria-label={`Increase ${product.name} quantity`} className="flex h-6 w-6 items-center justify-center disabled:opacity-30">
                              <Plus size={12} aria-hidden="true" />
                            </button>
                          </span>
                        </div>
                        <p className="mt-2 flex flex-wrap items-baseline gap-x-1.5 text-sm">
                          <span className="font-semibold text-main_text">{rupees(product.price * quantity)}</span>
                          {mrp > 0 && (
                            <>
                              <span className="text-xs text-muted line-through">{rupees(mrp * quantity)}</span>
                              <span className="text-xs font-semibold text-[#E8762C]">{Math.round((1 - product.price / mrp) * 100)}% OFF</span>
                            </>
                          )}
                        </p>
                        {!variantId && (
                          <p className="mt-1 text-xs font-semibold text-sale">
                            Size not chosen. <Link className="underline" to={product.id ? `/product/${product.id}` : "/"}>Choose a size</Link>
                          </p>
                        )}
                      </div>
                      <button type="button" onClick={() => removeFromCart(product.name, variantId)}
                        aria-label={`Remove ${product.name}${size ? ` size ${size}` : ""}${color ? ` ${color}` : ""} from bag`}
                        className="absolute right-2 top-2 flex h-7 w-7 items-center justify-center rounded-full text-muted hover:bg-Alt_background hover:text-main_text">
                        <X size={16} aria-hidden="true" />
                      </button>
                    </article>
                  );
                })}
              </div>

              <aside className="border border-divider bg-white p-4 md:sticky md:top-24">
                <h2 className="text-xs font-bold uppercase tracking-wide text-muted">Price details ({itemCount} {itemCount === 1 ? "item" : "items"})</h2>
                <dl className="mt-3 space-y-2 text-sm text-main_text">
                  <div className="flex justify-between"><dt>Total MRP</dt><dd>{rupees(totalMrp)}</dd></div>
                  {totalMrp > total && (
                    <div className="flex justify-between"><dt>Discount on MRP</dt><dd className="text-[#03A685]">−{rupees(totalMrp - total)}</dd></div>
                  )}
                  <div className="flex justify-between"><dt>Shipping</dt><dd className="text-muted">Calculated at checkout</dd></div>
                </dl>
                <div className="mt-3 flex justify-between border-t border-divider pt-3 font-bold text-main_text">
                  <span>Total amount</span><span>{rupees(total)}</span>
                </div>
                {totalMrp > total && (
                  <p className="mt-2 text-xs font-semibold text-[#03A685]">You save {rupees(totalMrp - total)} on this order</p>
                )}
                <Link to={needSize ? "#" : "/checkout"} aria-disabled={needSize}
                  onClick={(e) => { if (needSize) e.preventDefault(); }}
                  className={`mt-4 flex min-h-12 w-full items-center justify-center rounded bg-primary px-4 text-sm font-semibold uppercase tracking-wide text-white hover:bg-primary-dark ${needSize ? "cursor-not-allowed opacity-50" : ""}`}>
                  Place order
                </Link>
                {needSize && <p className="mt-2 text-xs text-sale">Choose a size for every item first.</p>}
              </aside>
            </div>
          )}
        </section>
      </main>
      <Footer />
    </>
  );
}
