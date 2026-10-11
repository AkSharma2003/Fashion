import type { ClothingCardProduct } from "../components/Card";

export type CartItem = {
  product: ClothingCardProduct;
  quantity: number;
};

const CART_STORAGE_KEY = "wearverse-cart";
const CART_EVENT = "wearverse:cart-updated";

export function getCart(): CartItem[] {
  try {
    const saved = window.localStorage.getItem(CART_STORAGE_KEY);
    if (!saved) return [];

    const items: unknown = JSON.parse(saved);
    return Array.isArray(items) ? (items as CartItem[]) : [];
  } catch {
    return [];
  }
}

function saveCart(items: CartItem[]) {
  try {
    window.localStorage.setItem(CART_STORAGE_KEY, JSON.stringify(items));
    window.dispatchEvent(new Event(CART_EVENT));
  } catch {
    // Keep the storefront usable when browser storage is unavailable.
  }
}

export function cartUpdatedEventName() {
  return CART_EVENT;
}

export function addToCart(product: ClothingCardProduct) {
  const items = getCart();
  const existing = items.find((item) => item.product.name === product.name);

  if (existing) {
    saveCart(items.map((item) =>
      item.product.name === product.name
        ? { ...item, quantity: item.quantity + 1 }
        : item
    ));
    return;
  }

  saveCart([...items, { product, quantity: 1 }]);
}

export function updateCartQuantity(productName: string, quantity: number) {
  const items = getCart()
    .map((item) => item.product.name === productName ? { ...item, quantity } : item)
    .filter((item) => item.quantity > 0);
  saveCart(items);
}

export function removeFromCart(productName: string) {
  saveCart(getCart().filter((item) => item.product.name !== productName));
}
