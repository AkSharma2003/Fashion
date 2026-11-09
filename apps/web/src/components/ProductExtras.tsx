import { useState } from "react";
import { apiData, errorMessage, post } from "../lib/api/client";
import { getCustomerToken } from "../lib/auth/session";
import { useApi } from "../lib/hooks/useApi";
import { useT } from "../lib/i18n";
import { useSeo } from "../lib/seo";
import { toCardProduct, type StoreCard } from "../lib/storeCards";
import Card from "./Card";

type Rec = { product_id: string; reason: string; product: StoreCard };
type Detail = StoreCard & { images: (string | null)[]; variants: { available: number; price_paise: number }[] };

const REASONS: Record<string, string> = { similar: "Similar designs", complete_the_look: "Complete the look",
  also_bought: "Customers also bought", picked_for_you: "Picked for you", bestseller: "Bestsellers" };

/** AI-1 recommendations, AI-4 size help and product structured data for one product page. */
export default function ProductExtras({ productId }: { productId: string }) {
  const { t } = useT();
  const token = getCustomerToken();
  const recs = useApi(() => apiData<{ items: Rec[] }>(`/ai/recommendations?product_id=${productId}&limit=12`,
    token ? { headers: { Authorization: `Bearer ${token}` } } : {}), [productId]);
  const detail = useApi(() => apiData<Detail>(`/store/products/${productId}`), [productId]);
  const d = detail.data;
  useSeo({
    title: d ? `${d.name} | WearVerse` : "WearVerse",
    description: d?.description ?? (d ? `${d.name} from WearVerse` : undefined),
    image: d?.images?.[0] ?? undefined,
    jsonLd: d ? {
      "@context": "https://schema.org", "@type": "Product", name: d.name, category: d.category,
      description: d.description ?? undefined, image: d.images.filter(Boolean),
      offers: { "@type": "AggregateOffer", priceCurrency: "INR", lowPrice: d.price_from_paise / 100, highPrice: d.price_to_paise / 100,
        availability: d.in_stock ? "https://schema.org/InStock" : "https://schema.org/OutOfStock" },
    } : undefined,
  });

  const groups = new Map<string, Rec[]>();
  (recs.data?.items ?? []).forEach((r) => groups.set(r.reason, [...(groups.get(r.reason) ?? []), r]));

  return (
    <div className="mx-auto mt-12 max-w-7xl space-y-10 px-4 sm:px-6 lg:px-8">
      {d && d.sizes.length > 0 && !d.sizes.every((s) => /free/i.test(s)) && <SizeHelper productId={productId} />}
      {[...groups.entries()].map(([reason, items]) => (
        <section key={reason}>
          <h2 className="mb-4 font-primaryFont text-2xl font-semibold text-main_text">{t(REASONS[reason] ?? "You may also like")}</h2>
          <div className="grid grid-cols-1 gap-3 min-[360px]:grid-cols-2 sm:gap-6 lg:grid-cols-4">
            {items.slice(0, 4).map((r) => <Card key={r.product_id} product={toCardProduct(r.product)} />)}
          </div>
        </section>
      ))}
    </div>
  );
}

function SizeHelper({ productId }: { productId: string }) {
  const { t } = useT();
  const [open, setOpen] = useState(false);
  const [m, setM] = useState({ bust: "", waist: "", height: "", fit: "regular" });
  const [result, setResult] = useState<{ size: string | null; reason: string; in_stock?: boolean } | null>(null);
  const [error, setError] = useState("");

  async function ask() {
    try {
      setResult(await post("/ai/size", { product_id: productId, bust_cm: m.bust ? Number(m.bust) : null,
        waist_cm: m.waist ? Number(m.waist) : null, height_cm: m.height ? Number(m.height) : null, fit: m.fit }));
      setError("");
    } catch (err) {
      setError(errorMessage(err));
    }
  }

  const input = "min-h-11 w-full rounded-lg border border-gray-300 px-3 outline-none focus:border-primary";
  return (
    <section className="rounded-2xl border border-divider bg-white p-5">
      <button type="button" className="font-semibold text-primary underline" onClick={() => setOpen((o) => !o)}>📏 {t("Find my size")}</button>
      {open && (
        <div className="mt-4 grid gap-3 sm:grid-cols-5">
          <label className="text-sm">{t("Bust (cm)")}<input inputMode="decimal" className={input} value={m.bust} onChange={(e) => setM({ ...m, bust: e.target.value })} /></label>
          <label className="text-sm">{t("Waist (cm)")}<input inputMode="decimal" className={input} value={m.waist} onChange={(e) => setM({ ...m, waist: e.target.value })} /></label>
          <label className="text-sm">{t("Height (cm)")}<input inputMode="decimal" className={input} value={m.height} onChange={(e) => setM({ ...m, height: e.target.value })} /></label>
          <label className="text-sm">{t("Fit")}<select className={input} value={m.fit} onChange={(e) => setM({ ...m, fit: e.target.value })}>
            <option value="regular">{t("Regular")}</option><option value="tight">{t("Tight")}</option><option value="loose">{t("Loose")}</option></select></label>
          <button type="button" onClick={() => void ask()} className="min-h-11 self-end rounded-lg bg-primary px-4 font-semibold text-white">{t("Suggest size")}</button>
          {result && <p className="sm:col-span-5">{result.size ? <b className="text-lg">Size {result.size}. </b> : null}{result.reason}</p>}
          {error && <p className="text-sm text-sale sm:col-span-5">{error}</p>}
        </div>
      )}
    </section>
  );
}
