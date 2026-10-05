/** Money is always an integer number of paise. 149900 means INR 1,499.00 */
export type Paise = number;

export type CustomerType = "online" | "walk_in" | "khata";

export type OrderStatus =
  | "PENDING_PAYMENT" | "PLACED" | "CONFIRMED" | "FALL_PICO_IN_PROGRESS" | "PACKED"
  | "SHIPPED" | "OUT_FOR_DELIVERY" | "DELIVERED" | "CANCELLED"
  | "RETURN_REQUESTED" | "RETURN_PICKED" | "RETURNED" | "REFUNDED";

export type FallPicoStatus =
  | "PENDING" | "ASSIGNED" | "IN_PROGRESS" | "COMPLETED" | "QC_PASSED"
  | "READY" | "HANDED_OVER" | "REWORK" | "CANCELLED";

export type LedgerEntryType = "SALE" | "PAYMENT" | "RETURN" | "ADJUSTMENT" | "WRITE_OFF" | "REVERSAL";

export interface ApiResponse<T> {
  success: boolean;
  data: T | null;
  error: { code: string; message: string } | null;
}
