import { createContext, useContext, useEffect, useState, type ReactNode } from "react";
import { api } from "../api/client";
import { clearSession, getAccessToken } from "./session";

export type StaffMe = {
  id: string;
  full_name: string;
  phone_number: string;
  role: string | null;
  is_active: boolean;
};

type StaffState = { me: StaffMe | null; loading: boolean; logout: () => void; refresh: () => Promise<void> };

const StaffContext = createContext<StaffState>({ me: null, loading: true, logout: () => {}, refresh: async () => {} });

export function StaffProvider({ children }: { children: ReactNode }) {
  const [me, setMe] = useState<StaffMe | null>(null);
  const [loading, setLoading] = useState(true);

  async function refresh() {
    if (!getAccessToken()) {
      setMe(null);
      setLoading(false);
      return;
    }
    try {
      setMe(await api<StaffMe>("/auth/me"));
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
    <StaffContext.Provider value={{ me, loading, refresh, logout: () => { clearSession(); setMe(null); } }}>
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
