import clothingFallback from "../assets/images/clothing-fallback.svg";
import type { ClothingCardProduct } from "../components/Card";

/** One size/colour of a product, as the public store API returns it. */
export type StoreVariant = {
  id: string; size: string | null; color: string | null; sku: string; price_paise: number; available: number;
};

/** Product card from /store or /ai endpoints. */
export type StoreCard = {
  id: string; name: string; category: string; description: string | null; price_from_paise: number;
  price_to_paise: number; mrp_paise?: number | null; image_url: string | null; in_stock: boolean; colors: string[]; sizes: string[];
  single_variant?: StoreVariant | null;
};

export function toCardProduct(c: StoreCard): ClothingCardProduct {
  return {
    id: c.id, name: c.name, description: c.category, price: c.price_from_paise / 100,
    mrp: c.mrp_paise ? c.mrp_paise / 100 : null,
    image: c.image_url ?? clothingFallback, imageAlt: c.name,
    colors: c.colors.map((name) => ({ name, value: name.toLowerCase() })),
    tag: c.in_stock ? undefined : "Out of stock",
    inStock: c.in_stock,
    variant: c.single_variant ?? undefined,
  };
}
