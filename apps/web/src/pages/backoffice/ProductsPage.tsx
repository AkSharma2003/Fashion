
import { useCallback, useEffect, useState } from "react";
import {
  createProduct,
  getProducts,
  updateProduct,
  uploadProductImage,
  getProductVariants,
  createProductVariant,
  updateProductVariant,
  deleteProductPermanently,
  deleteVariantPermanently,
  type Product,
  type ProductCreateInput,
  type ProductVariant,
  type ProductVariantCreateInput,
  type ProductVariantUpdateInput,
} from "../../lib/api/client";
import ColorPicker from "../../components/backoffice/ColorPicker";
import { swatchBackground } from "../../lib/colors";
import { hasRole, useStaff } from "../../lib/auth/staff";

const CATEGORY_SUGGESTIONS = ["Sarees", "Suits", "Kids", "Lehenga", "Dupatta", "Blouse", "Kurti", "Petticoat", "Jewellery"];
const GST_OPTIONS: { label: string; value: string }[] = [
  { label: "Automatic (by price slab in Settings)", value: "" },
  { label: "0%", value: "0" }, { label: "5%", value: "500" }, { label: "12%", value: "1200" }, { label: "18%", value: "1800" },
];

type DisplayProduct = {
  id: string;
  name: string;
  category: string;
  barcode: string;
  sku: string;
  price: number;
  stock: string;
  description: string;
  isActive: boolean;
  mrp: number | null;
  gstRateBp: number | null;
  hsnCode: string;
  fallPico: boolean;
  variantCount: number;
  stockOnHand: number;
  colors: string[];
  imageUrl: string | null;
};

const MAX_IMAGES = 5;

type VariantFormState = {
  size: string;
  color: string;
  sku: string;
  selling_price: string;
  stock_quantity: string;
};

const emptyVariantForm: VariantFormState = {
  size: "",
  color: "",
  sku: "",
  selling_price: "",
  stock_quantity: "0",
};

const emptyForm: ProductCreateInput = {
  name: "",
  description: "",
  sku: "",
  barcode: "",
  category: "",
  selling_price_paise: 0,
  mrp_paise: null,
  gst_rate_bp: null,
  hsn_code: "",
  fall_pico_eligible: false,
};

function toDisplayProduct(product: Product): DisplayProduct {
  return {
    id: product.id,
    name: product.name,
    category: product.category,
    barcode: product.barcode ?? "—",
    sku: product.sku,
    price: product.selling_price_paise / 100,
    stock: product.variant_count ? String(product.stock_on_hand ?? 0) : "—",
    description: product.description ?? "",
    isActive: product.is_active,
    mrp: product.mrp_paise != null ? product.mrp_paise / 100 : null,
    gstRateBp: product.gst_rate_bp ?? null,
    hsnCode: product.hsn_code ?? "",
    fallPico: Boolean(product.fall_pico_eligible),
    variantCount: product.variant_count ?? 0,
    stockOnHand: product.stock_on_hand ?? 0,
    colors: product.colors ?? [],
    imageUrl: product.image_url ?? null,
  };
}

