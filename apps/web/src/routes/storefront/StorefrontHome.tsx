import { Link } from "react-router-dom";
import Header from "../../components/Header";
import Footer from "../../components/Footer";
import ProductGrid from "../../components/ProductGrid";
import { useStoreProducts } from "../../lib/store";
import { useSeo } from "../../lib/seo";

const CATEGORIES = [
  { name: "Sarees", to: "/sarees", note: "Silk, cotton, party wear" },
  { name: "Suits", to: "/suits", note: "Anarkali and straight" },
  { name: "Kids", to: "/kids", note: "Festive and everyday" },
  { name: "New Arrivals", to: "/new-arrivals", note: "Latest in the shop" },
];

/** Website home: shop by category and the newest products, from the store API (same stock as the shop). */
export default function StorefrontHome() {
  const { items, loading, error } = useStoreProducts({ sort: "new", pageSize: 24 });
  useSeo({ title: "WearVerse | Sarees, suits and kids wear",
           description: "Shop sarees, suits and kids wear from WearVerse. Same stock as our shop, free fall-pico on sarees above ₹1,000." });

  return (
    <>
      <Header />

      <main className="min-h-screen bg-linear-to-br from-background to-Alt_background px-3 py-6 sm:px-6 sm:py-14 lg:px-8">
        <section className="mx-auto max-w-7xl">
          <nav aria-label="Shop by category" className="mb-8 grid grid-cols-2 gap-3 sm:mb-12 sm:grid-cols-4 sm:gap-4">
            {CATEGORIES.map((c) => (
              <Link key={c.to} to={c.to}
                className="rounded-xl border border-divider bg-surface px-4 py-4 shadow-sm transition hover:-translate-y-0.5 hover:border-primary hover:shadow-md sm:py-6">
                <span className="block font-primaryFont text-lg font-semibold text-primary sm:text-2xl">{c.name}</span>
                <span className="mt-1 block text-xs text-text sm:text-sm">{c.note}</span>
              </Link>
            ))}
          </nav>

          <h2 className="mb-4 font-primaryFont text-2xl font-semibold text-main_text sm:mb-6 sm:text-3xl">New in the shop</h2>
          <ProductGrid items={items} loading={loading} error={error} empty="No products are available yet." />
        </section>
      </main>

      <Footer />
    </>
  );
}
