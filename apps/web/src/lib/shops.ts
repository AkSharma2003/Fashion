/** Which shop the back office is looking at (Sethi Saree Sansar, Sethi Suit, Sethi Kids, or all).
 *  Sent to the API as the X-Shop-Id header. Staff tied to one shop always get their own shop from the server. */
export type Shop = { id: string; code: string; name: string; gstin: string | null; state_code: string | null;
  address: string | null; phone: string | null; tally_company: string | null; is_main: boolean; is_active: boolean };

const KEY = "wearverse.shop";
const EVENT = "wearverse:shop-changed";

export function getSelectedShop(): string {
  try {
    return localStorage.getItem(KEY) || "all";
  } catch {
    return "all";
  }
}

export function setSelectedShop(shopId: string): void {
  try {
    localStorage.setItem(KEY, shopId);
  } catch {
    // storage blocked: the choice lasts until reload
  }
  window.dispatchEvent(new CustomEvent(EVENT, { detail: shopId }));
}

export function onShopChange(fn: (shopId: string) => void): () => void {
  const handler = (e: Event) => fn((e as CustomEvent<string>).detail);
  window.addEventListener(EVENT, handler);
  return () => window.removeEventListener(EVENT, handler);
}
