
import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { ArrowLeft, ShoppingCart, Minus, Plus } from "lucide-react";
import Header from "../components/Header";
import Footer from "../components/Footer";
import clothingFallback from "../assets/images/clothing-fallback.svg";
import { addToCart } from "../lib/cart";
import {
    getProducts,
    getProductImages,
    getProductVariants,
    type Product,
    type ProductImage,
    type ProductVariant,
} from "../lib/api/client";
import type { ClothingCardProduct } from "../components/Card";

const API_BASE = (import.meta.env.VITE_API_URL ?? "").replace(/\/$/, "");

function resolveImageUrl(url: string | null | undefined): string {
    if (!url) return clothingFallback;
    if (url.startsWith("http")) return url;
    return `${API_BASE}${url.startsWith("/") ? "" : "/"}${url}`;
}

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

                const products = await getProducts();
                const selectedProduct = products.find(
                    (item: Product) => item.id === productId && item.is_active,
                );

                if (!selectedProduct) {
                    throw new Error("Product not found.");
                }

                let imageUrls: string[] = [];
                try {
                    const productImages: ProductImage[] = await getProductImages(
                        selectedProduct.id,
                    );

                    imageUrls = productImages
                        .map((item) => resolveImageUrl(item.image_url))
                        .filter((url) => url !== clothingFallback);
                } catch {
                    // Image loading fail hone par fallback image use hogi.
                }

                let productVariants: ProductVariant[] = [];
                try {
                    productVariants = await getProductVariants(selectedProduct.id);
                } catch {
                    if (!cancelled) {
                        setVariantError("Size aur stock details load nahi ho paayi.");
                    }
                }

                productVariants = productVariants.filter(
                    (variant) => variant.is_active,
                );

                const primaryImage = imageUrls[0] ?? clothingFallback;

                const mappedProduct: ClothingCardProduct = {
                    id: selectedProduct.id,
                    name: selectedProduct.name,
                    description:
                        selectedProduct.description ?? selectedProduct.category,
                    price: selectedProduct.selling_price_paise / 100,
                    image: primaryImage,
                    imageAlt: selectedProduct.name,
                    colors: [],
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
            setCartMessage("Ye variant abhi out of stock hai.");
            return;
        }

        if (
            selectedVariant &&
            quantity > selectedVariant.stock_quantity
        ) {
            setCartMessage("Selected quantity available stock se zyada hai.");
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
            setCartMessage("Itni quantity stock mein available nahi hai.");
            return;
        }

        if (goToCart) {
            navigate("/cart");
            return;
        }

        setCartMessage("Product cart mein add ho gaya!");
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
                        <section className="grid gap-8 rounded-2xl border border-divider bg-surface p-4 shadow-sm sm:p-6 md:grid-cols-2 md:gap-12">
                            <div>
                                <div className="overflow-hidden rounded-xl bg-Alt_background">
                                    <img
                                        key={selectedImage}
                                        src={selectedImage}
                                        alt={product.imageAlt}
                                        onError={(event) => {
                                            event.currentTarget.onerror = null;
                                            event.currentTarget.src = clothingFallback;
                                        }}
                                        className="aspect-[4/5] w-full object-contain object-center sm:object-cover"
                                    />
                                </div>

                                {images.length > 1 && (
                                    <div className="mt-4 flex gap-3 overflow-x-auto pb-2" aria-label="Product images">
                                        {images.map((image, index) => (
                                            <button
                                                key={`${image}-${index}`}
                                                type="button"
                                                onClick={() => setSelectedImage(image)}
                                                aria-label={`View product image ${index + 1}`}
                                                aria-pressed={selectedImage === image}
                                                className={`h-20 w-16 shrink-0 overflow-hidden rounded-lg border-2 transition sm:h-24 sm:w-20 ${selectedImage === image
                                                    ? "border-primary"
                                                    : "border-divider hover:border-primary/50"
                                                    }`}
                                            >
                                                <img
                                                    src={image}
                                                    alt={`${product.name} view ${index + 1}`}
                                                    className="h-full w-full object-cover"
                                                />
                                            </button>
                                        ))}
                                    </div>
                                )}
                            </div>

                            <div className="flex flex-col py-2 sm:py-4">
                                {product.tag && (
                                    <p className="mb-3 text-sm font-semibold uppercase tracking-wide text-primary">
                                        {product.tag}
                                    </p>
                                )}

                                <h1 className="font-primaryFont text-2xl font-semibold text-main_text sm:text-4xl">
                                    {product.name}
                                </h1>

                                <p className="mt-4 text-2xl font-bold text-primary">
                                    ₹{price.toLocaleString("en-IN")}
                                </p>

                                <div className="my-6 border-t border-divider" />
                                {variantError && (
                                    <p role="alert" className="mb-4 text-sm text-red-600">
                                        {variantError}
                                    </p>
                                )}
                                {variants.length > 0 ? (
                                    <div className="space-y-5">
                                        <div>
                                            <h2 className="mb-2 text-sm font-semibold text-main_text">
                                                Available variants
                                            </h2>
                                            <div className="flex flex-wrap gap-2">
                                                {variants.map((variant) => (
                                                    <button
                                                        key={variant.id}
                                                        type="button"
                                                        disabled={variant.stock_quantity <= 0}
                                                        onClick={() => selectVariant(variant.id)}
                                                        aria-pressed={selectedVariantId === variant.id}
                                                        className={`rounded-lg border px-4 py-2 text-sm transition ${selectedVariantId === variant.id
                                                            ? "border-primary bg-primary/10 font-semibold text-primary"
                                                            : "border-divider text-main_text"
                                                            } ${variant.stock_quantity <= 0
                                                                ? "cursor-not-allowed opacity-40"
                                                                : "hover:border-primary"
                                                            }`}
                                                    >
                                                        {variant.size} / {variant.color}
                                                    </button>
                                                ))}
                                            </div>
                                        </div>

                                        {selectedVariant && (
                                            <>
                                                <div className="text-sm text-text">
                                                    <p>
                                                        Size: <strong>{selectedVariant.size}</strong>
                                                    </p>
                                                    <p className="mt-1">
                                                        Colour: <strong>{selectedVariant.color}</strong>
                                                    </p>
                                                    <p className="mt-1">
                                                        SKU: <strong>{selectedVariant.sku}</strong>
                                                    </p>
                                                    <p className={`mt-2 font-semibold ${stock === 0 ? "text-red-600" : "text-green-700"}`}>
                                                        {stock === 0
                                                            ? "Out of stock"
                                                            : `${stock} items available`}
                                                    </p>
                                                </div>

                                                <div>
                                                    <label className="mb-2 block text-sm font-semibold text-main_text">
                                                        Quantity
                                                    </label>
                                                    <div className="inline-flex items-center rounded-lg border border-divider">
                                                        <button
                                                            type="button"
                                                            onClick={() => setQuantity((value) => Math.max(1, value - 1))}
                                                            disabled={quantity <= 1}
                                                            aria-label="Decrease quantity"
                                                            className="flex h-10 w-10 items-center justify-center disabled:opacity-40"
                                                        >
                                                            <Minus size={16} />
                                                        </button>
                                                        <span className="min-w-10 text-center font-semibold">
                                                            {quantity}
                                                        </span>
                                                        <button
                                                            type="button"
                                                            onClick={() =>
                                                                setQuantity((value) =>
                                                                    Math.min(selectedVariant.stock_quantity, value + 1),
                                                                )
                                                            }
                                                            disabled={quantity >= selectedVariant.stock_quantity}
                                                            aria-label="Increase quantity"
                                                            className="flex h-10 w-10 items-center justify-center disabled:opacity-40"
                                                        >
                                                            <Plus size={16} />
                                                        </button>
                                                    </div>
                                                </div>
                                            </>
                                        )}
                                    </div>
                                ) : (
                                    <p role="alert" className="mb-4 text-sm text-red-600">
                                        {variantError}
                                    </p>
                                )}

                                <h2 className="mt-7 text-base font-semibold text-main_text">
                                    Product description
                                </h2>
                                <p className="mt-3 whitespace-pre-line text-sm leading-7 text-text sm:text-base">
                                    {product.description || "No description available."}
                                </p>

                                {cartMessage && (
                                    <p role="status" className="mt-4 text-sm font-medium text-primary">
                                        {cartMessage}
                                    </p>
                                )}

                                <div className="mt-8 flex flex-col gap-3 sm:flex-row">
                                    <button
                                        type="button"
                                        onClick={() => handleAddToCart(false)}
                                        disabled={outOfStock}
                                        className="inline-flex min-h-12 flex-1 items-center justify-center gap-2 rounded-lg border border-primary px-5 py-3 font-semibold text-primary transition hover:bg-primary/5 disabled:cursor-not-allowed disabled:opacity-50"
                                    >
                                        <ShoppingCart size={19} />
                                        Add to cart
                                    </button>

                                    <button
                                        type="button"
                                        onClick={() => handleAddToCart(true)}
                                        disabled={outOfStock}
                                        className="min-h-12 flex-1 rounded-lg bg-primary px-5 py-3 font-semibold text-surface transition hover:bg-primary-dark disabled:cursor-not-allowed disabled:opacity-50"
                                    >
                                        Buy now
                                    </button>
                                </div>
                            </div>
                        </section>
                    )}
                </div>
            </main>

            <Footer />
        </>
    );
}
