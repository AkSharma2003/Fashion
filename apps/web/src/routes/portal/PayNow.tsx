import { useParams } from "react-router-dom";

export default function PayNow() {
  const { token } = useParams();
  return (
    <main className="p-6">
      <h1 className="text-2xl font-semibold">Pay your dues</h1>
      <p className="mt-2 text-gray-600">Secure link for one khata customer. Token: {token}</p>
    </main>
  );
}
