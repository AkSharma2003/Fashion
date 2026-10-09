
const khataCustomers = [
  {
    name: "Demo Customer One",
    phone: "9999990001",
    outstanding: 4500,
  },
  {
    name: "Demo Customer Two",
    phone: "9999990002",
    outstanding: 2800,
  },
  {
    name: "Demo Customer Three",
    phone: "9999990003",
    outstanding: 0,
  },
];

export default function KhataPage() {
  const totalOutstanding = khataCustomers.reduce(
    (total, customer) => total + customer.outstanding,
    0,
  );

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
        <h2 className="mt-2 text-3xl font-semibold">
          ₹{totalOutstanding.toLocaleString("en-IN")}
        </h2>
        <p className="mt-2 text-xs text-gray-500">
          Sample data for UI testing only
        </p>
      </section>

      <section className="overflow-hidden rounded-lg border border-gray-200 bg-white">
        <div className="border-b border-gray-100 px-5 py-4">
          <h2 className="font-semibold">Customers</h2>
        </div>

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
              {khataCustomers.map((customer) => (
                <tr key={customer.phone} className="border-t border-gray-100">
                  <td className="px-5 py-4 font-medium">{customer.name}</td>
                  <td className="px-5 py-4 text-gray-600">{customer.phone}</td>
                  <td className="px-5 py-4 text-right font-semibold">
                    ₹{customer.outstanding.toLocaleString("en-IN")}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
    </main>
  );
}