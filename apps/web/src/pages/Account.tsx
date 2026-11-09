import { Link, useNavigate } from "react-router-dom";
import Footer from "../components/Footer";
import Header from "../components/Header";
import { Alert, Badge, Loading } from "../components/ui";
import { apiData } from "../lib/api/client";
import { getCustomerToken, setCustomerToken } from "../lib/auth/session";
import { useApi } from "../lib/hooks/useApi";
import { formatDate, formatINR } from "../lib/money";

type Order = { order_no: string; status: string; total_paise: number; created_at: string; ship_phone: string;
  items: { id: string; product_name: string; qty: number }[] };

export default function Account() {
  const navigate = useNavigate();
  const token = getCustomerToken();
  const orders = useApi(() => token
    ? apiData<Order[]>("/store/my/orders", { headers: { Authorization: `Bearer ${token}` } })
    : Promise.resolve([] as Order[]));

  return (
    <>
      <Header />
      <main className="min-h-screen bg-background px-4 py-10 text-main_text">
        <div className="mx-auto max-w-3xl space-y-5">
          <div className="flex items-center justify-between">
            <h1 className="font-primaryFont text-3xl font-semibold">My orders</h1>
            {token ? <button type="button" className="text-sm underline" onClick={() => { setCustomerToken(null); navigate("/"); }}>Log out</button>
              : <Link to="/login" className="text-sm underline">Log in</Link>}
          </div>
          {!token && <p>Log in to see your orders, or <Link className="underline" to="/track">track an order</Link> with its number and your mobile.</p>}
          {orders.loading && token && <Loading />}
          {orders.error && <Alert>{orders.error}</Alert>}
          {token && orders.data?.length === 0 && <p>No orders yet. <Link className="underline" to="/">Start shopping</Link></p>}
          <ul className="space-y-3">
            {(orders.data ?? []).map((o) => (
              <li key={o.order_no}>
                <Link to={`/track?order=${o.order_no}&phone=${o.ship_phone}`} className="block rounded-2xl border border-divider bg-white p-5 hover:shadow-sm">
                  <div className="flex items-center justify-between"><b>{o.order_no}</b><Badge>{o.status}</Badge></div>
                  <p className="mt-1 text-sm text-text">{formatDate(o.created_at)} · {formatINR(o.total_paise)} · {o.items.map((i) => `${i.qty}× ${i.product_name}`).join(", ")}</p>
                </Link>
              </li>
            ))}
          </ul>
        </div>
      </main>
      <Footer />
    </>
  );
}
