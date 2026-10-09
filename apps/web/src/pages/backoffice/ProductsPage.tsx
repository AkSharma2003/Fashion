
import { useState } from "react";

type Product = {
  id: string;
  name: string;
  category: string;
  barcode: string;
  price: number;
  stock: number;
};

const initialProducts: Product[] = [
  {
    id: "PRD-001",
    name: "Silk Saree",
    category: "Sarees",
    barcode: "FOS-PRD-001",
    price: 2499,
    stock: 10,
  },
  {
    id: "PRD-002",
    name: "Anarkali Suit",
    category: "Suits",
    barcode: "FOS-PRD-002",
    price: 1899,
    stock: 8,
  },
  {
    id: "PRD-003",
    name: "Kids Kurta Set",
    category: "Kids",
    barcode: "FOS-PRD-003",
    price: 1299,
    stock: 15,
  },
];

export default function ProductsPage() {
  const [products, setProducts] = useState(initialProducts);
  const [search, setSearch] = useState("");
  const [newBarcode, setNewBarcode] = useState("");

  const filteredProducts = products.filter((product) =>
    `${product.name} ${product.barcode} ${product.category}`
      .toLowerCase()
      .includes(search.toLowerCase())
  );

  function updateBarcode(productId: string) {
    const code = newBarcode.trim();

    if (!code) return;

    const duplicate = products.some(
      (product) =>
        product.barcode.toLowerCase() === code.toLowerCase() &&
        product.id !== productId
    );

    if (duplicate) {
      alert("Ye barcode kisi doosre product ko assigned hai.");
      return;
    }

    setProducts((current) =>
      current.map((product) =>
        product.id === productId
          ? { ...product, barcode: code }
          : product
      )
    );

    setNewBarcode("");
  }

  return (
    <div className="min-h-screen bg-[#F7F7F7] p-4 text-[#111111] sm:p-6">
      <div className="mb-6">
        <p className="text-sm text-gray-500">Backoffice / Products</p>
        <h1 className="mt-1 text-2xl font-semibold">Products</h1>
        <p className="mt-1 text-sm text-gray-500">
          Product details and barcode management.
        </p>
      </div>

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
            {filteredProducts.map((product) => (
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
                    onClick={() => {
                      const code = window.prompt(
                        `Enter barcode for ${product.name}:`,
                        product.barcode
                      );

                      if (code !== null) {
                        setNewBarcode(code);
                        const value = code.trim();

                        if (!value) {
                          alert("Barcode empty nahi ho sakta.");
                          return;
                        }

                        const duplicate = products.some(
                          (item) =>
                            item.barcode.toLowerCase() ===
                              value.toLowerCase() &&
                            item.id !== product.id
                        );

                        if (duplicate) {
                          alert("Ye barcode kisi doosre product ko assigned hai.");
                          return;
                        }

                        setProducts((current) =>
                          current.map((item) =>
                            item.id === product.id
                              ? { ...item, barcode: value }
                              : item
                          )
                        );
                        setNewBarcode("");
                      }
                    }}
                    className="rounded-lg border border-gray-300 px-3 py-2 hover:bg-gray-50"
                  >
                    Edit Barcode
                  </button>
                </td>
              </tr>
            ))}

            {filteredProducts.length === 0 && (
              <tr>
                <td colSpan={6} className="p-8 text-center text-gray-500">
                  No products found.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      <p className="mt-4 text-xs text-gray-500">
        Demo data only. Products and barcode changes are not saved
        to a database yet.
      </p>
    </div>
  );
}
