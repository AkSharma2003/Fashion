import { useNavigate } from "react-router-dom";
import { ImagePlay } from "lucide-react";
import { useState } from "react";

const navigation = [
  { name: "Dashboard", icon: "◫" },
  { name: "Orders", icon: "▤" },
  { name: "Products", icon: "◇" },
  { name: "Inventory", icon: "▦" },
  { name: "Customers", icon: "♙" },
  { name: "Khata", icon: "₹" },
  { name: "Fall-Pico", icon: "✂" },
  { name: "Reports", icon: "▥" },
  { name: "Settings", icon: "⚙" },
];

const stats = [
  {
    label: "Today's Sales",
    value: "₹24,850",
    note: "Demo data",
    icon: "↗",
  },
  {
    label: "Collections",
    value: "₹12,400",
    note: "Demo data",
    icon: "₹",
  },
  {
    label: "Khata Outstanding",
    value: "₹1,48,500",
    note: "Amount to collect",
    icon: "◷",
  },
  {
    label: "Total Orders",
    value: "38",
    note: "Today's orders",
    icon: "▤",
  },
];

const orders = [
  {
    id: "#FS-1024",
    customer: "Priya Sharma",
    item: "Banarasi Saree",
    amount: "₹4,500",
    status: "Delivered",
  },
  {
    id: "#FS-1023",
    customer: "Neha Patel",
    item: "Ladies Suit",
    amount: "₹2,200",
    status: "Processing",
  },
  {
    id: "#FS-1022",
    customer: "Aarav Shah",
    item: "Kids Wear",
    amount: "₹1,250",
    status: "Pending",
  },
  {
    id: "#FS-1021",
    customer: "Kavita Sethi",
    item: "Silk Saree",
    amount: "₹6,800",
    status: "Delivered",
  },
];

const stockAlerts = [
  { name: "Banarasi Saree", detail: "SKU: SAR-104", stock: 2 },
  { name: "Cotton Suit", detail: "SKU: SUIT-028", stock: 4 },
  { name: "Kids Party Wear", detail: "SKU: KID-016", stock: 3 },
];

