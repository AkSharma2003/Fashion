import type { ClothingCardProduct } from "../components/Card";

const WISHLIST_STORAGE_KEY = "wearverse-wishlist";
const WISHLIST_EVENT = "wearverse:wishlist-updated";

export function getWishlist(): ClothingCardProduct[] {
  try {
    const saved = window.localStorage.getItem(WISHLIST_STORAGE_KEY);
    if (!saved) return [];

    const products: unknown = JSON.parse(saved);
    return Array.isArray(products) ? (products as ClothingCardProduct[]) : [];
  } catch {
    return [];
  }
}

export function saveWishlist(products: ClothingCardProduct[]) {
  try {
    window.localStorage.setItem(WISHLIST_STORAGE_KEY, JSON.stringify(products));
    window.dispatchEvent(new Event(WISHLIST_EVENT));
  } catch {
    // Keep the storefront usable when browser storage is unavailable.
  }
}

export function wishlistUpdatedEventName() {
  return WISHLIST_EVENT;
}

export function toggleWishlistProduct(product: ClothingCardProduct) {
  const current = getWishlist();
  const alreadySaved = current.some((item) => item.name === product.name);
  const updated = alreadySaved
    ? current.filter((item) => item.name !== product.name)
    : [...current, product];

  saveWishlist(updated);
  return !alreadySaved;
}
