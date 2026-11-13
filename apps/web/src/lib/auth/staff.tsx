import { createContext, useContext, useEffect, useState, type ReactNode } from "react";
import { api, apiData } from "../api/client";
import { getSelectedShop, setSelectedShop, type Shop } from "../shops";
import { clearSession, getAccessToken } from "./session";

export type StaffMe = {
  id: string;
  full_name: string;
  phone_number: string;
  role: string | null;
  is_active: boolean;
  shop_id: string | null;      // null = works in all shops
};

type StaffState = { me: StaffMe | null; loading: boolean; logout: () => void; refresh: () => Promise<void>;
  shops: Shop[]; shopId: string; setShopId: (id: string) => void };

const StaffContext = createContext<StaffState>({ me: null, loading: true, logout: () => {}, refresh: async () => {},
  shops: [], shopId: "all", setShopId: () => {} });

export function StaffProvider({ children }: { children: ReactNode }) {
  const [me, setMe] = useState<StaffMe | null>(null);
  const [loading, setLoading] = useState(true);
  const [shops, setShops] = useState<Shop[]>([]);
  const [shopId, setShopIdState] = useState(getSelectedShop());

  async function refresh() {
    if (!getAccessToken()) {
      setMe(null);
      setLoading(false);
      return;
    }
    try {
      const who = await api<StaffMe>("/auth/me");
      setMe(who);
      const list = await apiData<Shop[]>("/shops").catch(() => [] as Shop[]);
      setShops(list);
      // Staff tied to one shop always work in it; others keep their last choice if it still exists.
      const next = who.shop_id ?? (list.some((s) => s.id === getSelectedShop()) ? getSelectedShop() : "all");
      setSelectedShop(next);
      setShopIdState(next);
    } catch {
      setMe(null);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void refresh();
  }, []);

  return (
    <StaffContext.Provider value={{ me, loading, refresh, shops, shopId,
      setShopId: (id: string) => { setSelectedShop(id); setShopIdState(id); },
      logout: () => { clearSession(); setMe(null); } }}>
      {children}
    </StaffContext.Provider>
  );
}

export function useStaff() {
  return useContext(StaffContext);
}

/** Owner and Admin can open everything staff can. */
export function hasRole(me: StaffMe | null, ...roles: string[]): boolean {
  if (!me?.role) return false;
  return me.role === "Owner" || me.role === "Admin" || roles.includes(me.role);
}
