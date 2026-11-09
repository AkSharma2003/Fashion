import { useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";
import { apiData, errorMessage } from "../lib/api/client";
import { getCustomerToken } from "../lib/auth/session";
import { useT } from "../lib/i18n";
import { formatINR } from "../lib/money";

type Card = { id: string; name: string; price_from_paise: number; image_url: string | null };
type Msg = { role: "user" | "assistant"; text: string; products?: Card[] };

/** AI-2 support chat. Tells customers they are talking to an AI; order status comes from the database. */
export default function ChatWidget() {
  const { t } = useT();
  const [open, setOpen] = useState(false);
  const [text, setText] = useState("");
  const [busy, setBusy] = useState(false);
  const [notice, setNotice] = useState("");
  const [session, setSession] = useState<string | null>(null);
  const [msgs, setMsgs] = useState<Msg[]>([]);
  const end = useRef<HTMLDivElement>(null);

  useEffect(() => end.current?.scrollIntoView({ behavior: "smooth" }), [msgs, open]);

  async function send(e: React.FormEvent) {
    e.preventDefault();
    const q = text.trim();
    if (!q || busy) return;
    setText("");
    setMsgs((m) => [...m, { role: "user", text: q }]);
    setBusy(true);
    try {
      const token = getCustomerToken();
      const r = await apiData<{ session_id: string; reply: string; notice: string; products: Card[] }>("/ai/chat", {
        method: "POST", headers: token ? { Authorization: `Bearer ${token}` } : undefined,
        body: JSON.stringify({ session_id: session, text: q, language: "english" }),
      });
      setSession(r.session_id);
      setNotice(r.notice);
      setMsgs((m) => [...m, { role: "assistant", text: r.reply, products: r.products }]);
    } catch (err) {
      setMsgs((m) => [...m, { role: "assistant", text: errorMessage(err, "Sorry, please try again or WhatsApp the shop.") }]);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="fixed bottom-4 right-4 z-[55] font-SecondryFont">
      {open && (
        <section className="mb-3 flex h-[min(520px,75vh)] w-[min(360px,calc(100vw-2rem))] flex-col overflow-hidden rounded-2xl border border-divider bg-white shadow-2xl">
          <header className="flex items-center justify-between bg-primary px-4 py-3 text-white">
            <span className="font-semibold">WearVerse · {t("Ask us")}</span>
            <button type="button" onClick={() => setOpen(false)} aria-label="Close chat" className="rounded p-1 hover:bg-white/10">✕</button>
          </header>
          <div className="flex-1 space-y-3 overflow-y-auto p-3 text-sm">
            <p className="rounded-lg bg-Alt_background p-2 text-xs text-text">{notice || "You are chatting with the WearVerse AI assistant. For anything urgent, call or WhatsApp the shop."}</p>
            {msgs.map((m, i) => (
              <div key={i} className={m.role === "user" ? "text-right" : ""}>
                <p className={`inline-block max-w-[85%] rounded-2xl px-3 py-2 text-left ${m.role === "user" ? "bg-primary text-white" : "bg-gray-100 text-main_text"}`}>{m.text}</p>
                {m.products && m.products.length > 0 && (
                  <div className="mt-2 flex gap-2 overflow-x-auto">
                    {m.products.slice(0, 3).map((p) => (
                      <Link key={p.id} to={`/product/${p.id}`} className="w-28 shrink-0 rounded-lg border border-divider p-1 text-xs">
                        {p.image_url && <img src={p.image_url} alt={p.name} className="h-24 w-full rounded object-cover" />}
                        <p className="mt-1 line-clamp-2">{p.name}</p><p className="font-semibold">{formatINR(p.price_from_paise)}</p>
                      </Link>
                    ))}
                  </div>
                )}
              </div>
            ))}
            {busy && <p className="text-xs text-text">…</p>}
            <div ref={end} />
          </div>
          <form onSubmit={send} className="flex gap-2 border-t border-divider p-2">
            <input value={text} onChange={(e) => setText(e.target.value)} placeholder={t("Type your question")} aria-label={t("Type your question")}
              className="min-h-11 min-w-0 flex-1 rounded-full border border-gray-300 px-3 outline-none focus:border-primary" />
            <button type="submit" disabled={busy} className="min-h-11 rounded-full bg-primary px-4 font-semibold text-white disabled:opacity-60">{t("Send")}</button>
          </form>
        </section>
      )}
      <button type="button" onClick={() => setOpen((o) => !o)} aria-label="Open chat"
        className="ml-auto flex h-14 w-14 items-center justify-center rounded-full bg-primary text-2xl text-white shadow-lg hover:opacity-90">💬</button>
    </div>
  );
}
