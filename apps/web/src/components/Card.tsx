import { useEffect, useState, type MouseEvent } from "react";
import { useNavigate } from "react-router-dom";
import { Heart, ShoppingBag } from "lucide-react";
import clothingFallback from "../assets/images/clothing-fallback.svg";
import { isWishlisted, toggleWishlistProduct, wishlistUpdatedEventName } from "../lib/wishlist";
import { addToCart } from "../lib/cart";
import type { StoreVariant } from "../lib/storeCards";
import { swatchBackground } from "../lib/colors";

export type ClothingCardColor = {
  name: string;
  value: string;
};

export type ClothingCardProduct = {
  id?: string;
  name: string;
  description: string;
  price: number;
  /** Printed price (₹); shown struck through with the % off when higher than the price. */
  mrp?: number | null;
  image: string;
  imageAlt: string;
  colors: ClothingCardColor[];
  tag?: string;
  /** false when nothing is left in stock (from the store API). */
  inStock?: boolean;
  /** Set when the product has a single size/colour, so it can go straight into the cart. */
  variant?: StoreVariant;
};

type CardProps = {
  product: ClothingCardProduct;
};

const rupees = (n: number) => `₹${Math.round(n).toLocaleString("en-IN")}`;

/** Compact product card: 3:4 photo, name, price with MRP and % off, wishlist heart, quick add on hover. */
export default function Card({ product }: CardProps) {
  const navigate = useNavigate();
  const [saved, setSaved] = useState(() => isWishlisted(product));
  const [note, setNote] = useState("");
  const soldOut = product.inStock === false;
  const off = product.mrp && product.mrp > product.price ? Math.round((1 - product.price / product.mrp) * 100) : 0;

  useEffect(() => {
    const sync = () => setSaved(isWishlisted(product));
    window.addEventListener(wishlistUpdatedEventName(), sync);
    window.addEventListener("storage", sync);
    return () => {
      window.removeEventListener(wishlistUpdatedEventName(), sync);
      window.removeEventListener("storage", sync);
    };
  }, [product]);

  const open = () => {
    if (product.id) navigate(`/product/${encodeURIComponent(product.id)}`);
  };

  const toggleSaved = (e: MouseEvent) => {
    e.stopPropagation();          // the heart must not also open the product page
    setSaved(toggleWishlistProduct(product));
  };

  /** Single-size products go straight into the cart; others open the product page to choose a size. */
  const add = (e: MouseEvent) => {
    e.stopPropagation();
    setNote("");
    const v = product.variant;
    if (!v) {
      open();
      return;
    }
    const added = addToCart({ ...product, price: v.price_paise / 100 }, {
      variantId: v.id, size: v.size ?? undefined, color: v.color ?? undefined, sku: v.sku, stockQuantity: v.available });
    setNote(added ? "Added to cart" : "No more pieces in stock");
  };

  const swatches = product.colors.slice(0, 4);
  const more = product.colors.length - swatches.length;

  return (
    <article className="group relative flex min-w-0 flex-col bg-surface text-main_text transition hover:shadow-[0_2px_16px_rgba(43,26,32,0.14)]">
      <div className={`relative aspect-[3/4] overflow-hidden bg-Alt_background ${product.id ? "cursor-pointer" : ""}`} onClick={open}>
        <img
          src={product.image}
          alt={product.imageAlt}
          loading="lazy"
          referrerPolicy="no-referrer"
          onError={(event) => {
            event.currentTarget.onerror = null;
            event.currentTarget.src = clothingFallback;
          }}
          className={`h-full w-full object-cover object-top transition duration-500 group-hover:scale-[1.04] ${soldOut ? "opacity-60" : ""}`}
        />
        {(product.tag || soldOut) && (
          <span className="absolute left-2 top-2 rounded-sm bg-surface/95 px-1.5 py-0.5 text-[10px] font-semibold uppercase tracking-wide text-main_text">
            {soldOut ? "Sold out" : product.tag}
          </span>
        )}
        <button
          type="button"
          onClick={toggleSaved}
          aria-label={saved ? `Remove ${product.name} from wishlist` : `Add ${product.name} to wishlist`}
          aria-pressed={saved}
          title={saved ? "Saved in wishlist" : "Save to wishlist"}
          className="absolute right-2 top-2 flex h-8 w-8 items-center justify-center rounded-full bg-surface/95 shadow-sm transition hover:scale-110 focus:outline-none focus:ring-2 focus:ring-primary"
        >
          <Heart size={16} aria-hidden="true" className={saved ? "text-sale" : "text-main_text"} fill={saved ? "currentColor" : "none"} />
        </button>
        {!soldOut && (
          <button
            type="button"
            onClick={add}
            className="absolute inset-x-0 bottom-0 hidden translate-y-full items-center justify-center gap-2 bg-surface/95 py-2.5 text-xs font-semibold uppercase tracking-wide text-main_text transition group-hover:translate-y-0 lg:flex"
          >
            <ShoppingBag size={14} aria-hidden="true" />
            {product.variant ? "Add to cart" : "Choose size"}
          </button>
        )}
      </div>

      <div className={`flex flex-1 flex-col px-2 pb-2.5 pt-2 ${product.id ? "cursor-pointer" : ""}`} onClick={open}>
        <h3 className="truncate text-[13px] font-semibold leading-5 sm:text-sm" title={product.name}>{product.name}</h3>
        <p className="truncate text-xs leading-5 text-muted">{product.description}</p>
        <p className="mt-1 flex flex-wrap items-baseline gap-x-1.5 text-[13px] sm:text-sm">
          <span className="font-semibold">{rupees(product.price)}</span>
          {off > 0 && (
            <>
              <span className="text-xs text-muted line-through">{rupees(product.mrp!)}</span>
              <span className="text-xs font-semibold text-[#E8762C]">({off}% OFF)</span>
            </>
          )}
        </p>
        {swatches.length > 0 && (
          <div className="mt-1.5 flex items-center gap-1" aria-label={`Colours: ${product.colors.map((c) => c.name).join(", ")}`}>
            {swatches.map((c) => (
              <span key={c.name} title={c.name} className="h-3 w-3 rounded-full border border-divider"
                style={{ background: swatchBackground(c.name) }} />
            ))}
            {more > 0 && <span className="text-[10px] text-muted">+{more}</span>}
          </div>
        )}
        {!soldOut && (
          <button type="button" onClick={add}
            className="mt-2 inline-flex min-h-8 items-center justify-center gap-1.5 rounded border border-divider text-xs font-semibold text-main_text active:bg-Alt_background lg:hidden">
            <ShoppingBag size={13} aria-hidden="true" />
            {product.variant ? "Add" : "Choose size"}
          </button>
        )}
        {note && <p role="status" className={`mt-1 text-[11px] ${note.startsWith("Added") ? "text-[#1E8E3E]" : "text-sale"}`}>{note}</p>}
      </div>
    </article>
  );
}
