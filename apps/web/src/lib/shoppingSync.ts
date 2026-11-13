/** Keeps the bag and wishlist on the signed-in customer's account.
 *
 * - Guests: bag and wishlist live only in this browser.
 * - Sign-in: what the guest picked is added to the account's saved bag and wishlist, and the result is shown.
 * - Signed in: every change is saved to the account (so it follows them to another device).
 * - Sign-out: both are removed from this browser.
 */
import { getCustomerToken } from "./auth/session";
import { getCart, replaceCart, type CartItem } from "./cart";
import { customerApi } from "./customer";
import { toCardProduct, type StoreCard, type StoreVariant } from "./storeCards";
import { getWishlist, replaceWishlist } from "./wishlist";
import type { ClothingCardProduct } from "../components/Card";

type Saved = { wishlist: StoreCard[]; cart: { product: StoreCard; variant: StoreVariant; qty: number }[] };
const SYNCED_KEY = "wearverse.shopping_synced";

let timer: ReturnType<typeof setTimeout> | undefined;

function localPayload() {
  return {
    wishlist: getWishlist().map((p) => p.id).filter((id): id is string => Boolean(id)),
    cart: getCart().filter((i) => i.variantId).map((i) => ({ variant_id: i.variantId!, qty: Math.min(i.quantity, 20) })),
  };
}

function showSaved(data: Saved) {
  const wishlist: ClothingCardProduct[] = data.wishlist.map(toCardProduct);
  const cart: CartItem[] = data.cart.map(({ product, variant, qty }) => ({
    product: { ...toCardProduct(product), price: variant.price_paise / 100 },
    quantity: qty,
    variantId: variant.id,
    size: variant.size ?? undefined,
    color: variant.color ?? undefined,
    sku: variant.sku,
    stockQuantity: variant.available,
  }));
  replaceWishlist(wishlist, false);
  replaceCart(cart, false);
}

/** Called after every change in the bag or wishlist: save to the account a moment later. */
export function scheduleSave(): void {
  if (!getCustomerToken()) return;
  clearTimeout(timer);
  timer = setTimeout(() => {
    void customerApi("/store/me/shopping", { method: "PUT", body: JSON.stringify(localPayload()) }).catch(() => undefined);
  }, 400);
}

/** Right after sign-in (or the first page load of a signed-in visit): join guest picks with the account. */
export async function mergeOnSignIn(): Promise<void> {
  if (!getCustomerToken()) return;
  try {
    showSaved(await customerApi<Saved>("/store/me/shopping/merge", { method: "POST", body: JSON.stringify(localPayload()) }));
    sessionStorage.setItem(SYNCED_KEY, "1");
  } catch {
    // offline: keep what the browser has; it is saved on the next change
  }
}

export function syncedThisVisit(): boolean {
  try {
    return sessionStorage.getItem(SYNCED_KEY) === "1";
  } catch {
    return false;
  }
}

/** Sign-out: the next person on this browser must not see this customer's bag or wishlist. */
export function clearLocalShopping(): void {
  clearTimeout(timer);
  replaceWishlist([], false);
  replaceCart([], false);
  try {
    sessionStorage.removeItem(SYNCED_KEY);
  } catch {
    // ignore
  }
}
