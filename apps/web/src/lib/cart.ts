
import type { ClothingCardProduct } from "../components/Card";

export type CartItem = {
  product: ClothingCardProduct;
  quantity: number;
  variantId?: string;
  size?: string;
  color?: string;
  sku?: string;
  stockQuantity?: number;
};

const CART_STORAGE_KEY = "wearverse-cart";
const CART_EVENT = "wearverse:cart-updated";

function getItemKey(item: CartItem): string {
  return [
    item.product.id ?? item.product.name,
    item.variantId ?? "",
    item.size ?? "",
    item.color ?? "",
  ].join("::");
}

export function getCart(): CartItem[] {
  try {
    const saved = window.localStorage.getItem(CART_STORAGE_KEY);
    if (!saved) return [];

    const parsed: unknown = JSON.parse(saved);
    if (!Array.isArray(parsed)) return [];

    // Purane cart items ko bhi support karo.
    return parsed.filter(
      (item): item is CartItem =>
        typeof item === "object" &&
        item !== null &&
        "product" in item &&
        "quantity" in item &&
        typeof item.quantity === "number",
    );
  } catch {
    return [];
  }
}

function saveCart(items: CartItem[]) {
  try {
    window.localStorage.setItem(CART_STORAGE_KEY, JSON.stringify(items));
    window.dispatchEvent(new Event(CART_EVENT));
  } catch {
    // Browser storage unavailable hone par storefront chalta rahega.
  }
}

export function cartUpdatedEventName() {
  return CART_EVENT;
}

export type AddToCartOptions = {
  variantId?: string;
  size?: string;
  color?: string;
  sku?: string;
  stockQuantity?: number;
  quantity?: number;
};

export function addToCart(
  product: ClothingCardProduct,
  options: AddToCartOptions = {},
) {
  const items = getCart();
  const newItem: CartItem = {
    product,
    quantity: options.quantity ?? 1,
    variantId: options.variantId,
    size: options.size,
    color: options.color,
    sku: options.sku,
    stockQuantity: options.stockQuantity,
  };

  const key = getItemKey(newItem);
  const existing = items.find((item) => getItemKey(item) === key);

  if (existing) {
    const requestedQuantity = existing.quantity + newItem.quantity;
    const maxStock = options.stockQuantity ?? existing.stockQuantity;

    if (maxStock !== undefined && requestedQuantity > maxStock) {
      return false;
    }

    saveCart(
      items.map((item) =>
        getItemKey(item) === key
          ? { ...item, quantity: requestedQuantity }
          : item,
      ),
    );
    return true;
  }

  if (
    options.stockQuantity !== undefined &&
    newItem.quantity > options.stockQuantity
  ) {
    return false;
  }

  saveCart([...items, newItem]);
  return true;
}

export function updateCartQuantity(
  productName: string,
  quantity: number,
  variantId?: string,
) {
  const items = getCart();

  const target = items.find(
    (item) =>
      item.product.name === productName &&
      (variantId === undefined || item.variantId === variantId),
  );

  if (!target) return;

  if (quantity <= 0) {
    saveCart(items.filter((item) => item !== target));
    return;
  }

  if (
    target.stockQuantity !== undefined &&
    quantity > target.stockQuantity
  ) {
    return;
  }

  saveCart(
    items.map((item) =>
      item === target ? { ...item, quantity } : item,
    ),
  );
}

export function removeFromCart(
  productName: string,
  variantId?: string,
) {
  const items = getCart();

  if (variantId === undefined) {
    saveCart(items.filter((item) => item.product.name !== productName));
    return;
  }

  saveCart(
    items.filter(
      (item) =>
        !(
          item.product.name === productName &&
          item.variantId === variantId
        ),
    ),
  );
}
