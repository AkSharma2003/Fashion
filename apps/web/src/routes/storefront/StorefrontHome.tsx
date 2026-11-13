import { STORE_NAME } from "../../lib/brand";
import Header from "../../components/Header";
import Footer from "../../components/Footer";
import ProductGrid from "../../components/ProductGrid";
import { useStoreProducts } from "../../lib/store";
import { useSeo } from "../../lib/seo";

/** Website home: the newest products (categories are in the header), from the store API (same stock as the shop). */
export default function StorefrontHome() {
  const { items, loading, error } = useStoreProducts({ sort: "new", pageSize: 24 });
  useSeo({ title: `${STORE_NAME} | Sarees, suits and kids wear`,
           description: `Shop sarees, suits and kids wear from ${STORE_NAME}. Same stock as our shops, free fall-pico on sarees above ₹1,000.` });

  return (
    <>
      <Header />

      <main className="min-h-screen bg-linear-to-br from-background to-Alt_background px-3 py-6 sm:px-6 sm:py-14 lg:px-8">
        <section className="mx-auto max-w-7xl">
          <h1 className="sr-only">New in the shop</h1>
          <ProductGrid items={items} loading={loading} error={error} empty="No products are available yet." />
        </section>
      </main>

      <Footer />
    </>
  );
}
