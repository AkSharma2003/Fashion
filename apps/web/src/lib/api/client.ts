import { getAccessToken } from "../auth/session";

const BASE = (import.meta.env.VITE_API_URL ?? "").replace(/\/$/, "");

export class ApiError extends Error {
  status: number;
  code?: string;

  constructor(message: string, status: number, code?: string) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.code = code;
  }
}

/** Calls the FastAPI API and returns its raw JSON response. Throws on non-2xx responses. */
export async function api<T>(path: string, init: RequestInit = {}): Promise<T> {
  const token = getAccessToken();
  const headers = new Headers(init.headers);

  if (!headers.has("Content-Type") && init.body !== undefined) {
    headers.set("Content-Type", "application/json");
  }
  if (token && !headers.has("Authorization")) {
    headers.set("Authorization", `Bearer ${token}`);
  }

  let response: Response;
  try {
    response = await fetch(`${BASE}/api/v1${path.startsWith("/") ? path : `/${path}`}`, {
      ...init,
      headers,
    });
  } catch {
    throw new ApiError("Could not connect to FashionOS API. Check that the backend is running.", 0);
  }

  const contentType = response.headers.get("content-type") ?? "";
  const payload: unknown = contentType.includes("application/json")
    ? await response.json().catch(() => null)
    : await response.text().catch(() => "");

  if (!response.ok) {
    const body = payload as { detail?: unknown; message?: unknown; code?: unknown } | null;
    const detail = typeof body?.detail === "string"
      ? body.detail
      : typeof body?.message === "string"
        ? body.message
        : `Request failed (${response.status})`;
    throw new ApiError(detail, response.status, typeof body?.code === "string" ? body.code : undefined);
  }

  return payload as T;
}


/** Upload a product image using multipart/form-data. */
export async function uploadProductImage<T>(
  productId: string,
  file: File,
): Promise<T> {
  const formData = new FormData();
  formData.append("file", file);

  return api<T>(
    `/catalog/${encodeURIComponent(productId)}/images`,
    {
      method: "POST",
      body: formData,
    },
  );
}


export type ProductImage = {
  id: string;
  product_id: string;
  object_key: string;
  image_url: string | null;
  original_filename: string;
  content_type: string;
  size_bytes: number;
  created_at: string;
};

/** Fetch all images belonging to a product. */
export async function getProductImages(
  productId: string,
): Promise<ProductImage[]> {
  return api<ProductImage[]>(
    `/catalog/${encodeURIComponent(productId)}/images`,
  );
}

export type Product = {
  id: string;
  name: string;
  description: string | null;
  sku: string;
  barcode: string | null;
  category: string;
  selling_price_paise: number;
  is_active: boolean;
};

/** Fetch active products from the backend. */
export async function getProducts(): Promise<Product[]> {
  return api<Product[]>("/catalog/");
}