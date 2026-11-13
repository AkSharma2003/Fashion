import { lazy, Suspense } from "react";
import { Link, Navigate } from "react-router-dom";
import { LogOut } from "lucide-react";
import { StaffProvider, useStaff } from "../lib/auth/staff";
import { BACK_OFFICE_ROLES, clearSession, getAccessToken, staffHome } from "../lib/auth/session";

const MyStatementPage = lazy(() => import("./backoffice/MyStatementPage"));
const ROLE_LABEL: Record<string, string> = { OnlineStaff: "Online staff" };

/** A staff member's own profile. Employees see only this (no back office). */
function Profile() {
  const { me, loading, shops } = useStaff();
  if (!loading && !me && !getAccessToken()) return <Navigate to="/login?next=/me" replace />;
  if (!me) return <p className="p-8 text-sm text-gray-500">Loading…</p>;
  const shop = shops.find((s) => s.id === me.shop_id);
  const initials = me.full_name.split(" ").map((p) => p[0]).join("").slice(0, 2).toUpperCase();
  const backOffice = BACK_OFFICE_ROLES.includes(me.role ?? "");

  return (
    <div className="min-h-screen bg-[#F7F7F7] text-[#111111]">
      <header className="flex items-center justify-between bg-[#111111] px-4 py-3 text-white sm:px-8">
        <Link to="/" className="text-lg font-semibold tracking-wide">WearVerse</Link>
        <div className="flex items-center gap-2 text-sm">
          {backOffice && <Link to={staffHome(me.role)} className="rounded px-3 py-1.5 hover:bg-white/10">Back office</Link>}
          <button type="button" onClick={() => { clearSession(); window.location.replace("/login"); }}
            className="inline-flex items-center gap-1.5 rounded px-3 py-1.5 hover:bg-white/10"><LogOut size={15} /> Log out</button>
        </div>
      </header>
      <main className="mx-auto max-w-5xl px-4 py-6 sm:px-8">
        <section className="flex flex-wrap items-center gap-4 rounded-xl border border-gray-200 bg-white p-5">
          <span className="flex h-16 w-16 items-center justify-center rounded-full bg-[#111111] text-xl font-semibold text-white">{initials}</span>
          <div className="min-w-0">
            <h1 className="text-xl font-semibold">{me.full_name}</h1>
            <p className="text-sm text-gray-600">+91 {me.phone_number}</p>
            <p className="mt-1 text-sm">
              <span className="rounded bg-gray-100 px-2 py-0.5 font-medium">{ROLE_LABEL[me.role ?? ""] ?? me.role ?? "Staff"}</span>
              <span className="ml-2 text-gray-600">{shop ? shop.name : "All shops"}</span>
            </p>
          </div>
        </section>
        <div className="mt-4">
          <Suspense fallback={<p className="p-4 text-sm text-gray-500">Loading…</p>}>
            <MyStatementPage />
          </Suspense>
        </div>
      </main>
    </div>
  );
}

export default function StaffProfile() {
  return (
    <StaffProvider>
      <Profile />
    </StaffProvider>
  );
}