export default function ProductsPage() {
  const { me, shops, shopId } = useStaff();
  const canDelete = hasRole(me, "Manager");      // deleting / archiving and restoring is a manager's decision
  // Stock typed on this screen goes to: the user's own shop, else the shop picked in the header, else the main shop.
  const stockShop = shops.find((s) => s.id === (me?.shop_id ?? (shopId !== "all" ? shopId : ""))) ?? shops.find((s) => s.is_main);
  const shopStock = (v: ProductVariant) => v.by_shop?.find((b) => b.shop_id === stockShop?.id)?.available ?? 0;
  const [products, setProducts] = useState<DisplayProduct[]>([]);
  const [search, setSearch] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [saving, setSaving] = useState(false);
  const [showArchived, setShowArchived] = useState(false);

  const [formOpen, setFormOpen] = useState(false);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [form, setForm] = useState<ProductCreateInput>(emptyForm);
  const [imageFiles, setImageFiles] = useState<File[]>([]);
  const [previewUrls, setPreviewUrls] = useState<string[]>([]);

  const [variantProduct, setVariantProduct] =
    useState<DisplayProduct | null>(null);

  const [variants, setVariants] = useState<ProductVariant[]>([]);
  const [variantsLoading, setVariantsLoading] = useState(false);
  const [variantSaving, setVariantSaving] = useState(false);
  const [variantFormOpen, setVariantFormOpen] = useState(false);
  const [editingVariantId, setEditingVariantId] = useState<string | null>(null);
  const [variantForm, setVariantForm] =
    useState<VariantFormState>(emptyVariantForm);

  // Create and clean up preview URLs whenever selected images change.
  useEffect(() => {
    const urls = imageFiles.map((file) => URL.createObjectURL(file));
    setPreviewUrls(urls);

    return () => {
      urls.forEach((url) => URL.revokeObjectURL(url));
    };
  }, [imageFiles]);

  const loadProducts = useCallback(async () => {
    try {
      setLoading(true);
      setError("");

      const data = await getProducts(showArchived);
      setProducts(data.map(toDisplayProduct));
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Unable to load products."
      );
    } finally {
      setLoading(false);
    }
  }, [showArchived]);

  useEffect(() => {
    void loadProducts();
  }, [loadProducts]);

  function resetImageSelection() {
    setImageFiles([]);
  }

  function openAddForm() {
    setEditingId(null);
    setForm({ ...emptyForm });
    resetImageSelection();
    setNotice("");
    setError("");
    setFormOpen(true);
  }

  function openEditForm(product: DisplayProduct) {
    setEditingId(product.id);
    setForm({
      name: product.name,
      description: product.description,
      sku: product.sku,
      barcode: product.barcode === "—" ? "" : product.barcode,
      category: product.category,
      selling_price_paise: Math.round(product.price * 100),
      mrp_paise: product.mrp != null ? Math.round(product.mrp * 100) : null,
      gst_rate_bp: product.gstRateBp,
      hsn_code: product.hsnCode,
      fall_pico_eligible: product.fallPico,
    });
    resetImageSelection();
    setNotice("");
    setError("");
    setFormOpen(true);
  }

  function updateFormField(
    field: keyof ProductCreateInput,
    value: string
  ) {
    setForm((current) => ({
      ...current,
      [field]:
        field === "selling_price_paise"
          ? Math.round(Number(value || 0) * 100)
          : field === "mrp_paise"
            ? (value === "" ? null : Math.round(Number(value) * 100))
            : field === "gst_rate_bp"
              ? (value === "" ? null : Number(value))
              : value,
      // Sarees get free fall-pico by default; staff can untick it.
      ...(field === "category" && !editingId && /saree/i.test(value) ? { fall_pico_eligible: true } : {}),
    }));
  }

  function handleImageSelection(
    event: React.ChangeEvent<HTMLInputElement>
  ) {
    const selectedFiles = Array.from(event.target.files ?? []);

    if (selectedFiles.length > MAX_IMAGES) {
      setError(`You can select a maximum of ${MAX_IMAGES} images at a time.`);
      setImageFiles([]);
      event.target.value = "";
      return;
    }

    const invalidFile = selectedFiles.find(
      (file) =>
        !["image/jpeg", "image/png", "image/webp"].includes(file.type)
    );

    if (invalidFile) {
      setError("Only JPG, PNG, and WebP images are allowed.");
      setImageFiles([]);
      event.target.value = "";
      return;
    }

    setError("");
    setImageFiles(selectedFiles);
  }

  function removeSelectedImage(indexToRemove: number) {
    setImageFiles((current) =>
      current.filter((_, index) => index !== indexToRemove)
    );
  }

  async function handleSave(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSaving(true);
    setError("");
    setNotice("");

    try {
      if (form.selling_price_paise < 0) {
        throw new Error("Price cannot be negative.");
      }
      if (form.mrp_paise != null && form.mrp_paise > 0 && form.mrp_paise < form.selling_price_paise) {
        throw new Error("MRP cannot be lower than the selling price.");
      }

      const input: ProductCreateInput = {
        name: form.name.trim(),
        description: form.description?.trim() || null,
        sku: form.sku.trim(),
        barcode: form.barcode?.trim() || null,
        category: form.category.trim(),
        selling_price_paise: form.selling_price_paise,
        mrp_paise: form.mrp_paise || null,
        gst_rate_bp: form.gst_rate_bp ?? null,
        hsn_code: form.hsn_code?.trim() || null,
        fall_pico_eligible: Boolean(form.fall_pico_eligible),
      };

      let savedProduct: Product;

      if (editingId) {
        savedProduct = await updateProduct(editingId, input);
      } else {
        savedProduct = await createProduct(input);
      }

      // Upload each selected image separately using the existing API.
      let uploadedCount = 0;

      for (const imageFile of imageFiles) {
        await uploadProductImage(savedProduct.id, imageFile);
        uploadedCount += 1;
      }

      setFormOpen(false);
      setForm({ ...emptyForm });
      resetImageSelection();

      const actionText = editingId
        ? "Product updated successfully."
        : "Product added successfully.";

      setNotice(
        uploadedCount > 0
          ? `${actionText} ${uploadedCount} image(s) uploaded.`
          : actionText
      );

      await loadProducts();
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Failed to save product."
      );
    } finally {
      setSaving(false);
    }
  }

  async function handleDelete(product: DisplayProduct) {
    const confirmed = window.confirm(
      `Delete "${product.name}"?\n\nIf it was ever sold or had stock, it will be archived instead (hidden from the shop and POS, history kept).`
    );
    if (!confirmed) return;
    setError("");
    setNotice("");
    try {
      const result = await deleteProductPermanently(product.id);
      setNotice(result.message);
      if (variantProduct?.id === product.id) setVariantProduct(null);
      if (editingId === product.id) setFormOpen(false);
      await loadProducts();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to delete product.");
    }
  }

  async function handleRestore(product: DisplayProduct) {
    setError("");
    setNotice("");
    try {
      await updateProduct(product.id, { is_active: true });
      setNotice(`"${product.name}" is back in the shop.`);
      await loadProducts();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to restore product.");
    }
  }

  async function loadVariants(productId: string) {
    setVariantsLoading(true);
    setError("");

    try {
      const data = await getProductVariants(productId);
      setVariants(data.filter((variant) => variant.is_active));
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Unable to load product variants.",
      );
    } finally {
      setVariantsLoading(false);
    }
  }

  async function openVariants(product: DisplayProduct) {
    setVariantProduct(product);
    setVariantFormOpen(false);
    setEditingVariantId(null);
    setVariantForm({ ...emptyVariantForm });
    setNotice("");
    await loadVariants(product.id);
  }

  function openAddVariantForm() {
    setEditingVariantId(null);
    setVariantForm({ ...emptyVariantForm });
    setVariantFormOpen(true);
    setError("");
  }

  function openEditVariantForm(variant: ProductVariant) {
    setEditingVariantId(variant.id);
    setVariantForm({
      size: variant.size,
      color: variant.color,
      sku: variant.sku,
      selling_price: (variant.selling_price_paise / 100).toFixed(2),
      stock_quantity: String(shopStock(variant)),
    });
    setVariantFormOpen(true);
    setError("");
  }

  async function handleSaveVariant(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();

    if (!variantProduct) return;

    setVariantSaving(true);
    setError("");
    setNotice("");

    try {
      const price = Number(variantForm.selling_price);
      const stock = Number(variantForm.stock_quantity);

      if (!Number.isFinite(price) || price < 0) {
        throw new Error("Enter a valid selling price.");
      }

      if (!Number.isInteger(stock) || stock < 0) {
        throw new Error("Stock quantity must be a non-negative whole number.");
      }

      const commonFields = {
        size: variantForm.size.trim(),
        color: variantForm.color.trim(),
        sku: variantForm.sku.trim(),
        selling_price_paise: Math.round(price * 100),
        stock_quantity: stock,
      };

      if (!commonFields.size || !commonFields.color || !commonFields.sku) {
        throw new Error("Size, color and SKU are required.");
      }

      if (editingVariantId) {
        const input: ProductVariantUpdateInput = commonFields;
        await updateProductVariant(
          variantProduct.id,
          editingVariantId,
          input,
        );
        setNotice("Variant updated successfully.");
      } else {
        const input: ProductVariantCreateInput = commonFields;
        await createProductVariant(variantProduct.id, input);
        setNotice("Variant added successfully.");
      }

      setVariantFormOpen(false);
      setVariantForm({ ...emptyVariantForm });
      setEditingVariantId(null);

      await loadVariants(variantProduct.id);
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Failed to save variant.",
      );
    } finally {
      setVariantSaving(false);
    }
  }

  async function handleDeactivateVariant(variant: ProductVariant) {
    if (!variantProduct) return;

    const confirmed = window.confirm(
      `Delete variant "${variant.size} / ${variant.color}"?\n\nIf it was ever sold or had stock, it will be hidden instead (history kept).`,
    );

    if (!confirmed) return;

    setError("");
    setNotice("");

    try {
      const result = await deleteVariantPermanently(variantProduct.id, variant.id);
      setNotice(result.message);
      await loadVariants(variantProduct.id);
      await loadProducts();
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Failed to delete variant.",
      );
    }
  }

  const filteredProducts = products.filter((product) =>
    `${product.name} ${product.barcode} ${product.category} ${product.sku}`
      .toLowerCase()
      .includes(search.toLowerCase())
  );

  return (
    <div className="min-h-screen bg-[#F7F7F7] p-4 text-[#111111] sm:p-6">
      <div className="mb-6 flex flex-wrap items-start justify-between gap-4">
        <div>
          <p className="text-sm text-gray-500">Backoffice / Products</p>
          <h1 className="mt-1 text-2xl font-semibold">Products</h1>
          <p className="mt-1 text-sm text-gray-500">
            Add products, update details and manage product images.
          </p>
        </div>

        <button
          type="button"
          onClick={openAddForm}
          className="min-h-11 rounded-lg bg-[#111111] px-5 py-3 text-sm font-medium text-white hover:bg-black"
        >
          + Add Product
        </button>
      </div>

      {loading && (
        <p className="mb-4 text-sm text-gray-500">Loading products...</p>
      )}

      {error && (
        <div className="mb-4 rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-700">
          {error}
        </div>
      )}

      {notice && (
        <div className="mb-4 rounded-lg border border-green-200 bg-green-50 p-3 text-sm text-green-800">
          {notice}
        </div>
      )}

      {formOpen && (
        <form
          onSubmit={handleSave}
          className="mb-6 rounded-xl border border-gray-200 bg-white p-4 sm:p-6"
        >
          <h2 className="mb-5 text-lg font-semibold">
            {editingId ? "Update Product" : "Add New Product"}
          </h2>

          <div className="grid gap-4 sm:grid-cols-2">
            <div>
              <label htmlFor="product-name" className="mb-1 block text-sm font-medium">
                Product name *
              </label>
              <input
                id="product-name"
                required
                maxLength={200}
                value={form.name}
                onChange={(e) => updateFormField("name", e.target.value)}
                className="min-h-11 w-full rounded-lg border border-gray-300 px-3 text-sm outline-none focus:border-black"
                placeholder="e.g. Silk Saree"
              />
            </div>

            <div>
              <label htmlFor="product-sku" className="mb-1 block text-sm font-medium">
                SKU *
              </label>
              <input
                id="product-sku"
                required
                value={form.sku}
                onChange={(e) => updateFormField("sku", e.target.value)}
                className="min-h-11 w-full rounded-lg border border-gray-300 px-3 text-sm outline-none focus:border-black"
                placeholder="e.g. SAREE-001"
              />
            </div>

            <div>
              <label htmlFor="product-category" className="mb-1 block text-sm font-medium">
                Category *
              </label>
              <input
                id="product-category"
                required
                value={form.category}
                onChange={(e) => updateFormField("category", e.target.value)}
                list="category-options"
                className="min-h-11 w-full rounded-lg border border-gray-300 px-3 text-sm outline-none focus:border-black"
                placeholder="Choose or type, e.g. Sarees"
              />
              <datalist id="category-options">
                {CATEGORY_SUGGESTIONS.map((c) => <option key={c} value={c} />)}
              </datalist>
            </div>

            <div>
              <label htmlFor="product-barcode" className="mb-1 block text-sm font-medium">
                Barcode
              </label>
              <input
                id="product-barcode"
                value={form.barcode ?? ""}
                onChange={(e) => updateFormField("barcode", e.target.value)}
                className="min-h-11 w-full rounded-lg border border-gray-300 px-3 text-sm outline-none focus:border-black"
                placeholder="Enter barcode"
              />
            </div>

            <div>
              <label htmlFor="product-price" className="mb-1 block text-sm font-medium">
                Selling price (₹) *
              </label>
              <input
                id="product-price"
                required
                type="number"
                min="0"
                step="0.01"
                value={(form.selling_price_paise / 100).toString()}
                onChange={(e) =>
                  updateFormField("selling_price_paise", e.target.value)
                }
                className="min-h-11 w-full rounded-lg border border-gray-300 px-3 text-sm outline-none focus:border-black"
                placeholder="e.g. 1499"
              />
            </div>

            <div>
              <label htmlFor="product-mrp" className="mb-1 block text-sm font-medium">
                MRP (₹)
              </label>
              <input
                id="product-mrp"
                type="number"
                min="0"
                step="0.01"
                value={form.mrp_paise != null ? (form.mrp_paise / 100).toString() : ""}
                onChange={(e) => updateFormField("mrp_paise", e.target.value)}
                className="min-h-11 w-full rounded-lg border border-gray-300 px-3 text-sm outline-none focus:border-black"
                placeholder="Printed price, optional"
              />
            </div>

            <div>
              <label htmlFor="product-gst" className="mb-1 block text-sm font-medium">
                GST rate
              </label>
              <select
                id="product-gst"
                value={form.gst_rate_bp != null ? String(form.gst_rate_bp) : ""}
                onChange={(e) => updateFormField("gst_rate_bp", e.target.value)}
                className="min-h-11 w-full rounded-lg border border-gray-300 bg-white px-3 text-sm outline-none focus:border-black"
              >
                {GST_OPTIONS.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
              </select>
            </div>

            <div>
              <label htmlFor="product-hsn" className="mb-1 block text-sm font-medium">
                HSN code
              </label>
              <input
                id="product-hsn"
                maxLength={16}
                value={form.hsn_code ?? ""}
                onChange={(e) => updateFormField("hsn_code", e.target.value)}
                className="min-h-11 w-full rounded-lg border border-gray-300 px-3 text-sm outline-none focus:border-black"
                placeholder="e.g. 5007 (silk saree)"
              />
            </div>

            <label className="flex items-start gap-3 rounded-lg border border-gray-200 p-3 sm:col-span-2">
              <input
                type="checkbox"
                className="mt-0.5 h-4 w-4 accent-[#111111]"
                checked={Boolean(form.fall_pico_eligible)}
                onChange={(e) => setForm((current) => ({ ...current, fall_pico_eligible: e.target.checked }))}
              />
              <span className="text-sm">
                <span className="font-medium">Free fall-pico</span>
                <span className="block text-gray-500">
                  For sarees: a fall-pico job is made automatically when it sells above the limit in Settings.
                </span>
              </span>
            </label>

            <div className="sm:col-span-2">
              <label htmlFor="product-images" className="mb-1 block text-sm font-medium">
                Product images
              </label>
              <input
                id="product-images"
                type="file"
                accept="image/jpeg,image/png,image/webp"
                multiple
                onChange={handleImageSelection}
                className="min-h-11 w-full rounded-lg border border-gray-300 px-3 py-2 text-sm"
              />
              <p className="mt-1 text-xs text-gray-500">
                Select up to 5 photos at a time. JPG, PNG or WebP. Optional.
                Existing images are kept when you add new photos.
              </p>

              {imageFiles.length > 0 && (
                <div className="mt-4 grid grid-cols-2 gap-3 min-[480px]:grid-cols-3 sm:grid-cols-5">
                  {imageFiles.map((file, index) => (
                    <div
                      key={`${file.name}-${file.size}-${index}`}
                      className="min-w-0 rounded-lg border border-gray-200 p-2"
                    >
                      <img
                        src={previewUrls[index]}
                        alt={`Product preview ${index + 1}`}
                        className="h-28 w-full rounded-md object-cover"
                      />
                      <p className="mt-2 truncate text-xs text-gray-600">
                        {file.name}
                      </p>
                      <button
                        type="button"
                        disabled={saving}
                        onClick={() => removeSelectedImage(index)}
                        className="mt-2 min-h-9 w-full rounded-md border border-gray-300 px-2 text-xs hover:bg-gray-50 disabled:opacity-60"
                      >
                        Remove
                      </button>
                    </div>
                  ))}
                </div>
              )}
            </div>

            <div className="sm:col-span-2">
              <label htmlFor="product-description" className="mb-1 block text-sm font-medium">
                Description
              </label>
              <textarea
                id="product-description"
                rows={3}
                value={form.description ?? ""}
                onChange={(e) => updateFormField("description", e.target.value)}
                className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm outline-none focus:border-black"
                placeholder="Product details..."
              />
            </div>
          </div>

          <div className="mt-5 flex flex-wrap gap-3">
            <button
              type="submit"
              disabled={saving}
              className="min-h-11 rounded-lg bg-[#111111] px-5 py-3 text-sm font-medium text-white disabled:cursor-not-allowed disabled:opacity-60"
            >
              {saving
                ? "Saving..."
                : editingId
                  ? "Save Changes"
                  : "Add Product"}
            </button>

            <button
              type="button"
              disabled={saving}
              onClick={() => {
                setFormOpen(false);
                resetImageSelection();
              }}
              className="min-h-11 rounded-lg border border-gray-300 px-5 py-3 text-sm hover:bg-gray-50 disabled:opacity-60"
            >
              Cancel
            </button>
          </div>
        </form>
      )}

      <div className="mb-5 rounded-xl border border-gray-200 bg-white p-4">
        <label htmlFor="product-search" className="mb-2 block text-sm font-medium">
          Search products
        </label>
        <input
          id="product-search"
          value={search}
          onChange={(event) => setSearch(event.target.value)}
          placeholder="Search by name, category, SKU or barcode..."
          className="min-h-11 w-full rounded-lg border border-gray-300 px-3 text-sm outline-none focus:border-[#111111]"
        />
        {canDelete && <label className="mt-3 inline-flex items-center gap-2 text-sm text-gray-600">
          <input type="checkbox" className="h-4 w-4 accent-[#111111]" checked={showArchived}
            onChange={(e) => setShowArchived(e.target.checked)} />
          Show archived products
        </label>}
      </div>

      <div className="overflow-x-auto rounded-xl border border-gray-200 bg-white">
        <table className="w-full min-w-[960px] text-left text-sm">
          <thead className="border-b border-gray-200 bg-gray-50">
            <tr>
              <th className="p-4">Product</th>
              <th className="p-4">Colours</th>
              <th className="p-4">Category</th>
              <th className="p-4">Barcode</th>
              <th className="p-4">Price</th>
              <th className="p-4">Stock</th>
              <th className="p-4">Status</th>
              <th className="p-4">Actions</th>
            </tr>
          </thead>

          <tbody className="divide-y divide-gray-200">
            {!loading &&
              !error &&
              filteredProducts.map((product) => (
                <tr key={product.id}>
                  <td className="p-4">
                    <div className="flex items-center gap-3">
                      {product.imageUrl ? (
                        <img src={product.imageUrl} alt="" className="h-12 w-12 shrink-0 rounded-lg object-cover" />
                      ) : (
                        <span className="flex h-12 w-12 shrink-0 items-center justify-center rounded-lg bg-gray-100 text-xs text-gray-400">No photo</span>
                      )}
                      <div className="min-w-0">
                        <p className="font-medium">{product.name}</p>
                        <p className="mt-1 text-xs text-gray-500">SKU: {product.sku}</p>
                        {product.fallPico && <p className="mt-1 text-xs text-gray-500">Free fall-pico</p>}
                      </div>
                    </div>
                  </td>
                  <td className="p-4">
                    {product.colors.length ? (
                      <div className="flex max-w-[140px] flex-wrap gap-1">
                        {product.colors.map((c) => (
                          <span key={c} title={c} aria-label={c} className="h-5 w-5 rounded-full border border-gray-300"
                            style={{ background: swatchBackground(c) }} />
                        ))}
                      </div>
                    ) : <span className="text-xs text-gray-400">—</span>}
                  </td>
                  <td className="p-4">{product.category}</td>
                  <td className="p-4 font-mono text-xs">{product.barcode}</td>
                  <td className="p-4">
                    ₹
                    {product.price.toLocaleString("en-IN", {
                      minimumFractionDigits: 2,
                      maximumFractionDigits: 2,
                    })}
                  </td>
                  <td className="p-4">
                    {product.variantCount ? (
                      <>
                        <p className={product.stockOnHand <= 0 ? "font-medium text-red-700" : ""}>{product.stockOnHand} pcs</p>
                        <p className="text-xs text-gray-500">{product.variantCount} variant{product.variantCount > 1 ? "s" : ""}</p>
                      </>
                    ) : <span className="text-xs text-amber-700">Add a variant</span>}
                  </td>
                  <td className="p-4">
                    <span
                      className={`rounded-full px-2 py-1 text-xs ${product.isActive
                        ? "bg-green-100 text-green-800"
                        : "bg-gray-100 text-gray-600"
                        }`}
                    >
                      {product.isActive ? "Active" : "Archived"}
                    </span>
                  </td>
                  <td className="p-4">
                    <div className="flex gap-2">
                      <button
                        type="button"
                        onClick={() => openEditForm(product)}
                        className="rounded-lg border border-gray-300 px-3 py-2 hover:bg-gray-50"
                      >
                        Edit
                      </button>
                      <button
                        type="button"
                        onClick={() => void openVariants(product)}
                        className="rounded-lg border border-gray-300 px-3 py-2 hover:bg-gray-50"
                      >
                        Variants
                      </button>
                      {!canDelete ? null : product.isActive ? (
                        <button
                          type="button"
                          onClick={() => void handleDelete(product)}
                          className="rounded-lg border border-red-200 px-3 py-2 text-red-700 hover:bg-red-50"
                        >
                          Delete
                        </button>
                      ) : (
                        <button
                          type="button"
                          onClick={() => void handleRestore(product)}
                          className="rounded-lg border border-green-300 px-3 py-2 text-green-800 hover:bg-green-50"
                        >
                          Restore
                        </button>
                      )}
                    </div>
                  </td>
                </tr>
              ))}

            {!loading && !error && filteredProducts.length === 0 && (
              <tr>
                <td colSpan={8} className="p-8 text-center text-gray-500">
                  No products found.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      {variantProduct && (
        <section className="mt-6 rounded-xl border border-gray-200 bg-white p-4 sm:p-6">
          <div className="mb-5 flex flex-wrap items-center justify-between gap-3">
            <div>
              <h2 className="text-lg font-semibold">Manage Variants</h2>
              <p className="mt-1 text-sm text-gray-500">
                {variantProduct.name}
              </p>
            </div>

            <div className="flex gap-2">
              <button
                type="button"
                onClick={openAddVariantForm}
                className="min-h-10 rounded-lg bg-[#111111] px-4 py-2 text-sm font-medium text-white"
              >
                + Add Variant
              </button>

              <button
                type="button"
                onClick={() => {
                  setVariantProduct(null);
                  setVariantFormOpen(false);
                }}
                className="min-h-10 rounded-lg border border-gray-300 px-4 py-2 text-sm"
              >
                Close
              </button>
            </div>
          </div>

          {variantFormOpen && (
            <form
              onSubmit={handleSaveVariant}
              className="mb-6 rounded-lg border border-gray-200 bg-gray-50 p-4"
            >
              <h3 className="mb-4 font-semibold">
                {editingVariantId ? "Edit Variant" : "Add New Variant"}
              </h3>

              <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
                <div>
                  <label htmlFor="variant-size" className="mb-1 block text-sm font-medium">
                    Size *
                  </label>
                  <input
                    id="variant-size"
                    required
                    maxLength={30}
                    value={variantForm.size}
                    onChange={(e) =>
                      setVariantForm((current) => ({ ...current, size: e.target.value }))
                    }
                    placeholder="e.g. M, L, XL"
                    className="min-h-11 w-full rounded-lg border border-gray-300 px-3"
                  />
                </div>

                <div className="sm:col-span-2 lg:col-span-3">
                  <label htmlFor="variant-color" className="mb-1 block text-sm font-medium">
                    Colour *
                  </label>
                  <ColorPicker
                    value={variantForm.color}
                    onChange={(name) => setVariantForm((current) => ({ ...current, color: name }))}
                  />
                </div>

                <div>
                  <label htmlFor="variant-sku" className="mb-1 block text-sm font-medium">
                    SKU *
                  </label>
                  <input
                    id="variant-sku"
                    required
                    maxLength={100}
                    value={variantForm.sku}
                    onChange={(e) =>
                      setVariantForm((current) => ({ ...current, sku: e.target.value }))
                    }
                    placeholder="e.g. SAREE-YEL-M"
                    className="min-h-11 w-full rounded-lg border border-gray-300 px-3"
                  />
                </div>

                <div>
                  <label htmlFor="variant-price" className="mb-1 block text-sm font-medium">
                    Selling Price (₹) *
                  </label>
                  <input
                    id="variant-price"
                    type="number"
                    required
                    min="0"
                    step="0.01"
                    value={variantForm.selling_price}
                    onChange={(e) =>
                      setVariantForm((current) => ({
                        ...current,
                        selling_price: e.target.value,
                      }))
                    }
                    className="min-h-11 w-full rounded-lg border border-gray-300 px-3"
                  />
                </div>

                <div>
                  <label htmlFor="variant-stock" className="mb-1 block text-sm font-medium">
                    Stock in {stockShop?.name ?? "this shop"} *
                  </label>
                  <input
                    id="variant-stock"
                    type="number"
                    required
                    min="0"
                    step="1"
                    value={variantForm.stock_quantity}
                    onChange={(e) =>
                      setVariantForm((current) => ({
                        ...current,
                        stock_quantity: e.target.value,
                      }))
                    }
                    className="min-h-11 w-full rounded-lg border border-gray-300 px-3"
                  />
                </div>
              </div>

              <div className="mt-4 flex gap-3">
                <button
                  type="submit"
                  disabled={variantSaving}
                  className="min-h-10 rounded-lg bg-[#111111] px-4 py-2 text-sm font-medium text-white disabled:opacity-60"
                >
                  {variantSaving
                    ? "Saving..."
                    : editingVariantId
                      ? "Save Changes"
                      : "Add Variant"}
                </button>

                <button
                  type="button"
                  disabled={variantSaving}
                  onClick={() => setVariantFormOpen(false)}
                  className="min-h-10 rounded-lg border border-gray-300 px-4 py-2 text-sm"
                >
                  Cancel
                </button>
              </div>
            </form>
          )}

          {variantsLoading ? (
            <p className="py-6 text-sm text-gray-500">Loading variants...</p>
          ) : (
            <div className="overflow-x-auto rounded-lg border border-gray-200">
              <table className="w-full min-w-[700px] text-left text-sm">
                <thead className="border-b border-gray-200 bg-gray-50">
                  <tr>
                    <th className="p-3">Size</th>
                    <th className="p-3">Color</th>
                    <th className="p-3">SKU</th>
                    <th className="p-3">Price</th>
                    <th className="p-3">Stock</th>
                    <th className="p-3">Actions</th>
                  </tr>
                </thead>

                <tbody className="divide-y divide-gray-200">
                  {variants.map((variant) => (
                    <tr key={variant.id}>
                      <td className="p-3">{variant.size}</td>
                      <td className="p-3">
                        <span className="inline-flex items-center gap-2">
                          <span aria-hidden="true" className="h-4 w-4 rounded-full border border-gray-300"
                            style={{ background: swatchBackground(variant.color) }} />
                          {variant.color}
                        </span>
                      </td>
                      <td className="p-3 font-mono text-xs">{variant.sku}</td>
                      <td className="p-3">
                        {(variant.selling_price_paise / 100).toLocaleString("en-IN", {
                          style: "currency",
                          currency: "INR",
                        })}
                      </td>
                      <td className="p-3">
                        <p className="font-medium">{variant.stock_quantity}</p>
                        {(variant.by_shop?.length ?? 0) > 1 && (
                          <p className="text-xs text-gray-500">
                            {variant.by_shop!.map((b) => `${shops.find((s) => s.id === b.shop_id)?.code ?? "?"} ${b.available}`).join(" · ")}
                          </p>
                        )}
                      </td>
                      <td className="p-3">
                        <div className="flex gap-2">
                          <button
                            type="button"
                            onClick={() => openEditVariantForm(variant)}
                            className="rounded-md border border-gray-300 px-3 py-2 hover:bg-gray-50"
                          >
                            Edit
                          </button>

                          {canDelete && (
                          <button
                            type="button"
                            onClick={() => void handleDeactivateVariant(variant)}
                            className="rounded-md border border-red-200 px-3 py-2 text-red-700 hover:bg-red-50"
                          >
                            Delete
                          </button>)}
                        </div>
                      </td>
                    </tr>
                  ))}

                  {variants.length === 0 && (
                    <tr>
                      <td colSpan={6} className="p-6 text-center text-gray-500">
                        No active variants found. Add a variant to manage size, color and stock.
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          )}
        </section>
      )}
      <p className="mt-4 text-xs text-gray-500">
        Products are loaded from the backend. Stock management is not connected
        yet.
      </p>
    </div>
  );
}
