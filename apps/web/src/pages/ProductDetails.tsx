
import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { ArrowLeft, Heart, ShoppingCart, Minus, Plus } from "lucide-react";
import { isWishlisted, toggleWishlistProduct, wishlistUpdatedEventName } from "../lib/wishlist";
import { swatchBackground } from "../lib/colors";
import Header from "../components/Header";
import Footer from "../components/Footer";
import ProductExtras from "../components/ProductExtras";
import clothingFallback from "../assets/images/clothing-fallback.svg";
import { addToCart } from "../lib/cart";
import { apiData } from "../lib/api/client";
import type { StoreCard, StoreVariant } from "../lib/storeCards";
import type { ClothingCardProduct } from "../components/Card";

/** Variant as this page uses it (from the public store API). */
type ProductVariant = {
    id: string; size: string; color: string; sku: string;
    selling_price_paise: number; stock_quantity: number; is_active: boolean;
};

type StoreProductDetail = StoreCard & { images: (string | null)[]; variants: StoreVariant[] };

export default function ProductDetails() {
    const { productId } = useParams<{ productId: string }>();
    const navigate = useNavigate();

    const [product, setProduct] = useState<ClothingCardProduct | null>(null);
    const [images, setImages] = useState<string[]>([]);
    const [selectedImage, setSelectedImage] = useState(clothingFallback);
    const [variants, setVariants] = useState<ProductVariant[]>([]);
    const [selectedVariantId, setSelectedVariantId] = useState("");
    const [quantity, setQuantity] = useState(1);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState("");
    const [variantError, setVariantError] = useState("");
    const [cartMessage, setCartMessage] = useState("");
    const [saved, setSaved] = useState(false);
    useEffect(() => {
        const sync = () => setSaved(product ? isWishlisted(product) : false);
        sync();
        window.addEventListener(wishlistUpdatedEventName(), sync);
        return () => window.removeEventListener(wishlistUpdatedEventName(), sync);
    }, [product]);

    const selectedVariant = variants.find(
        (variant) => variant.id === selectedVariantId,
    );

    useEffect(() => {
        let cancelled = false;

        async function loadProduct() {
            try {
                setLoading(true);
                setError("");
                setVariantError("");
                setCartMessage("");

                if (!productId) {
                    throw new Error("Product ID is missing.");
                }

                const detail = await apiData<StoreProductDetail>(
                    `/store/products/${encodeURIComponent(productId)}`,
                );
                const selectedProduct = {
                    id: detail.id, name: detail.name, description: detail.description,
                    category: detail.category, selling_price_paise: detail.price_from_paise,
                };
                const imageUrls = detail.images.filter((url): url is string => Boolean(url));
                const productVariants: ProductVariant[] = detail.variants.map((v) => ({
                    id: v.id, size: v.size ?? "Free", color: v.color ?? "", sku: v.sku,
                    selling_price_paise: v.price_paise, stock_quantity: v.available, is_active: true,
                }));

                const primaryImage = imageUrls[0] ?? clothingFallback;

                const mappedProduct: ClothingCardProduct = {
                    id: selectedProduct.id,
                    name: selectedProduct.name,
                    description: selectedProduct.description ?? selectedProduct.category,
                    price: selectedProduct.selling_price_paise / 100,
                    mrp: detail.mrp_paise ? detail.mrp_paise / 100 : null,
                    image: primaryImage,
                    imageAlt: selectedProduct.name,
                    colors: detail.colors.map((name) => ({ name, value: name.toLowerCase() })),
                    inStock: detail.in_stock,
                    variant: detail.single_variant ?? undefined,
                    tag: selectedProduct.category,
                };

                if (!cancelled) {
                    setProduct(mappedProduct);
                    setImages(imageUrls.length > 0 ? imageUrls : [clothingFallback]);
                    setSelectedImage(primaryImage);
                    setVariants(productVariants);
                    setSelectedVariantId(
                        productVariants.find((variant) => variant.stock_quantity > 0)?.id ??
                        productVariants[0]?.id ??
                        "",
                    );
                    setQuantity(1);
                }
            } catch (err) {
                if (!cancelled) {
                    setError(
                        err instanceof Error ? err.message : "Unable to load product.",
                    );
                }
            } finally {
                if (!cancelled) setLoading(false);
            }
        }

        void loadProduct();

        return () => {
            cancelled = true;
        };
    }, [productId]);

    const colours = [...new Set(variants.map((v) => v.color).filter(Boolean))];
    const sizes = [...new Set(variants.filter((v) => !selectedVariant || v.color === selectedVariant.color).map((v) => v.size))];
    const mrp = product?.mrp ?? 0;

    /** Pick a colour: keep the same size if it exists in that colour, else its first size in stock. */
    function chooseColour(colour: string) {
        const same = variants.find((v) => v.color === colour && v.size === selectedVariant?.size && v.stock_quantity > 0);
        const first = variants.find((v) => v.color === colour && v.stock_quantity > 0) ?? variants.find((v) => v.color === colour);
        const pick = same ?? first;
        if (pick) selectVariant(pick.id);
        // One photo per colour, in the same order as the colours: show that colour's photo.
        const byName = images.find((u) => decodeURIComponent(u).toLowerCase().includes(colour.toLowerCase().replace(/\s+/g, "_")));
        const byOrder = images.length === colours.length ? images[colours.indexOf(colour)] : undefined;
        if (byName ?? byOrder) setSelectedImage((byName ?? byOrder)!);
    }

    function selectVariant(variantId: string) {
        setSelectedVariantId(variantId);
        setQuantity(1);
        setCartMessage("");
    }

    function handleAddToCart(goToCart = false) {
        if (!product) return;

        setCartMessage("");

        if (variants.length > 0 && !selectedVariant) {
            setCartMessage("Please select a size and colour.");
            return;
        }

        if (selectedVariant && selectedVariant.stock_quantity <= 0) {
            setCartMessage("This size is out of stock right now.");
            return;
        }

        if (
            selectedVariant &&
            quantity > selectedVariant.stock_quantity
        ) {
            setCartMessage(`Only ${selectedVariant.stock_quantity} left in stock.`);
            return;
        }

        const productForCart: ClothingCardProduct = {
            ...product,
            price: selectedVariant
                ? selectedVariant.selling_price_paise / 100
                : product.price,
            colors: selectedVariant
                ? [{ name: selectedVariant.color, value: selectedVariant.color }]
                : product.colors,
        };

        const added = addToCart(
            productForCart,
            selectedVariant
                ? {
                    variantId: selectedVariant.id,
                    size: selectedVariant.size,
                    color: selectedVariant.color,
                    sku: selectedVariant.sku,
                    stockQuantity: selectedVariant.stock_quantity,
                    quantity,
                }
                : { quantity },
        );

        if (!added) {
            setCartMessage("That many pieces are not in stock.");
            return;
        }

        if (goToCart) {
            navigate("/cart");
            return;
        }

        setCartMessage("Added to your cart.");
    }

    const price = selectedVariant
        ? selectedVariant.selling_price_paise / 100
        : product?.price ?? 0;

    const stock = selectedVariant?.stock_quantity;
    const outOfStock = variants.length > 0 && stock === 0;

    return (
        <>
            <Header />

            <main className="min-h-screen bg-linear-to-br from-background to-Alt_background px-4 py-8 sm:px-6 sm:py-12">
                <div className="mx-auto max-w-6xl">
                    <button
                        type="button"
                        onClick={() => navigate(-1)}
                        className="mb-6 inline-flex items-center gap-2 rounded-lg px-3 py-2 text-sm font-medium text-main_text transition hover:bg-surface"
                    >
                        <ArrowLeft size={18} />
                        Back to shopping
                    </button>

                    {loading && (
                        <p className="py-16 text-center text-text">
                            Loading product details...
                        </p>
                    )}

                    {!loading && error && (
                        <div className="py-16 text-center">
                            <p className="text-red-600">{error}</p>
                            <button
                                type="button"
                                onClick={() => navigate("/")}
                                className="mt-4 rounded-lg bg-primary px-5 py-3 text-sm font-semibold text-surface"
                            >
                                Back to home
                            </button>
                        </div>
                    )}

                    {!loading && !error && product && (
                        <section className="grid gap-6 md:grid-cols-[minmax(0,1fr)_minmax(0,1fr)] md:gap-10">
                            {/* Photos: thumbnails beside a 3:4 main photo */}
                            <div className="flex gap-3 md:sticky md:top-24 md:self-start">
                                {images.length > 1 && (
                                    <div className="hidden w-16 shrink-0 flex-col gap-2 sm:flex" aria-label="Product images">
                                        {images.map((image, index) => (
                                            <button
                                                key={`${image}-${index}`}
                                                type="button"
                                                onClick={() => setSelectedImage(image)}
                                                aria-label={`View product image ${index + 1}`}
                                                aria-pressed={selectedImage === image}
                                                className={`aspect-[3/4] w-16 overflow-hidden border-2 transition ${selectedImage === image ? "border-primary" : "border-transparent hover:border-divider"}`}
                                            >
                                                <img src={image} alt="" className="h-full w-full object-cover object-top" />
                                            </button>
                                        ))}
                                    </div>
                                )}
                                <div className="min-w-0 flex-1">
                                    <div className="mx-auto aspect-[3/4] max-h-[620px] overflow-hidden bg-Alt_background">
                                        <img
                                            key={selectedImage}
                                            src={selectedImage}
                                            alt={product.imageAlt}
                                            onError={(event) => {
                                                event.currentTarget.onerror = null;
                                                event.currentTarget.src = clothingFallback;
                                            }}
                                            className="h-full w-full object-cover object-top"
                                        />
                                    </div>
                                    {images.length > 1 && (
                                        <div className="mt-2 flex gap-2 overflow-x-auto sm:hidden" aria-label="Product images">
                                            {images.map((image, index) => (
                                                <button key={`m-${image}-${index}`} type="button" onClick={() => setSelectedImage(image)}
                                                    aria-label={`View product image ${index + 1}`}
                                                    className={`aspect-[3/4] w-14 shrink-0 overflow-hidden border-2 ${selectedImage === image ? "border-primary" : "border-transparent"}`}>
                                                    <img src={image} alt="" className="h-full w-full object-cover object-top" />
                                                </button>
                                            ))}
                                        </div>
                                    )}
                                </div>
                            </div>

                            <div className="flex min-w-0 flex-col">
                                <h1 className="text-xl font-semibold leading-snug text-main_text sm:text-2xl">{product.name}</h1>
                                {product.tag && <p className="mt-1 text-sm text-muted">{product.tag}</p>}

                                <div className="mt-4 border-t border-divider pt-4">
                                    <p className="flex flex-wrap items-baseline gap-x-2">
                                        <span className="text-2xl font-bold text-main_text">₹{price.toLocaleString("en-IN")}</span>
                                        {mrp > price && (
                                            <>
                                                <span className="text-base text-muted">MRP <span className="line-through">₹{mrp.toLocaleString("en-IN")}</span></span>
                                                <span className="text-base font-semibold text-[#E8762C]">({Math.round((1 - price / mrp) * 100)}% OFF)</span>
                                            </>
                                        )}
                                    </p>
                                    <p className="mt-1 text-xs font-semibold text-[#03A685]">inclusive of all taxes</p>
                                </div>

                                {variantError && <p role="alert" className="mt-4 text-sm text-red-600">{variantError}</p>}

                                {colours.length > 0 && (
                                    <div className="mt-6">
                                        <p className="mb-2 text-sm font-semibold uppercase tracking-wide text-main_text">
                                            Colour: <span className="font-normal normal-case text-text">{selectedVariant?.color ?? ""}</span>
                                        </p>
                                        <div className="flex flex-wrap gap-2">
                                            {colours.map((colour) => {
                                                const active = selectedVariant?.color === colour;
                                                const anyStock = variants.some((v) => v.color === colour && v.stock_quantity > 0);
                                                return (
                                                    <button key={colour} type="button" onClick={() => chooseColour(colour)} title={colour}
                                                        aria-pressed={active} aria-label={`Colour ${colour}${anyStock ? "" : " (out of stock)"}`}
                                                        className={`flex h-10 w-10 items-center justify-center rounded-full border-2 transition ${active ? "border-primary" : "border-transparent hover:border-divider"} ${anyStock ? "" : "opacity-40"}`}>
                                                        <span className="h-8 w-8 rounded-full border border-divider" style={{ background: swatchBackground(colour) }} />
                                                    </button>
                                                );
                                            })}
                                        </div>
                                    </div>
                                )}

                                {sizes.length > 0 && !(sizes.length === 1 && sizes[0].toLowerCase() === "free") && (
                                    <div className="mt-6">
                                        <div className="mb-2 flex items-center justify-between">
                                            <p className="text-sm font-semibold uppercase tracking-wide text-main_text">Select size</p>
                                            <a href="#size-help" className="text-sm font-semibold text-primary hover:underline">Size chart</a>
                                        </div>
                                        <div className="flex flex-wrap gap-2.5">
                                            {sizes.map((size) => {
                                                const v = variants.find((x) => x.size === size && x.color === selectedVariant?.color);
                                                const available = (v?.stock_quantity ?? 0) > 0;
                                                const active = selectedVariant?.size === size;
                                                return (
                                                    <button key={size} type="button" disabled={!v || !available} onClick={() => v && selectVariant(v.id)}
                                                        aria-pressed={active}
                                                        className={`relative flex h-12 min-w-12 items-center justify-center rounded-full border px-3 text-sm font-semibold transition ${active ? "border-primary bg-surface text-primary ring-1 ring-primary" : "border-gray-300 text-main_text hover:border-primary"} disabled:cursor-not-allowed disabled:border-gray-200 disabled:text-gray-300`}>
                                                        {size}
                                                        {v && !available && <span aria-hidden="true" className="absolute inset-x-2 top-1/2 h-px -rotate-45 bg-gray-300" />}
                                                    </button>
                                                );
                                            })}
                                        </div>
                                    </div>
                                )}
                                {sizes.length === 1 && sizes[0].toLowerCase() === "free" && (
                                    <p className="mt-4 text-sm text-text">Size: <strong>Free size</strong></p>
                                )}

                                {selectedVariant && (
                                    <p className={`mt-3 text-sm font-semibold ${stock === 0 ? "text-red-600" : stock !== undefined && stock <= 3 ? "text-[#E8762C]" : "text-[#03A685]"}`}>
                                        {stock === 0 ? "Out of stock" : stock !== undefined && stock <= 3 ? `Only ${stock} left!` : "In stock"}
                                    </p>
                                )}

                                {selectedVariant && stock !== undefined && stock > 1 && (
                                    <div className="mt-4 flex items-center gap-3">
                                        <span className="text-sm font-semibold text-main_text">Qty</span>
                                        <div className="inline-flex items-center rounded border border-divider">
                                            <button type="button" onClick={() => setQuantity((value) => Math.max(1, value - 1))} disabled={quantity <= 1}
                                                aria-label="Decrease quantity" className="flex h-9 w-9 items-center justify-center disabled:opacity-40">
                                                <Minus size={15} />
                                            </button>
                                            <span className="min-w-8 text-center text-sm font-semibold">{quantity}</span>
                                            <button type="button" onClick={() => setQuantity((value) => Math.min(selectedVariant.stock_quantity, value + 1))}
                                                disabled={quantity >= selectedVariant.stock_quantity} aria-label="Increase quantity"
                                                className="flex h-9 w-9 items-center justify-center disabled:opacity-40">
                                                <Plus size={15} />
                                            </button>
                                        </div>
                                    </div>
                                )}

                                {cartMessage && <p role="status" className="mt-4 text-sm font-medium text-primary">{cartMessage}</p>}

                                <div className="mt-6 grid grid-cols-2 gap-3 sm:flex">
                                    <button type="button" onClick={() => handleAddToCart(false)} disabled={outOfStock}
                                        className="col-span-2 inline-flex min-h-12 flex-1 items-center justify-center gap-2 rounded bg-primary px-5 font-semibold uppercase tracking-wide text-surface transition hover:bg-primary-dark disabled:cursor-not-allowed disabled:opacity-50 sm:col-span-1">
                                        <ShoppingCart size={18} aria-hidden="true" /> Add to bag
                                    </button>
                                    <button type="button" onClick={() => handleAddToCart(true)} disabled={outOfStock}
                                        className="min-h-12 rounded border border-primary px-5 font-semibold uppercase tracking-wide text-primary transition hover:bg-primary/5 disabled:cursor-not-allowed disabled:opacity-50">
                                        Buy now
                                    </button>
                                    <button type="button"
                                        onClick={() => setSaved(toggleWishlistProduct({ ...product, image: images[0] ?? product.image,
                                            description: product.tag ?? product.description, tag: undefined }))}
                                        aria-pressed={saved}
                                        className={`inline-flex min-h-12 items-center justify-center gap-2 rounded border px-5 font-semibold uppercase tracking-wide transition ${saved ? "border-sale text-sale" : "border-gray-300 text-main_text hover:border-main_text"}`}>
                                        <Heart size={17} aria-hidden="true" fill={saved ? "currentColor" : "none"} />
                                        {saved ? "Wishlisted" : "Wishlist"}
                                    </button>
                                </div>

                                <div className="mt-8 border-t border-divider pt-5">
                                    <h2 className="text-sm font-semibold uppercase tracking-wide text-main_text">Product details</h2>
                                    <p className="mt-2 whitespace-pre-line text-sm leading-6 text-text">
                                        {product.description || "No description available."}
                                    </p>
                                    {selectedVariant && <p className="mt-3 text-xs text-muted">SKU: {selectedVariant.sku}</p>}
                                </div>
                            </div>
                        </section>
                    )}
                </div>
            {productId && <ProductExtras productId={productId} />}
            </main>

            <Footer />
        </>
    );
}
