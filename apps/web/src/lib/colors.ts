/** Fashion colour names used for variants, with a swatch colour for each. */
export const COLORS: { name: string; hex: string }[] = [
  { name: "Red", hex: "#C62828" }, { name: "Maroon", hex: "#7B1E2B" }, { name: "Wine", hex: "#5B1A33" },
  { name: "Rani Pink", hex: "#D81B7A" }, { name: "Pink", hex: "#F48FB1" }, { name: "Peach", hex: "#FFB59A" },
  { name: "Orange", hex: "#EF6C00" }, { name: "Rust", hex: "#A8441C" }, { name: "Mustard", hex: "#D4A017" },
  { name: "Yellow", hex: "#FBC02D" }, { name: "Lemon", hex: "#F3E66B" }, { name: "Green", hex: "#2E7D32" },
  { name: "Bottle Green", hex: "#0B4F2C" }, { name: "Parrot Green", hex: "#7CB342" }, { name: "Mint", hex: "#A5D6A7" },
  { name: "Teal", hex: "#00796B" }, { name: "Sky Blue", hex: "#81D4FA" }, { name: "Blue", hex: "#1565C0" },
  { name: "Royal Blue", hex: "#283FA8" }, { name: "Navy", hex: "#1A2A5A" }, { name: "Purple", hex: "#6A1B9A" },
  { name: "Lavender", hex: "#C3B1E1" }, { name: "Magenta", hex: "#B0006D" }, { name: "Black", hex: "#111111" },
  { name: "Grey", hex: "#8A8A8A" }, { name: "White", hex: "#FFFFFF" }, { name: "Off White", hex: "#F5F1E6" },
  { name: "Cream", hex: "#F3E5C0" }, { name: "Beige", hex: "#D8C3A5" }, { name: "Brown", hex: "#6D4C41" },
  { name: "Gold", hex: "#C9A227" }, { name: "Silver", hex: "#BFC4CA" }, { name: "Multicolour", hex: "multi" },
];

const BY_NAME = new Map(COLORS.map((c) => [c.name.toLowerCase(), c.hex]));
const MULTI = "conic-gradient(#C62828, #FBC02D, #2E7D32, #1565C0, #6A1B9A, #C62828)";

/** CSS background for a colour name: known palette colour, a valid CSS colour name, or a neutral fallback. */
export function swatchBackground(name: string | null | undefined): string {
  const key = (name ?? "").trim().toLowerCase();
  if (!key) return "#E5E7EB";
  const hex = BY_NAME.get(key);
  if (hex === "multi" || /multi|print/.test(key)) return MULTI;
  if (hex) return hex;
  if (typeof CSS !== "undefined" && CSS.supports("color", key)) return key;
  return "#E5E7EB";
}
