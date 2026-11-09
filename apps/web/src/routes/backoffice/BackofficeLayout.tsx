import { Navigate, NavLink, Outlet, useLocation, useNavigate } from "react-router-dom";
import { hasRole, StaffProvider, useStaff } from "../../lib/auth/staff";
import { useT } from "../../lib/i18n";

type NavItem = { name: string; path: string; icon: string; roles: string[] };

// Sitemap SRS 9.2. Owner/Admin see everything; other roles see what they work with.
const navigation: NavItem[] = [
  { name: "Dashboard", path: "/backoffice", icon: "◫", roles: ["Manager", "Accountant"] },
  { name: "POS billing", path: "/pos", icon: "⌁", roles: ["Cashier", "Manager"] },
  { name: "Products", path: "/backoffice/products", icon: "◇", roles: ["Manager", "Cashier", "OnlineStaff"] },
  { name: "Stock", path: "/backoffice/inventory", icon: "▦", roles: ["Manager", "Cashier", "OnlineStaff"] },
  { name: "Bills", path: "/backoffice/bills", icon: "▤", roles: ["Manager", "Cashier", "Accountant"] },
  { name: "Online orders", path: "/backoffice/online-orders", icon: "⇪", roles: ["OnlineStaff", "Manager"] },
  { name: "Khata", path: "/backoffice/khata", icon: "₹", roles: ["Manager", "Cashier", "Accountant"] },
  { name: "Fall-pico", path: "/backoffice/fall-pico", icon: "✂", roles: ["Supervisor", "Manager"] },
  { name: "Purchasing", path: "/backoffice/purchasing", icon: "⇩", roles: ["Manager", "Accountant"] },
  { name: "People", path: "/backoffice/people", icon: "♙", roles: ["Manager", "Accountant"] },
  { name: "Salary", path: "/backoffice/payroll", icon: "₹", roles: ["Accountant"] },
  { name: "Tally", path: "/backoffice/tally", icon: "⇄", roles: ["Accountant"] },
  { name: "Reports", path: "/backoffice/reports", icon: "▥", roles: ["Accountant"] },
  { name: "AI tools", path: "/backoffice/ai", icon: "✦", roles: ["Manager", "Accountant", "OnlineStaff"] },
  { name: "Settings", path: "/backoffice/settings", icon: "⚙", roles: [] },
  { name: "My statement", path: "/backoffice/me", icon: "☺", roles: ["Employee", "Cashier", "Manager", "Supervisor", "OnlineStaff", "Accountant"] },
];

function Shell() {
  const { me, loading, logout } = useStaff();
  const location = useLocation();
  const navigate = useNavigate();
  const { t } = useT();

  if (loading) return <p className="p-8 text-sm text-gray-500">Loading…</p>;
  if (!me) return <Navigate to="/login" replace state={{ from: location }} />;

  const items = navigation.filter((item) => hasRole(me, ...item.roles));
  const initials = me.full_name.split(" ").map((p) => p[0]).join("").slice(0, 2).toUpperCase();

  return (
    <div className="min-h-screen bg-[#F7F7F7] text-[#111111] md:flex">
      <aside className="flex w-full shrink-0 flex-col bg-[#111111] text-white md:sticky md:top-0 md:h-screen md:w-60">
        <div className="flex items-center gap-3 border-b border-white/10 px-5 py-5">
          <div className="flex h-9 w-9 items-center justify-center bg-white text-lg font-bold text-black">W</div>
          <div>
            <p className="text-base font-semibold tracking-wide">WearVerse</p>
            <p className="text-xs text-gray-400">{me.role ?? "Staff"} workspace</p>
          </div>
        </div>
        <nav className="flex gap-1 overflow-x-auto px-3 py-3 md:flex-1 md:flex-col md:overflow-y-auto">
          {items.map((item) => (
            <NavLink key={item.path} to={item.path} end={item.path === "/backoffice"}
              className={({ isActive }) =>
                `flex shrink-0 items-center gap-3 rounded-md px-3 py-2.5 text-sm transition ${
                  isActive ? "bg-white font-semibold text-black" : "text-gray-300 hover:bg-white/10 hover:text-white"}`}>
              <span className="w-5 text-center">{item.icon}</span>
              {t(item.name)}
            </NavLink>
          ))}
        </nav>
        <div className="hidden border-t border-white/10 p-4 text-xs text-gray-400 md:block">
          Signed in as <span className="text-white">{me.full_name}</span>
        </div>
      </aside>

      <div className="min-w-0 flex-1">
        <header className="flex items-center justify-between gap-4 border-b border-gray-200 bg-white px-4 py-3 md:px-8">
          <p className="text-sm text-gray-500">WearVerse back office</p>
          <div className="flex items-center gap-3">
            <button type="button" onClick={() => { logout(); navigate("/login"); }}
              className="rounded-md px-3 py-2 text-sm text-gray-600 hover:bg-gray-100">{t("Log out")}</button>
            <div className="flex h-9 w-9 items-center justify-center rounded-full bg-[#111111] text-sm font-semibold text-white">{initials}</div>
          </div>
        </header>
        <Outlet />
      </div>
    </div>
  );
}

export default function BackofficeLayout() {
  return (
    <StaffProvider>
      <Shell />
    </StaffProvider>
  );
}
