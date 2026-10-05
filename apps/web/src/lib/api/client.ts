const BASE = import.meta.env.VITE_API_URL ?? "";

export interface ApiResponse<T> {
  success: boolean;
  data: T | null;
  error: { code: string; message: string } | null;
}

export async function api<T>(path: string, init?: RequestInit): Promise<ApiResponse<T>> {
  const res = await fetch(`${BASE}/api/v1${path}`, {
    headers: { "Content-Type": "application/json" },
    ...init,
  });
  return res.json() as Promise<ApiResponse<T>>;
}
