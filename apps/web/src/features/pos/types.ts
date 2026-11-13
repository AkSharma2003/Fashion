export type PosItem = {
  variant_id: string; product_id: string; name: string; category: string; sku: string; size: string | null;
  color: string | null; codes: string[]; price_paise: number; mrp_paise: number | null; gst_rate_bp: number | null;
  fall_pico_eligible: boolean; on_hand: number;
};
export type KhataCustomer = { customer_id: string; account_id: string; name: string; phone: string; balance_paise: number;
  credit_limit_paise: number; offline_limit_paise: number };
export type Snapshot = {
  token: string; items: PosItem[]; khata_customers: KhataCustomer[];
  series: { prefix: string; next_number: number };
  rules: { fall_pico_limit_paise: number; discount_limit_percent: Record<string, number>; pos_mode: string;
    shop_name: string; shop_gstin: string };
  /** The shop this counter bills for (its name, GSTIN and address go on the bill). */
  shop?: { id: string; code: string; name: string; gstin: string | null; address: string | null; phone: string | null };
};
export type CartLine = { item: PosItem; qty: number; discount_paise: number; fall_pico: boolean };
export type Payment = { mode: "CASH" | "UPI" | "CARD" | "KHATA"; amount: number };
