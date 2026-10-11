import { Link, useSearchParams } from "react-router-dom";
import Header from "../components/Header";
import Footer from "../components/Footer";
import Card from "../components/Card";
import { kidsProducts, sareeProducts, suitProducts } from "../data/catalog";

const catalog = [
  ...sareeProducts.map((product) => ({ product, category: "Sarees" })),
  ...suitProducts.map((product) => ({ product, category: "Suits" })),
  ...kidsProducts.map((product) => ({ product, category: "Kids" })),
];

export default function SearchResults() {
  const [searchParams] = useSearchParams();
  const query = (searchParams.get("q") ?? "").trim();
  const normalizedQuery = query.toLocaleLowerCase();
  const results = catalog.filter(({ product, category }) =>
    `${product.name} ${product.description} ${product.colors.map((color) => color.name).join(" ")} ${category} ${product.tag ?? ""}`
      .toLocaleLowerCase()
      .includes(normalizedQuery)
  );

  return (
    <>
      <Header />
      <main className="min-h-screen bg-linear-to-br from-background to-Alt_background px-4 py-10 sm:px-6 sm:py-14 lg:px-8">
        <section className="mx-auto max-w-7xl">
          <div className="mb-8 text-center sm:mb-10">
            <p className="text-xs font-semibold uppercase tracking-[0.22em] text-primary sm:text-sm">
              Search the collection
            </p>
            <h1 className="mt-2 font-primaryFont text-3xl font-semibold text-main_text sm:text-4xl">
              {query ? `Results for “${query}”` : "Search products"}
            </h1>
            {query && (
              <p className="mt-3 text-sm text-text">
                {results.length} {results.length === 1 ? "design" : "designs"} found
              </p>
            )}
          </div>

          {results.length > 0 ? (
            <div className="grid grid-cols-1 gap-3 min-[360px]:grid-cols-2 sm:gap-6 lg:grid-cols-4">
              {results.map(({ product }) => (
                <Card key={product.name} product={product} />
              ))}
            </div>
          ) : (
            <div className="mx-auto max-w-lg rounded-2xl border border-divider bg-white px-6 py-12 text-center shadow-sm">
              <p className="font-primaryFont text-xl font-semibold text-main_text">
                {query ? "No matching designs found" : "Enter a search term to get started"}
              </p>
              <p className="mt-2 text-sm text-text">
                Try a product name or category such as saree, suit, or kids.
              </p>
              <Link to="/" className="mt-6 inline-flex min-h-11 items-center justify-center rounded-lg bg-primary px-5 py-2.5 font-semibold text-white transition hover:bg-primary-dark">
                Explore all designs
              </Link>
            </div>
          )}
        </section>
      </main>
      <Footer />
    </>
  );
}
