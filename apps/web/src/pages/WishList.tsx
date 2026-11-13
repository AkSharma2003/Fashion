import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import Header from "../components/Header";
import Footer from "../components/Footer";
import Card, { type ClothingCardProduct } from "../components/Card";
import { apiData, ApiError } from "../lib/api/client";
import { toCardProduct, type StoreCard } from "../lib/storeCards";
import { getWishlist, removeFromWishlist, saveWishlist, wishlistUpdatedEventName } from "../lib/wishlist";

/** Saved products. Prices, photos and stock are refreshed from the shop; removed products drop out. */
export default function Wishlist() {
  const [products, setProducts] = useState<ClothingCardProduct[]>(getWishlist);
  const [removedNote, setRemovedNote] = useState("");

  useEffect(() => {
    const refreshWishlist = () => setProducts(getWishlist());
    window.addEventListener(wishlistUpdatedEventName(), refreshWishlist);
    window.addEventListener("storage", refreshWishlist);
    return () => {
      window.removeEventListener(wishlistUpdatedEventName(), refreshWishlist);
      window.removeEventListener("storage", refreshWishlist);
    };
  }, []);

  // Bring every saved item up to date once when the page opens.
  useEffect(() => {
    let cancelled = false;
    (async () => {
      const saved = getWishlist();
      const fresh: ClothingCardProduct[] = [];
      const gone: string[] = [];
      for (const item of saved) {
        if (!item.id) { fresh.push(item); continue; }
        try {
          fresh.push(toCardProduct(await apiData<StoreCard>(`/store/products/${encodeURIComponent(item.id)}`)));
        } catch (err) {
          if (err instanceof ApiError && err.status === 404) gone.push(item.name);
          else fresh.push(item);              // offline or server busy: keep the saved copy
        }
      }
      if (cancelled) return;
      saveWishlist(fresh);
      if (gone.length) setRemovedNote(`${gone.join(", ")} ${gone.length > 1 ? "are" : "is"} no longer available and was removed.`);
    })();
    return () => { cancelled = true; };
  }, []);

  return (
    <>
      <Header />
      <main className="min-h-screen bg-linear-to-br from-background to-Alt_background px-4 py-8 sm:px-6 sm:py-12 lg:px-8">
        <section className="mx-auto max-w-7xl">
          <h1 className="sr-only">My wishlist</h1>
          {products.length > 0 && (
            <div className="mb-3 flex justify-end">
              <button type="button" onClick={() => { if (window.confirm("Remove all items from your wishlist?")) saveWishlist([]); }}
                className="text-xs text-muted underline hover:text-main_text">Clear all</button>
            </div>
          )}
          {removedNote && <p role="status" className="mb-4 rounded-lg bg-surface px-4 py-2 text-sm text-text">{removedNote}</p>}

          {products.length > 0 ? (
            <div className="grid grid-cols-2 gap-x-3 gap-y-6 sm:grid-cols-3 sm:gap-x-4 md:grid-cols-4 xl:grid-cols-5">
              {products.map((product) => (
                <div key={product.id ?? product.name} className="relative">
                  <Card product={product} />
                  <button type="button" onClick={() => removeFromWishlist(product)}
                    className="mt-1 w-full rounded border border-divider bg-surface py-1.5 text-xs font-semibold text-muted hover:text-sale">
                    Remove
                  </button>
                </div>
              ))}
            </div>
          ) : (
            <div className="mx-auto max-w-lg rounded-2xl border border-divider bg-white px-6 py-12 text-center shadow-sm">
              <p className="font-primaryFont text-xl font-semibold text-main_text">Your wishlist is empty</p>
              <p className="mt-2 text-sm text-text">Tap the heart on any product to save it here.</p>
              <Link to="/" className="mt-6 inline-flex min-h-11 items-center justify-center rounded-lg bg-primary px-5 py-2.5 font-semibold text-white transition hover:bg-primary-dark">
                Explore designs
              </Link>
            </div>
          )}
        </section>
      </main>
      <Footer />
    </>
  );
}
