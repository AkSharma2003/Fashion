
import { useEffect, useState } from "react";
import { getProducts } from "../../lib/api/client";

type DisplayProduct = {
  id: string;
  name: string;
  category: string;
  barcode: string;
  price: number;
  stock: string;
};

export default function ProductsPage() {
  const [products, setProducts] = useState<DisplayProduct[]>([]);
  const [search, setSearch] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    async function loadProducts() {
      try {
        setLoading(true);
        setError("");

        const data = await getProducts();

        setProducts(
          data.map((product) => ({
            id: product.id,
            name: product.name,
            category: product.category,
            barcode: product.barcode ?? "—",
            price: product.selling_price_paise / 100,
            stock: "—",
          }))
        );
      } catch (err) {
        setError(
          err instanceof Error
            ? err.message
            : "Products load nahi ho paye."
        );
      } finally {
        setLoading(false);
      }
    }

    void loadProducts();
  }, []);

  const filteredProducts = products.filter((product) =>
    `${product.name} ${product.barcode} ${product.category}`
      .toLowerCase()
      .includes(search.toLowerCase())
  );

  return (
    <div className="min-h-screen bg-[#F7F7F7] p-4 text-[#111111] sm:p-6">
      <div className="mb-6">
        <p className="text-sm text-gray-500">Backoffice / Products</p>
        <h1 className="mt-1 text-2xl font-semibold">Products</h1>
        <p className="mt-1 text-sm text-gray-500">
          Product details and barcode management.
        </p>
      </div>

      {loading && (
        <p className="mb-4 text-sm text-gray-500">
          Products load ho rahe hain...
        </p>
      )}

      {error && (
        <div className="mb-4 rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-700">
          {error}
        </div>
      )}

      <div className="mb-5 rounded-xl border border-gray-200 bg-white p-4">
        <label
          htmlFor="product-search"
          className="mb-2 block text-sm font-medium"
        >
          Search products
        </label>

        <input
          id="product-search"
          value={search}
          onChange={(event) => setSearch(event.target.value)}
          placeholder="Search by name, category or barcode..."
          className="min-h-11 w-full rounded-lg border border-gray-300 px-3 text-sm outline-none focus:border-[#111111]"
        />
      </div>

      <div className="overflow-x-auto rounded-xl border border-gray-200 bg-white">
        <table className="w-full min-w-[700px] text-left text-sm">
          <thead className="border-b border-gray-200 bg-gray-50">
            <tr>
              <th className="p-4">Product</th>
              <th className="p-4">Category</th>
              <th className="p-4">Barcode</th>
              <th className="p-4">Price</th>
              <th className="p-4">Stock</th>
              <th className="p-4">Action</th>
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
                      {product.id}
                    </p>
                  </td>

                  <td className="p-4">{product.category}</td>

                  <td className="p-4 font-mono text-xs">
                    {product.barcode}
                  </td>

                  <td className="p-4">
                    ₹{product.price.toLocaleString("en-IN")}
                  </td>

                  <td className="p-4">{product.stock}</td>

                  <td className="p-4">
                    <button
                      type="button"
                      onClick={() => {
                        alert(
                          "Barcode update ko database API se connect karna abhi baaki hai."
                        );
                      }}
                      className="rounded-lg border border-gray-300 px-3 py-2 hover:bg-gray-50"
                    >
                      Edit Barcode
                    </button>
                  </td>
                </tr>
              ))}

            {!loading &&
              !error &&
              filteredProducts.length === 0 && (
                <tr>
                  <td
                    colSpan={6}
                    className="p-8 text-center text-gray-500"
                  >
                    No products found.
                  </td>
                </tr>
              )}
          </tbody>
        </table>
      </div>

      <p className="mt-4 text-xs text-gray-500">
        Products are loaded from the backend. Stock information and
        barcode updates are not connected yet.
      </p>
    </div>
  );
}