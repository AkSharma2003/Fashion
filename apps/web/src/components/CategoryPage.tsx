import Header from "./Header";
import Footer from "./Footer";
import ProductGrid from "./ProductGrid";
import { useStoreProducts } from "../lib/store";
import { useSeo } from "../lib/seo";

/** Shared page for Sarees / Suits / Kids / New arrivals, filled from the store API. */
export default function CategoryPage({ title, subtitle, category, sort = "new", pageSize }: {
  title: string; subtitle: string; category?: string; sort?: "new" | "price_asc" | "price_desc" | "name"; pageSize?: number;
}) {
  const { items, loading, error } = useStoreProducts({ category, sort, pageSize });
  useSeo({ title: `${title} | WearVerse`, description: subtitle });
  return (
    <>
      <Header />
      <main className="min-h-screen bg-linear-to-br from-background to-Alt_background px-4 py-10 sm:px-6 sm:py-14 lg:px-8">
        <section className="mx-auto max-w-7xl">
          <header className="mb-6 sm:mb-8">
            <h1 className="font-primaryFont text-3xl font-semibold text-primary sm:text-4xl">{title}</h1>
            <p className="mt-2 text-text">{subtitle}</p>
          </header>
          <ProductGrid items={items} loading={loading} error={error} />
        </section>
      </main>
      <Footer />
    </>
  );
}
