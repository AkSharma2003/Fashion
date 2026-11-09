/** The web app is English only (owner's decision). Screens still call `t("...")`, which returns the text as is,
 *  so a second language can be added here later without touching every screen. */
export type Lang = "en";

try {
  localStorage.removeItem("wearverse.lang"); // forget a Hindi choice saved by an older version
} catch {
  // storage blocked: nothing to forget
}

export function useT() {
  const t = (text: string) => text;
  return { t, lang: "en" as Lang };
}
