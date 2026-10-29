
import { useEffect, useState } from "react";
import Header from "../../components/Header";
import Footer from "../../components/Footer";
import Card, { type ClothingCardProduct } from "../../components/Card";
import clothingFallback from "../../assets/images/clothing-fallback.svg";
import {
  getProducts,
  getProductImages,
  type Product,
} from "../../lib/api/client";

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

        const apiProducts = await getProducts();
        const activeProducts = apiProducts.filter(
          (product: Product) => product.is_active
        );

        const mappedProducts = await Promise.all(
          activeProducts.map(async (product: Product) => {
            let image = clothingFallback;

            try {
              const images = await getProductImages(product.id);
              const firstImage = images[0];

              if (firstImage?.image_url) {
                image = firstImage.image_url.startsWith("http")
                  ? firstImage.image_url
                  : `${(import.meta.env.VITE_API_URL ?? "").replace(
                      /\/$/,
                      ""
                    )}${firstImage.image_url.startsWith("/") ? "" : "/"}${
                      firstImage.image_url
                    }`;
              }
            } catch {
              // Keep the fallback image if image loading fails.
            }

            return {
              id: product.id,
              name: product.name,
              description: product.description ?? product.category,
              price: product.selling_price_paise / 100,
              image,
              imageAlt: product.name,
              colors: [],
              tag: product.category,
            } satisfies ClothingCardProduct;
          })
        );

        if (!cancelled) {
          setProducts(mappedProducts);
        }
      } catch (err) {
        if (!cancelled) {
          setError(
            err instanceof Error
              ? err.message
              : "Unable to load products."
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
              Loading products...
            </p>
          )}

          {!loading && error && (
            <p className="py-10 text-center text-red-600">
              Unable to load products: {error}
            </p>
          )}

          {!loading && !error && products.length === 0 && (
            <p className="py-10 text-center text-text">
              No products are available yet.
            </p>
          )}

          {!loading && !error && products.length > 0 && (
            <div className="grid grid-cols-1 gap-3 min-[360px]:grid-cols-2 sm:gap-6 lg:grid-cols-4">
              {products.map((product) => (
                <Card
                  key={product.id ?? product.name}
                  product={product}
                />
              ))}
            </div>
          )}
        </section>
      </main>

      <Footer />
    </>
  );
}
