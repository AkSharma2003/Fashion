import { useRef, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { Camera, LogOut, MapPin, Package, Pencil, Plus, Trash2, User } from "lucide-react";
import Footer from "../components/Footer";
import Header from "../components/Header";
import Avatar from "../components/account/Avatar";
import AddressForm from "../components/account/AddressForm";
import { Alert, Badge, Loading } from "../components/ui";
import { errorMessage } from "../lib/api/client";
import { getCustomerToken } from "../lib/auth/session";
import { addressLines, customerApi, logoutCustomer, publishProfile, useCustomerProfile,
         type Address, type AddressInput, type CustomerProfile } from "../lib/customer";
import { useApi } from "../lib/hooks/useApi";
import { formatDate, formatINR } from "../lib/money";

type Order = { order_no: string; status: string; total_paise: number; created_at: string; ship_phone: string;
  items: { id: string; product_name: string; qty: number }[] };

const TABS = [
  { id: "profile", label: "My profile", icon: User },
  { id: "orders", label: "My orders", icon: Package },
  { id: "addresses", label: "Saved addresses", icon: MapPin },
] as const;
type Tab = (typeof TABS)[number]["id"];

/** Customer's account: profile with photo, orders, and an address book. */
export default function Account() {
  const [params, setParams] = useSearchParams();
  const tab = (TABS.some((t) => t.id === params.get("tab")) ? params.get("tab") : "profile") as Tab;
  const { profile } = useCustomerProfile();

  if (!getCustomerToken()) {
    return (
      <>
        <Header />
        <main className="min-h-screen bg-background px-4 py-16 text-center text-main_text">
          <h1 className="font-primaryFont text-3xl font-semibold">My account</h1>
          <p className="mt-3">Please <Link className="font-semibold text-primary underline" to="/login?next=/account">sign in</Link> to see
            your profile, orders and addresses.</p>
          <p className="mt-2 text-sm text-text">Or <Link className="underline" to="/track">track an order</Link> with its number and your mobile.</p>
        </main>
        <Footer />
      </>
    );
  }

  return (
    <>
      <Header />
      <main className="min-h-screen bg-background px-4 py-8 text-main_text sm:py-12">
        <div className="mx-auto grid max-w-5xl gap-6 md:grid-cols-[240px_1fr]">
          <aside className="space-y-3">
            <div className="flex items-center gap-3 rounded-2xl border border-divider bg-white p-4">
              <Avatar name={profile?.full_name} photo={profile?.profile_photo_url} size={48} />
              <div className="min-w-0">
                <p className="text-xs text-text">Hello,</p>
                <p className="truncate font-semibold">{profile?.full_name ?? "…"}</p>
              </div>
            </div>
            <nav className="overflow-hidden rounded-2xl border border-divider bg-white" aria-label="Account sections">
              {TABS.map(({ id, label, icon: Icon }) => (
                <button key={id} type="button" onClick={() => setParams({ tab: id })} aria-current={tab === id ? "page" : undefined}
                  className={`flex w-full items-center gap-3 border-b border-divider px-4 py-3 text-left text-sm last:border-b-0 ${
                    tab === id ? "bg-primary/10 font-semibold text-primary" : "hover:bg-gray-50"}`}>
                  <Icon size={17} /> {label}
                </button>
              ))}
              <button type="button" onClick={() => { logoutCustomer(); window.location.replace("/"); }}
                className="flex w-full items-center gap-3 px-4 py-3 text-left text-sm text-gray-600 hover:bg-gray-50">
                <LogOut size={17} /> Log out
              </button>
            </nav>
          </aside>

          <section className="min-w-0">
            {tab === "profile" && <ProfileTab profile={profile} />}
            {tab === "orders" && <OrdersTab />}
            {tab === "addresses" && <AddressesTab />}
          </section>
        </div>
      </main>
      <Footer />
    </>
  );
}

function Panel({ title, actions, children }: { title: string; actions?: React.ReactNode; children: React.ReactNode }) {
  return (
    <div className="rounded-2xl border border-divider bg-white p-5 sm:p-7">
      <div className="mb-5 flex flex-wrap items-center justify-between gap-3">
        <h1 className="sr-only">{title}</h1>
        {actions}
      </div>
      {children}
    </div>
  );
}

function ProfileTab({ profile }: { profile: CustomerProfile | null }) {
  const fileRef = useRef<HTMLInputElement>(null);
  const [editing, setEditing] = useState(false);
  const [name, setName] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");

  async function run(fn: () => Promise<CustomerProfile>, done: string) {
    setBusy(true); setError(""); setNotice("");
    try {
      publishProfile(await fn());
      setNotice(done);
      return true;
    } catch (e) {
      setError(errorMessage(e));
      return false;
    } finally {
      setBusy(false);
    }
  }

  async function uploadPhoto(file: File) {
    const body = new FormData();
    body.append("file", file);
    await run(() => customerApi<CustomerProfile>("/store/me/photo", { method: "POST", body }), "Photo updated.");
  }

  if (!profile) return <Panel title="My profile"><Loading /></Panel>;

  const row = "grid gap-1 border-b border-divider py-3 last:border-b-0 sm:grid-cols-[160px_1fr]";
  return (
    <Panel title="My profile">
      <div className="mb-6 flex flex-wrap items-center gap-5">
        <Avatar name={profile.full_name} photo={profile.profile_photo_url} size={96} />
        <div className="flex flex-wrap gap-2">
          <input ref={fileRef} type="file" accept="image/jpeg,image/png,image/webp" className="hidden"
            onChange={(e) => { const f = e.target.files?.[0]; if (f) void uploadPhoto(f); e.target.value = ""; }} />
          <button type="button" disabled={busy} onClick={() => fileRef.current?.click()}
            className="inline-flex min-h-10 items-center gap-2 rounded-lg border border-primary px-4 text-sm font-semibold text-primary hover:bg-primary/5 disabled:opacity-60">
            <Camera size={16} /> {profile.profile_photo_url ? "Change photo" : "Add photo"}
          </button>
          {profile.profile_photo_url && (
            <button type="button" disabled={busy}
              onClick={() => void run(() => customerApi<CustomerProfile>("/store/me/photo", { method: "DELETE" }), "Photo removed.")}
              className="min-h-10 rounded-lg px-3 text-sm text-gray-600 hover:underline disabled:opacity-60">Remove</button>
          )}
        </div>
        <p className="w-full text-xs text-text">JPEG, PNG or WebP, up to 5 MB.</p>
      </div>

      {notice && <Alert tone="good">{notice}</Alert>}
      <Alert>{error}</Alert>

      <dl>
        <div className={row}>
          <dt className="text-sm text-text">Full name</dt>
          <dd>
            {editing ? (
              <form className="flex flex-wrap gap-2" onSubmit={async (e) => {
                e.preventDefault();
                if (await run(() => customerApi<CustomerProfile>("/store/me", { method: "PATCH", body: JSON.stringify({ full_name: name.trim() }) }), "Name saved.")) setEditing(false);
              }}>
                <input autoFocus required minLength={2} maxLength={100} value={name} onChange={(e) => setName(e.target.value)}
                  className="min-h-10 flex-1 rounded-lg border border-gray-300 px-3 outline-none focus:border-primary focus:ring-2 focus:ring-primary/20" />
                <button type="submit" disabled={busy} className="min-h-10 rounded-lg bg-primary px-4 text-sm font-semibold text-white disabled:opacity-60">Save</button>
                <button type="button" onClick={() => setEditing(false)} className="min-h-10 px-3 text-sm text-gray-600">Cancel</button>
              </form>
            ) : (
              <span className="flex items-center gap-3 font-medium">{profile.full_name}
                <button type="button" onClick={() => { setName(profile.full_name); setEditing(true); }}
                  className="inline-flex items-center gap-1 text-sm font-medium text-primary hover:underline"><Pencil size={14} /> Edit</button>
              </span>
            )}
          </dd>
        </div>
        <div className={row}><dt className="text-sm text-text">Email</dt><dd>{profile.email ?? "—"}</dd></div>
        <div className={row}><dt className="text-sm text-text">Mobile number</dt><dd>+91 {profile.phone_number}</dd></div>
        <div className={row}><dt className="text-sm text-text">Account</dt>
          <dd>{profile.is_verified ? <Badge tone="good">Verified</Badge> : <Badge>Not verified</Badge>}
            {profile.member_since && <span className="ml-2 text-sm text-text">Member since {formatDate(profile.member_since)}</span>}</dd></div>
      </dl>
      <p className="mt-4 text-xs text-text">To change your e-mail or mobile number, please contact the shop.</p>
    </Panel>
  );
}

function OrdersTab() {
  const orders = useApi(() => customerApi<Order[]>("/store/my/orders"));
  return (
    <Panel title="My orders">
      {orders.loading && !orders.data && <Loading />}
      <Alert>{orders.error}</Alert>
      {orders.data?.length === 0 && <p>No orders yet. <Link className="font-semibold text-primary underline" to="/">Start shopping</Link></p>}
      <ul className="space-y-3">
        {(orders.data ?? []).map((o) => (
          <li key={o.order_no}>
            <Link to={`/track?order=${o.order_no}&phone=${o.ship_phone}`} className="block rounded-xl border border-divider p-4 hover:shadow-sm">
              <div className="flex items-center justify-between"><b>{o.order_no}</b><Badge>{o.status.replace(/_/g, " ").toLowerCase()}</Badge></div>
              <p className="mt-1 text-sm text-text">{formatDate(o.created_at)} · {formatINR(o.total_paise)} · {o.items.map((i) => `${i.qty}× ${i.product_name}`).join(", ")}</p>
            </Link>
          </li>
        ))}
      </ul>
    </Panel>
  );
}

function AddressesTab() {
  const list = useApi(() => customerApi<Address[]>("/store/me/addresses"));
  const [editing, setEditing] = useState<Address | "new" | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  async function act(fn: () => Promise<unknown>) {
    setBusy(true); setError("");
    try {
      await fn();
      setEditing(null);
      await list.reload();
    } catch (e) {
      setError(errorMessage(e));
    } finally {
      setBusy(false);
    }
  }

  const save = (a: AddressInput) => act(() => editing && editing !== "new"
    ? customerApi(`/store/me/addresses/${editing.id}`, { method: "PATCH", body: JSON.stringify(a) })
    : customerApi("/store/me/addresses", { method: "POST", body: JSON.stringify(a) }));

  return (
    <Panel title="Saved addresses" actions={!editing && (
      <button type="button" onClick={() => { setError(""); setEditing("new"); }}
        className="inline-flex min-h-10 items-center gap-2 rounded-lg bg-primary px-4 text-sm font-semibold text-white hover:bg-primary-dark">
        <Plus size={16} /> Add a new address
      </button>)}>
      {editing ? (
        <div className="rounded-xl border border-primary/30 bg-primary/5 p-4 sm:p-5">
          <h2 className="mb-4 font-semibold">{editing === "new" ? "Add a new address" : "Edit address"}</h2>
          <AddressForm key={editing === "new" ? "new" : editing.id} initial={editing === "new" ? undefined : editing}
            onSubmit={save} onCancel={() => setEditing(null)} busy={busy} error={error} />
        </div>
      ) : (
        <>
          {list.loading && !list.data && <Loading />}
          <Alert>{list.error || error}</Alert>
          {list.data?.length === 0 && (
            <p className="rounded-xl border border-dashed border-divider p-8 text-center text-text">
              No saved addresses yet. Add one to check out faster.
            </p>
          )}
          <ul className="grid gap-4 sm:grid-cols-2">
            {(list.data ?? []).map((a) => (
              <li key={a.id} className={`flex flex-col rounded-xl border p-4 ${a.is_default ? "border-primary" : "border-divider"}`}>
                <div className="mb-2 flex flex-wrap items-center gap-2">
                  <Badge>{a.kind === "HOME" ? "Home" : a.kind === "WORK" ? "Work" : "Other"}</Badge>
                  {a.is_default && <Badge tone="good">Default</Badge>}
                </div>
                <p className="font-semibold">{a.name}</p>
                <p className="mt-1 text-sm leading-6 text-text">{addressLines(a)}</p>
                <p className="mt-1 text-sm text-text">Phone: {a.phone}</p>
                <div className="mt-auto flex flex-wrap gap-x-4 gap-y-1 pt-3 text-sm font-medium">
                  <button type="button" disabled={busy} onClick={() => { setError(""); setEditing(a); }} className="inline-flex items-center gap-1 text-primary hover:underline"><Pencil size={14} /> Edit</button>
                  <button type="button" disabled={busy} onClick={() => { if (window.confirm("Remove this address?")) void act(() => customerApi(`/store/me/addresses/${a.id}`, { method: "DELETE" })); }}
                    className="inline-flex items-center gap-1 text-gray-600 hover:underline"><Trash2 size={14} /> Remove</button>
                  {!a.is_default && (
                    <button type="button" disabled={busy} onClick={() => void act(() => customerApi(`/store/me/addresses/${a.id}/default`, { method: "POST" }))}
                      className="text-gray-600 hover:underline">Set as default</button>
                  )}
                </div>
              </li>
            ))}
          </ul>
        </>
      )}
    </Panel>
  );
}
