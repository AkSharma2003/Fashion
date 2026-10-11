import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import Header from "../components/Header";
import Footer from "../components/Footer";
import Card, { type ClothingCardProduct } from "../components/Card";
import { getWishlist, wishlistUpdatedEventName } from "../lib/wishlist";

export default function Wishlist() {
  const [products, setProducts] = useState<ClothingCardProduct[]>(getWishlist);

  useEffect(() => {
    const refreshWishlist = () => setProducts(getWishlist());
    window.addEventListener(wishlistUpdatedEventName(), refreshWishlist);
    window.addEventListener("storage", refreshWishlist);

    return () => {
      window.removeEventListener(wishlistUpdatedEventName(), refreshWishlist);
      window.removeEventListener("storage", refreshWishlist);
    };
  }, []);

  return (
    <>
      <Header />
      <main className="min-h-screen bg-linear-to-br from-background to-Alt_background px-4 py-10 sm:px-6 sm:py-14 lg:px-8">
        <section className="mx-auto max-w-7xl">
          <div className="mb-8 text-center sm:mb-10">
            <p className="text-xs font-semibold uppercase tracking-[0.22em] text-primary sm:text-sm">
              Your saved styles
            </p>
            <h1 className="mt-2 font-primaryFont text-3xl font-semibold text-main_text sm:text-4xl">
              Wishlist
            </h1>
          </div>

          {products.length > 0 ? (
            <div className="grid grid-cols-1 gap-3 min-[360px]:grid-cols-2 sm:gap-6 lg:grid-cols-3">
              {products.map((product) => (
                <Card key={product.name} product={product} />
              ))}
            </div>
          ) : (
            <div className="mx-auto max-w-lg rounded-2xl border border-divider bg-white px-6 py-12 text-center shadow-sm">
              <p className="font-primaryFont text-xl font-semibold text-main_text">Your wishlist is empty</p>
              <p className="mt-2 text-sm text-text">Tap the heart on a design to save it here.</p>
              <Link
                to="/"
                className="mt-6 inline-flex min-h-11 items-center justify-center rounded-lg bg-primary px-5 py-2.5 font-semibold text-white transition hover:bg-primary-dark"
              >
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