export default function BackofficeDashboard() {
  const navigate = useNavigate();
  const [activePage, setActivePage] = useState("Dashboard");

  return (
    <div className="min-h-screen bg-[#F7F7F7] text-[#111111] md:flex">
      {/* Main content */}
      <main className="min-w-0 flex-1">
        <header className="flex flex-wrap items-center justify-between gap-4 border-b border-gray-200 bg-white px-5 py-4 md:px-8">
          <div>
            <p className="text-xs text-gray-500">Sethi Fashion / Workspace</p>
            <h2 className="mt-1 text-xl font-semibold">{activePage}</h2>
          </div>

          <div className="flex items-center gap-3">
            <span className="hidden text-xs text-gray-500 sm:block">
              Demo dashboard
            </span>
            <div className="flex h-10 w-10 items-center justify-center rounded-full bg-[#111111] text-sm font-semibold text-white">
              AK
            </div>
          </div>
        </header>

        <div className="space-y-7 p-5 md:p-8">
          {/* Welcome */}
          <section className="flex flex-wrap items-end justify-between gap-4">
            <div>
              <p className="text-sm text-gray-500">Friday, October 9, 2026</p>
              <h1 className="mt-2 text-2xl font-semibold tracking-tight md:text-3xl">
                Good morning, Ankit
              </h1>
              <p className="mt-2 text-sm text-gray-500">
                Here is what's happening with your store today.
              </p>
            </div>

            <button className="rounded-md bg-[#111111] px-5 py-3 text-sm font-medium text-white transition hover:bg-gray-800">
              + Create order
            </button>
          </section>

          {/* Statistics */}
          <section className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
            {stats.map((stat) => (
              <article
                key={stat.label}
                className="rounded-lg border border-gray-200 bg-white p-5"
              >
                <div className="flex items-start justify-between gap-3">
                  <p className="text-sm text-gray-500">{stat.label}</p>
                  <span className="flex h-9 w-9 items-center justify-center rounded-md bg-[#F2F2F2] text-lg">
                    {stat.icon}
                  </span>
                </div>
                <p className="mt-5 text-2xl font-semibold tracking-tight">
                  {stat.value}
                </p>
                <p className="mt-2 text-xs text-gray-500">{stat.note}</p>
              </article>
            ))}
          </section>

          {/* Orders and stock */}
          <section className="grid grid-cols-1 gap-6 xl:grid-cols-3">
            <div className="overflow-hidden rounded-lg border border-gray-200 bg-white xl:col-span-2">
              <div className="flex items-center justify-between border-b border-gray-100 px-5 py-5">
                <div>
                  <h3 className="font-semibold">Recent orders</h3>
                  <p className="mt-1 text-xs text-gray-500">
                    Latest store activity · Demo data
                  </p>
                </div>
                <button
                  onClick={() => setActivePage("Orders")}
                  className="text-sm font-medium underline underline-offset-4"
                >
                  View all
                </button>
              </div>

              <div className="overflow-x-auto">
                <table className="w-full min-w-[620px] text-left text-sm">
                  <thead className="bg-[#F7F7F7] text-xs text-gray-500">
                    <tr>
                      <th className="px-5 py-3 font-medium">Order</th>
                      <th className="px-5 py-3 font-medium">Customer</th>
                      <th className="px-5 py-3 font-medium">Item</th>
                      <th className="px-5 py-3 font-medium">Amount</th>
                      <th className="px-5 py-3 font-medium">Status</th>
                    </tr>
                  </thead>
                  <tbody>
                    {orders.map((order) => (
                      <tr
                        key={order.id}
                        className="border-t border-gray-100"
                      >
                        <td className="px-5 py-4 font-medium">{order.id}</td>
                        <td className="px-5 py-4">{order.customer}</td>
                        <td className="px-5 py-4 text-gray-600">
                          {order.item}
                        </td>
                        <td className="px-5 py-4 font-medium">
                          {order.amount}
                        </td>
                        <td className="px-5 py-4">
                          <span
                            className={`inline-block rounded-full px-2.5 py-1 text-xs ${order.status === "Delivered"
                                ? "bg-green-50 text-green-700"
                                : order.status === "Processing"
                                  ? "bg-blue-50 text-blue-700"
                                  : "bg-amber-50 text-amber-700"
                              }`}
                          >
                            {order.status}
                          </span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>

            {/* Low stock */}
            <div className="rounded-lg border border-gray-200 bg-white">
              <div className="border-b border-gray-100 px-5 py-5">
                <div className="flex items-center justify-between">
                  <h3 className="font-semibold">Low stock alerts</h3>
                  <span className="rounded-full bg-red-50 px-2.5 py-1 text-xs font-medium text-red-700">
                    {stockAlerts.length} items
                  </span>
                </div>
                <p className="mt-1 text-xs text-gray-500">
                  Products that need attention
                </p>
              </div>

              <div className="divide-y divide-gray-100 px-5">
                {stockAlerts.map((item) => (
                  <div
                    key={item.name}
                    className="flex items-center justify-between gap-3 py-4"
                  >
                    <div>
                      <p className="text-sm font-medium">{item.name}</p>
                      <p className="mt-1 text-xs text-gray-500">
                        {item.detail}
                      </p>
                    </div>
                    <div className="shrink-0 text-right">
                      <p className="font-semibold">{item.stock}</p>
                      <p className="text-xs text-gray-500">left</p>
                    </div>
                  </div>
                ))}
              </div>

              <div className="px-5 pb-5 pt-3">
                <button
                  onClick={() => setActivePage("Inventory")}
                  className="w-full rounded-md border border-gray-300 px-4 py-3 text-sm font-medium transition hover:bg-gray-50"
                >
                  Manage inventory
                </button>
              </div>
            </div>
          </section>

          {/* Quick actions */}
          <section>
            <h3 className="font-semibold">Quick actions</h3>
            <div className="mt-4 grid grid-cols-1 gap-3 sm:grid-cols-2 xl:grid-cols-4">
              {[
                {
                  title: "Manage Khata",
                  desc: "Customer balances and payments",
                  page: "Khata",
                },
                {
                  title: "Add product",
                  desc: "Update your product catalogue",
                  page: "Products",
                },
                {
                  title: "View customers",
                  desc: "Customer details and history",
                  page: "Customers",
                },
                {
                  title: "Sales reports",
                  desc: "Review your store performance",
                  page: "Reports",
                },
              ].map((action) => (
                <button
                  key={action.title}
                  onClick={() => setActivePage(action.page)}
                  className="rounded-lg border border-gray-200 bg-white p-5 text-left transition hover:border-[#111111]"
                >
                  <p className="font-medium">{action.title} ↗</p>
                  <p className="mt-2 text-sm text-gray-500">{action.desc}</p>
                </button>
              ))}
            </div>
          </section>

          <footer className="border-t border-gray-200 pt-5 text-xs text-gray-500">
            FashionOS · Owner workspace · Sample dashboard data
          </footer>
        </div>
      </main>
    </div>
  );
}