import Card, { type ClothingCardProduct } from "./Card";

/** Grid of product cards with loading, error and empty states. */
export default function ProductGrid({ items, loading, error, empty = "No products here yet. Please check back soon." }: {
  items: ClothingCardProduct[]; loading: boolean; error: string; empty?: string;
}) {
  if (loading) {
    return (
      <div className="grid grid-cols-2 gap-x-3 gap-y-6 sm:grid-cols-3 sm:gap-x-4 md:grid-cols-4 xl:grid-cols-5" aria-busy="true" aria-label="Loading products">
        {Array.from({ length: 8 }).map((_, i) => (
          <div key={i} className="aspect-[4/6] animate-pulse rounded-xl bg-surface/70 sm:rounded-2xl" />
        ))}
      </div>
    );
  }
  if (error) {
    return <p role="alert" className="rounded-lg bg-red-50 px-4 py-3 text-sm text-red-700">Could not load products: {error}</p>;
  }
  if (!items.length) {
    return <p className="rounded-lg bg-surface px-4 py-8 text-center text-text">{empty}</p>;
  }
  return (
    <div className="grid grid-cols-2 gap-x-3 gap-y-6 sm:grid-cols-3 sm:gap-x-4 md:grid-cols-4 xl:grid-cols-5">
      {items.map((product) => <Card key={product.id ?? product.name} product={product} />)}
    </div>
  );
}
