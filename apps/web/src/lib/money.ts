/** Money is an integer number of paise: 149900 means INR 1,499.00 */
export function formatINR(paise: number): string {
  return new Intl.NumberFormat("en-IN", { style: "currency", currency: "INR" }).format(paise / 100);
}
