import { useEffect, useRef, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import Card from "../components/Card";
import Footer from "../components/Footer";
import Header from "../components/Header";
import { api, apiData, errorMessage } from "../lib/api/client";
import { useT } from "../lib/i18n";
import { useSeo } from "../lib/seo";
import { toCardProduct, type StoreCard } from "../lib/storeCards";

type Filters = { colours: string[]; words: string[]; max_price_paise: number | null; min_price_paise: number | null; size: string | null };

/** AI-3 smart search ("lal silk saree under 5000") and AI-7 photo search, with keyword fallback built in. */
export default function SearchResults() {
  const { t } = useT();
  const [params] = useSearchParams();
  const query = (params.get("q") ?? "").trim();
  const [items, setItems] = useState<StoreCard[]>([]);
  const [filters, setFilters] = useState<Filters | null>(null);
  const [note, setNote] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const fileRef = useRef<HTMLInputElement>(null);
  useSeo({ title: query ? `${query} | WearVerse` : "Search | WearVerse", description: "Search sarees, suits and kidswear at WearVerse." });

  useEffect(() => {
    if (!query) return;
    setLoading(true);
    setNote("");
    apiData<{ items: StoreCard[]; filters: Filters }>(`/ai/search?q=${encodeURIComponent(query)}`)
      .then((r) => { setItems(r.items); setFilters(r.filters); setError(""); })
      .catch((err) => setError(errorMessage(err)))
      .finally(() => setLoading(false));
  }, [query]);

  async function photoSearch(file: File) {
    setLoading(true);
    const form = new FormData();
    form.append("file", file);
    try {
      const r = await api<{ data: { items: StoreCard[]; note: string } }>("/ai/visual-search", { method: "POST", body: form });
      setItems(r.data.items);
      setFilters(null);
      setNote(r.data.note);
      setError("");
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setLoading(false);
    }
  }

  const chips = filters ? [...filters.colours, ...filters.words,
    filters.max_price_paise ? `≤ ₹${filters.max_price_paise / 100}` : "", filters.min_price_paise ? `≥ ₹${filters.min_price_paise / 100}` : "",
    filters.size ?? ""].filter(Boolean) : [];

  return (
    <>
      <Header />
      <main className="min-h-screen bg-linear-to-br from-background to-Alt_background px-4 py-10 sm:px-6 sm:py-14 lg:px-8">
        <section className="mx-auto max-w-7xl">
          <div className="mb-8 text-center sm:mb-10">
            <h1 className="font-primaryFont text-3xl font-semibold text-main_text sm:text-4xl">
              {query ? `“${query}”` : t("Search")}
            </h1>
            {chips.length > 0 && (
              <div className="mt-3 flex flex-wrap justify-center gap-2">
                {chips.map((c) => <span key={c} className="rounded-full bg-white px-3 py-1 text-xs text-primary ring-1 ring-divider">{c}</span>)}
              </div>
            )}
            <p className="mt-3 text-sm text-text">{loading ? "…" : `${items.length} ${t("results found")}`} {note && `· ${note}`}</p>
            <button type="button" onClick={() => fileRef.current?.click()}
              className="mt-4 inline-flex min-h-11 items-center gap-2 rounded-lg border border-primary px-4 font-semibold text-primary">📷 {t("Search by photo")}</button>
            <input ref={fileRef} type="file" accept="image/*" capture="environment" className="hidden"
              onChange={(e) => { const f = e.target.files?.[0]; if (f) void photoSearch(f); e.target.value = ""; }} />
          </div>
          {error && <p className="mb-4 text-center text-sm text-sale">{error}</p>}
          {items.length > 0 ? (
            <div className="grid grid-cols-1 gap-3 min-[360px]:grid-cols-2 sm:gap-6 lg:grid-cols-4">
              {items.map((c) => <Card key={c.id} product={toCardProduct(c)} />)}
            </div>
          ) : !loading && (
            <div className="mx-auto max-w-lg rounded-2xl border border-divider bg-white px-6 py-12 text-center shadow-sm">
              <p className="font-primaryFont text-xl font-semibold text-main_text">{t("No matching designs found")}</p>
              <p className="mt-2 text-sm text-text">We noted your search so the shop can stock it. Try "red silk saree under 5000" or a photo.</p>
              <Link to="/" className="mt-6 inline-flex min-h-11 items-center justify-center rounded-lg bg-primary px-5 py-2.5 font-semibold text-white">Explore all designs</Link>
            </div>
          )}
        </section>
      </main>
      <Footer />
    </>
  );
}
