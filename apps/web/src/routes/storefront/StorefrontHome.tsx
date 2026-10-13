
import { useEffect, useState } from "react";
import Header from "../../components/Header";
import Footer from "../../components/Footer";
import Card, { type ClothingCardProduct } from "../../components/Card";
import clothingFallback from "../../assets/images/clothing-fallback.svg";
import { getProducts } from "../../lib/api/client";

type ApiProduct = {
  id: string;
  name: string;
  description: string | null;
  sku: string;
  barcode: string | null;
  category: string;
  selling_price_paise: number;
  is_active: boolean;
};

export default function StorefrontHome() {
  const [products, setProducts] = useState<ClothingCardProduct[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    let cancelled = false;

    async function loadProducts() {
      try {
        setLoading(true);
        setError("");

        const response = await getProducts();
        const apiProducts = response as ApiProduct[];

        const mappedProducts: ClothingCardProduct[] = apiProducts
          .filter((product) => product.is_active)
          .map((product) => ({
            name: product.name,
            description: product.description ?? product.category,
            price: product.selling_price_paise / 100,
            image: clothingFallback,
            imageAlt: product.name,
            colors: [],
            tag: product.category,
          }));

        if (!cancelled) {
          setProducts(mappedProducts);
        }
      } catch (err) {
        if (!cancelled) {
          setError(
            err instanceof Error
              ? err.message
              : "Products load nahi ho paaye."
          );
        }
      } finally {
        if (!cancelled) {
          setLoading(false);
        }
      }
    }

    void loadProducts();

    return () => {
      cancelled = true;
    };
  }, []);

  return (
    <>
      <Header />

      <main className="min-h-screen bg-linear-to-br from-background to-Alt_background px-3 py-6 sm:px-6 sm:py-14 lg:px-8">
        <section className="mx-auto max-w-7xl">
          {loading && (
            <p className="py-10 text-center text-text">
              Products load ho rahe hain...
            </p>
          )}

          {!loading && error && (
            <p className="py-10 text-center text-red-600">
              Products load nahi hue: {error}
            </p>
          )}

          {!loading && !error && products.length === 0 && (
            <p className="py-10 text-center text-text">
              Abhi koi product available nahi hai.
            </p>
          )}

          {!loading && !error && products.length > 0 && (
            <div className="grid grid-cols-1 gap-3 min-[360px]:grid-cols-2 sm:gap-6 lg:grid-cols-4">
              {products.map((product) => (
                <Card key={product.name} product={product} />
              ))}
            </div>
          )}
        </section>
      </main>

      <Footer />
    </>
  );
}
