
import { icons } from "lucide-react";
import { NavLink, Outlet } from "react-router-dom";

const navigation = [
  { name: "Dashboard", path: "/backoffice", icon: "◫" },
  { name: "Orders", path: "/backoffice/orders", icon: "▤" },
  { name: "Online Orders", path:"/Backoffice/online-orders"},
  { name: "Products", path: "/backoffice/products", icon: "◇" },
  { name: "Inventory", path: "/backoffice/inventory", icon: "▦" },
  { name: "Customers", path: "/backoffice/customers", icon: "♙" },
  { name: "Khata", path: "/backoffice/khata", icon: "₹" },
  { name: "Fall-Pico", path: "/backoffice/fall-pico", icon: "✂" },
  { name: "Reports", path: "/backoffice/reports", icon: "▥" },
  { name: "Settings", path: "/backoffice/settings", icon: "⚙" },
];

export default function BackofficeLayout() {
  return (
    <div className="min-h-screen bg-[#F7F7F7] text-[#111111] md:flex">
      <aside className="flex w-full shrink-0 flex-col bg-[#111111] text-white md:min-h-screen md:w-64">
        <div className="flex items-center gap-3 border-b border-white/10 px-6 py-6">
          <div className="flex h-10 w-10 items-center justify-center bg-white text-lg font-bold text-black">
            F
          </div>

          <div>
            <h1 className="text-lg font-semibold tracking-wide">
              FashionOS
            </h1>
            <p className="text-xs text-gray-400">Owner workspace</p>
          </div>
        </div>

        <div className="px-4 py-5">
          <p className="mb-3 px-3 text-[10px] font-semibold uppercase tracking-[0.2em] text-gray-500">
            Workspace
          </p>

          <nav className="flex gap-1 overflow-x-auto md:flex-col">
            {navigation.map((item) => (
              <NavLink
                key={item.name}
                to={item.path}
                end={item.path === "/backoffice"}
                className={({ isActive }) =>
                  `flex shrink-0 items-center gap-3 rounded-md px-3 py-3 text-sm transition ${
                    isActive
                      ? "bg-white font-semibold text-black"
                      : "text-gray-300 hover:bg-white/10 hover:text-white"
                  }`
                }
              >
                <span className="w-5 text-center text-base">
                  {item.icon}
                </span>
                {item.name}
              </NavLink>
            ))}
          </nav>
        </div>

        <div className="mt-auto hidden border-t border-white/10 p-5 md:block">
          <p className="text-sm font-medium">Sethi Fashion</p>
          <p className="mt-1 text-xs text-gray-400">
            Store management
          </p>

          <div className="mt-4 flex items-center gap-2 text-xs text-gray-400">
            <span className="h-2 w-2 rounded-full bg-green-500" />
            Workspace active
          </div>
        </div>
      </aside>

      <div className="min-w-0 flex-1">
        <header className="flex items-center justify-between gap-4 border-b border-gray-200 bg-white px-5 py-4 md:px-8">
          <div>
            <p className="text-xs text-gray-500">
              Sethi Fashion / Workspace
            </p>
            <h2 className="mt-1 text-xl font-semibold">
              FashionOS Backoffice
            </h2>
          </div>

          <div className="flex h-10 w-10 items-center justify-center rounded-full bg-[#111111] text-sm font-semibold text-white">
            AK
          </div>
        </header>

        <main className="min-w-0">
          <Outlet />
        </main>
      </div>
    </div>
  );
}

