import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { ArrowRight, Heart, ShoppingCart } from "lucide-react";
import clothingFallback from "../assets/images/clothing-fallback.svg";
import {
  getWishlist,
  toggleWishlistProduct,
  wishlistUpdatedEventName,
} from "../lib/wishlist";
import { addToCart, cartUpdatedEventName, getCart } from "../lib/cart";
import type { StoreVariant } from "../lib/storeCards";

export type ClothingCardColor = {
  name: string;
  value: string;
};

export type ClothingCardProduct = {
  id?: string;
  name: string;
  description: string;
  price: number;
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

export default function Card({ product }: CardProps) {
  const navigate = useNavigate();
  const [note, setNote] = useState("");
  const soldOut = product.inStock === false;

  /** Single-size products go straight into the cart; others open the product page to choose a size. */
  const add = (goToCart: boolean) => {
    setNote("");
    const v = product.variant;
    if (!v) {
      if (product.id) navigate(`/product/${encodeURIComponent(product.id)}`);
      return;
    }
    const added = addToCart({ ...product, price: v.price_paise / 100 }, {
      variantId: v.id, size: v.size ?? undefined, color: v.color ?? undefined, sku: v.sku, stockQuantity: v.available });
    if (!added) { setNote("No more pieces in stock."); return; }
    if (goToCart) navigate("/cart");
  };
  const openProductDetails = () => {
    if (product.id) {
      navigate(`/product/${encodeURIComponent(product.id)}`);
    }
  };
  const [isWishlisted, setIsWishlisted] = useState(() =>
    getWishlist().some((item) => item.name === product.name)
  );
  const [inCart, setInCart] = useState(() =>
    getCart().some((item) => item.product.name === product.name)
  );

  useEffect(() => {
    const syncWishlist = () => {
      setIsWishlisted(getWishlist().some((item) => item.name === product.name));
    };
    const syncCart = () => {
      setInCart(getCart().some((item) => item.product.name === product.name));
    };

    window.addEventListener(wishlistUpdatedEventName(), syncWishlist);
    window.addEventListener("storage", syncWishlist);
    window.addEventListener(cartUpdatedEventName(), syncCart);
    window.addEventListener("storage", syncCart);
    return () => {
      window.removeEventListener(wishlistUpdatedEventName(), syncWishlist);
      window.removeEventListener("storage", syncWishlist);
      window.removeEventListener(cartUpdatedEventName(), syncCart);
      window.removeEventListener("storage", syncCart);
    };
  }, [product.name]);

  return (
    <article className="group flex h-full min-w-0 flex-col overflow-hidden rounded-xl border border-divider bg-surface text-main_text shadow-sm transition duration-300 hover:-translate-y-1 hover:shadow-xl sm:rounded-2xl">
      <div
        className={`relative aspect-[4/5] overflow-hidden bg-Alt_background ${product.id ? "cursor-pointer" : ""
          }`}
        onClick={openProductDetails}
      >
        <img
          onClick={openProductDetails}
          src={product.image}
          alt={product.imageAlt}
          loading="lazy"
          referrerPolicy="no-referrer"
          onError={(event) => {
            event.currentTarget.onerror = null;
            event.currentTarget.src = clothingFallback;
          }}
          className="h-full w-full object-contain object-center transition duration-500 sm:object-cover sm:object-top sm:group-hover:scale-105"
        />
        {product.tag && (
          <span className="absolute left-2 top-2 rounded-full bg-surface/95 px-2 py-1 text-[10px] font-semibold text-primary shadow-sm sm:left-3 sm:top-3 sm:px-3 sm:text-xs">
            {product.tag}
          </span>
        )}
        <button
          type="button"
          onClick={() => setIsWishlisted(toggleWishlistProduct(product))}
          aria-label={isWishlisted ? `Remove ${product.name} from wishlist` : `Add ${product.name} to wishlist`}
          aria-pressed={isWishlisted}
          className="absolute right-2 top-2 flex h-10 w-10 items-center justify-center rounded-full bg-surface/95 text-primary shadow-sm transition hover:scale-105 hover:bg-surface focus:outline-none focus:ring-2 focus:ring-primary focus:ring-offset-2 active:scale-95 sm:right-3 sm:top-3"
        >
          <Heart size={19} aria-hidden="true" fill={isWishlisted ? "currentColor" : "none"} />
        </button>
      </div>

      <div className="flex flex-1 flex-col p-2.5 sm:p-5">
        <div className="flex min-h-14 flex-col gap-0.5 sm:min-h-14 sm:flex-row sm:items-start sm:justify-between sm:gap-3">
          <h2 className="line-clamp-2 min-h-9 min-w-0 break-words font-primaryFont text-sm font-semibold leading-4 text-main_text sm:min-h-14 sm:flex-1 sm:text-xl sm:leading-snug">
            {product.id ? (
              <button
                type="button"
                onClick={openProductDetails}
                className="text-left hover:text-primary focus:outline-none focus:ring-2 focus:ring-primary"
              >
                {product.name}
              </button>
            ) : (
              product.name
            )}
          </h2>
          <p className="shrink-0 whitespace-nowrap text-xs font-semibold leading-4 text-primary sm:pt-1 sm:text-base sm:leading-5">
            ₹{product.price.toLocaleString("en-IN")}
          </p>
        </div>

        <p className="mt-0 h-5 line-clamp-1 break-words text-[11px] leading-5 text-text sm:mt-2 sm:h-10 sm:line-clamp-2 sm:text-sm sm:leading-5">
          {product.description}
        </p>

        <div className="mt-auto flex items-center justify-between gap-2 border-t border-divider pt-2 sm:mt-4 sm:gap-3 sm:pt-4">
          <span className="text-[9px] font-medium text-muted sm:text-xs">Colors</span>
          <div className="flex items-center gap-1 sm:gap-2">
            {product.colors.map((color) => (
              <span
                key={`${color.name}-${color.value}`}
                title={color.name}
                aria-label={color.name}
                className="h-3.5 w-3.5 shrink-0 rounded-full border border-divider ring-1 ring-surface sm:h-5 sm:w-5 sm:ring-2"
                style={{ backgroundColor: color.value }}
              />
            ))}
          </div>
        </div>

        <div className="mt-2 grid grid-cols-2 gap-1 sm:mt-3 sm:gap-2">
          <button
            type="button"
            onClick={() => add(false)}
            disabled={soldOut}
            aria-label={product.variant ? `Add ${product.name} to cart` : `Choose a size for ${product.name}`}
            className="inline-flex min-h-9 min-w-0 items-center justify-center gap-1 whitespace-nowrap rounded-lg border border-primary px-1 py-1.5 text-[10px] font-semibold text-primary transition hover:bg-primary/5 active:scale-[0.98] disabled:cursor-not-allowed disabled:opacity-50 sm:min-h-11 sm:gap-2 sm:px-2 sm:py-2 sm:text-sm"
          >
            <ShoppingCart size={14} aria-hidden="true" />
            <span className="sm:hidden">{soldOut ? "Sold out" : !product.variant ? "Size" : inCart ? "Add +" : "Add"}</span>
            <span className="hidden sm:inline">{soldOut ? "Sold out" : !product.variant ? "Choose size" : inCart ? "Add another" : "Add to cart"}</span>
          </button>
          <button
            type="button"
            onClick={() => add(true)}
            disabled={soldOut}
            className="inline-flex min-h-9 min-w-0 items-center justify-center gap-1 whitespace-nowrap rounded-lg bg-primary px-1 py-1.5 text-[10px] font-semibold text-surface transition hover:bg-primary-dark active:scale-[0.98] disabled:cursor-not-allowed disabled:opacity-50 sm:min-h-11 sm:gap-2 sm:px-2 sm:py-2 sm:text-sm"
          >
            <span className="sm:hidden">Buy</span>
            <span className="hidden sm:inline">Buy now</span>
            <ArrowRight size={14} aria-hidden="true" className="sm:h-4 sm:w-4" />
          </button>
        </div>
        {note && <p role="status" className="mt-2 text-xs text-red-700">{note}</p>}
      </div>
    </article>
  );
}

