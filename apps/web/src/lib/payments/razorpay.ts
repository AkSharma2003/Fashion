/** Opens Razorpay Checkout. The browser result is only a hint; the order/ledger is updated by the webhook. */
declare global {
  interface Window { Razorpay?: new (options: Record<string, unknown>) => { open: () => void } }
}

let loading: Promise<void> | null = null;

function loadScript(): Promise<void> {
  loading ??= new Promise((resolve, reject) => {
    if (window.Razorpay) return resolve();
    const s = document.createElement("script");
    s.src = "https://checkout.razorpay.com/v1/checkout.js";
    s.onload = () => resolve();
    s.onerror = () => { loading = null; reject(new Error("Could not load the payment window. Check the internet.")); };
    document.body.appendChild(s);
  });
  return loading;
}

export async function openRazorpay(opts: { keyId: string; orderId: string; amountPaise: number; name: string;
  description: string; prefill?: Record<string, string>; onDone: () => void; onDismiss?: () => void }): Promise<void> {
  await loadScript();
  const rz = new window.Razorpay!({
    key: opts.keyId, order_id: opts.orderId, amount: opts.amountPaise, currency: "INR", name: opts.name,
    description: opts.description, prefill: opts.prefill ?? {}, theme: { color: "#5b2333" },
    handler: () => opts.onDone(), modal: { ondismiss: () => opts.onDismiss?.() },
  });
  rz.open();
}
