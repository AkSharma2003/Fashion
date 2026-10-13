import { useEffect, useState } from "react";
import { api, ApiError } from "../../lib/api/client";

interface Customer {
  id: string;
  full_name: string;
  phone_number: string;
  is_active: boolean;
}

export default function KhataPage() {
  const [customers, setCustomers] = useState<Customer[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    let cancelled = false;

    async function loadCustomers() {
      try {
        const data = await api<Customer[]>("/customers/customers");
        if (!cancelled) {
          setCustomers(data);
          setError("");
        }
      } catch (err) {
        if (!cancelled) {
          setError(
            err instanceof ApiError
              ? err.message
              : "Customers could not be loaded.",
          );
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    }

    void loadCustomers();

    return () => {
      cancelled = true;
    };
  }, []);

  return (
    <main className="min-h-screen bg-[#F7F7F7] p-5 text-[#111111] md:p-8">
      <header className="mb-8">
        <p className="text-sm text-gray-500">Backoffice / Khata</p>
        <h1 className="mt-2 text-3xl font-semibold">Customer Khata</h1>
        <p className="mt-2 text-sm text-gray-500">
          Manage customer outstanding balances.
        </p>
      </header>

      <section className="mb-6 rounded-lg border border-gray-200 bg-white p-6">
        <p className="text-sm text-gray-500">Total outstanding</p>
        <h2 className="mt-2 text-3xl font-semibold">—</h2>
        <p className="mt-2 text-xs text-gray-500">
          Balance data is not yet available from the backend.
        </p>
      </section>

      <section className="overflow-hidden rounded-lg border border-gray-200 bg-white">
        <div className="border-b border-gray-100 px-5 py-4">
          <h2 className="font-semibold">Customers</h2>
        </div>

        {loading && (
          <p className="px-5 py-6 text-sm text-gray-500">
            Loading customers...
          </p>
        )}

        {!loading && error && (
          <div className="px-5 py-6">
            <p className="text-sm text-red-600">{error}</p>
            <button
              type="button"
              onClick={() => window.location.reload()}
              className="mt-3 rounded border border-gray-300 px-4 py-2 text-sm"
            >
              Retry
            </button>
          </div>
        )}

        {!loading && !error && customers.length === 0 && (
          <p className="px-5 py-6 text-sm text-gray-500">
            No active customers found.
          </p>
        )}

        {!loading && !error && customers.length > 0 && (
          <div className="overflow-x-auto">
            <table className="w-full min-w-[520px] text-left text-sm">
              <thead className="bg-[#F7F7F7] text-gray-500">
                <tr>
                  <th className="px-5 py-4 font-medium">Customer</th>
                  <th className="px-5 py-4 font-medium">Phone</th>
                  <th className="px-5 py-4 text-right font-medium">
                    Outstanding
                  </th>
                </tr>
              </thead>
              <tbody>
                {customers.map((customer) => (
                  <tr key={customer.id} className="border-t border-gray-100">
                    <td className="px-5 py-4 font-medium">
                      {customer.full_name}
                    </td>
                    <td className="px-5 py-4 text-gray-600">
                      {customer.phone_number}
                    </td>
                    <td className="px-5 py-4 text-right text-gray-500">
                      Not available
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </main>
  );
}
