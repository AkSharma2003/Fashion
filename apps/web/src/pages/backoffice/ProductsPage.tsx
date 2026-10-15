
import { useCallback, useEffect, useState } from "react";
import {
  createProduct,
  deleteProduct,
  getProducts,
  updateProduct,
  uploadProductImage,
  type Product,
  type ProductCreateInput,
} from "../../lib/api/client";

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
};

const MAX_IMAGES = 5;

const emptyForm: ProductCreateInput = {
  name: "",
  description: "",
  sku: "",
  barcode: "",
  category: "",
  selling_price_paise: 0,
};

function toDisplayProduct(product: Product): DisplayProduct {
  return {
    id: product.id,
    name: product.name,
    category: product.category,
    barcode: product.barcode ?? "—",
    sku: product.sku,
    price: product.selling_price_paise / 100,
    stock: "—",
    description: product.description ?? "",
    isActive: product.is_active,
  };
}

export default function ProductsPage() {
  const [products, setProducts] = useState<DisplayProduct[]>([]);
  const [search, setSearch] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [saving, setSaving] = useState(false);

  const [formOpen, setFormOpen] = useState(false);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [form, setForm] = useState<ProductCreateInput>(emptyForm);
  const [imageFiles, setImageFiles] = useState<File[]>([]);
  const [previewUrls, setPreviewUrls] = useState<string[]>([]);

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

      const data = await getProducts();
      setProducts(data.map(toDisplayProduct));
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Unable to load products."
      );
    } finally {
      setLoading(false);
    }
  }, []);

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
          : value,
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

      const input: ProductCreateInput = {
        name: form.name.trim(),
        description: form.description?.trim() || null,
        sku: form.sku.trim(),
        barcode: form.barcode?.trim() || null,
        category: form.category.trim(),
        selling_price_paise: form.selling_price_paise,
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

  async function handleDeactivate(product: DisplayProduct) {
    const confirmed = window.confirm(
      `Deactivate "${product.name}"?`
    );

    if (!confirmed) return;

    setError("");
    setNotice("");

    try {
      await deleteProduct(product.id);
      setNotice("Product deactivated successfully.");
      await loadProducts();
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "Failed to deactivate product."
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
                className="min-h-11 w-full rounded-lg border border-gray-300 px-3 text-sm outline-none focus:border-black"
                placeholder="e.g. Sarees"
              />
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
      </div>

      <div className="overflow-x-auto rounded-xl border border-gray-200 bg-white">
        <table className="w-full min-w-[850px] text-left text-sm">
          <thead className="border-b border-gray-200 bg-gray-50">
            <tr>
              <th className="p-4">Product</th>
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
                    <p className="font-medium">{product.name}</p>
                    <p className="mt-1 text-xs text-gray-500">
                      SKU: {product.sku}
                    </p>
                    <p className="mt-1 text-xs text-gray-500">{product.id}</p>
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
                  <td className="p-4">{product.stock}</td>
                  <td className="p-4">
                    <span
                      className={`rounded-full px-2 py-1 text-xs ${
                        product.isActive
                          ? "bg-green-100 text-green-800"
                          : "bg-gray-100 text-gray-600"
                      }`}
                    >
                      {product.isActive ? "Active" : "Inactive"}
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
                      {product.isActive && (
                        <button
                          type="button"
                          onClick={() => void handleDeactivate(product)}
                          className="rounded-lg border border-red-200 px-3 py-2 text-red-700 hover:bg-red-50"
                        >
                          Deactivate
                        </button>
                      )}
                    </div>
                  </td>
                </tr>
              ))}

            {!loading && !error && filteredProducts.length === 0 && (
              <tr>
                <td colSpan={7} className="p-8 text-center text-gray-500">
                  No products found.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      <p className="mt-4 text-xs text-gray-500">
        Products are loaded from the backend. Stock management is not connected
        yet.
      </p>
    </div>
  );
}
