import { useEffect, useState } from "react";
import { apiData } from "./api/client";
import { toCardProduct, type StoreCard } from "./storeCards";
import type { ClothingCardProduct } from "../components/Card";

/** Products for the website from the public store API (same stock as the shop). */
export function useStoreProducts(opts: { category?: string; sort?: "new" | "price_asc" | "price_desc" | "name"; pageSize?: number } = {}) {
  const { category, sort = "new", pageSize = 48 } = opts;
  const [items, setItems] = useState<ClothingCardProduct[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError("");
    const params = new URLSearchParams({ sort, page_size: String(pageSize) });
    if (category) params.set("category", category);
    apiData<{ items: StoreCard[] }>(`/store/products?${params}`)
      .then((d) => { if (!cancelled) setItems(d.items.map(toCardProduct)); })
      .catch((e: unknown) => { if (!cancelled) setError(e instanceof Error ? e.message : "Could not load products."); })
      .finally(() => { if (!cancelled) setLoading(false); });
    return () => { cancelled = true; };
  }, [category, sort, pageSize]);

  return { items, loading, error };
}
