import type { ClothingCardProduct } from "../components/Card";
import { scheduleSave } from "./shoppingSync";

/** Wishlist in this browser. Items are matched by product id (name only for very old saved items),
 *  and the Wishlist page refreshes price, photo and stock from the shop. */
const WISHLIST_STORAGE_KEY = "wearverse-wishlist";
const WISHLIST_EVENT = "wearverse:wishlist-updated";

const keyOf = (p: Pick<ClothingCardProduct, "id" | "name">) => p.id ?? `name:${p.name}`;

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

export function saveWishlist(products: ClothingCardProduct[], saveToAccount = true) {
  try {
    window.localStorage.setItem(WISHLIST_STORAGE_KEY, JSON.stringify(products));
  } catch {
    // Keep the storefront usable when browser storage is unavailable.
  }
  window.dispatchEvent(new Event(WISHLIST_EVENT));
  if (saveToAccount) scheduleSave();
}

/** Replace the whole wishlist (loading it from the account, or clearing it at sign-out). */
export function replaceWishlist(products: ClothingCardProduct[], saveToAccount = true) {
  saveWishlist(products, saveToAccount);
}

export function wishlistUpdatedEventName() {
  return WISHLIST_EVENT;
}

export function isWishlisted(product: Pick<ClothingCardProduct, "id" | "name">): boolean {
  const key = keyOf(product);
  return getWishlist().some((item) => keyOf(item) === key);
}

export function wishlistCount(): number {
  return getWishlist().length;
}

/** Adds or removes the product; returns true when it is now saved. */
export function toggleWishlistProduct(product: ClothingCardProduct) {
  const key = keyOf(product);
  const current = getWishlist();
  const alreadySaved = current.some((item) => keyOf(item) === key);
  saveWishlist(alreadySaved ? current.filter((item) => keyOf(item) !== key) : [...current, product]);
  return !alreadySaved;
}

export function removeFromWishlist(product: Pick<ClothingCardProduct, "id" | "name">) {
  const key = keyOf(product);
  saveWishlist(getWishlist().filter((item) => keyOf(item) !== key));
}
