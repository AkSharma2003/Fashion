import type { ReactNode } from "react";

/** Put app-wide providers here later (auth, data fetching, language). */
export function Providers({ children }: { children: ReactNode }) {
  return <>{children}</>;
}
