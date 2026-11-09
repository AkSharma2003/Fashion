import { clearSession, getAccessToken, getRefreshToken, setAccessToken } from "../auth/session";

const BASE = (import.meta.env.VITE_API_URL ?? "").replace(/\/$/, "");

export class ApiError extends Error {
  status: number;
  code?: string;
  extra?: Record<string, unknown>;

  constructor(message: string, status: number, code?: string) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.code = code;
  }
}

let refreshing: Promise<boolean> | null = null;

async function tryRefresh(): Promise<boolean> {
  const refresh = getRefreshToken();
  if (!refresh) return false;
  refreshing ??= fetch(`${BASE}/api/v1/auth/refresh`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ refresh_token: refresh }),
  })
    .then(async (r) => {
      if (!r.ok) return false;
      const body = (await r.json()) as { access_token?: string };
      if (body.access_token) setAccessToken(body.access_token);
      return Boolean(body.access_token);
    })
    .catch(() => false)
    .finally(() => {
      refreshing = null;
    });
  return refreshing;
}

/** Calls the FastAPI API and returns its raw JSON response. Throws on non-2xx responses.
 *  A 401 with a stored refresh token is retried once after refreshing the access token. */
export async function api<T>(path: string, init: RequestInit = {}, retried = false): Promise<T> {
  const token = getAccessToken();
  const headers = new Headers(init.headers);

  if (
    !(init.body instanceof FormData) &&
    !headers.has("Content-Type") &&
    init.body !== undefined
  ) {
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
    throw new ApiError("Could not connect to WearVerse API. Check that the backend is running.", 0);
  }

  const contentType = response.headers.get("content-type") ?? "";
  const payload: unknown = contentType.includes("application/json")
    ? await response.json().catch(() => null)
    : await response.text().catch(() => "");

  if (response.status === 401 && !retried && token) {
    if (await tryRefresh()) return api<T>(path, init, true);
    clearSession();
  }

  if (!response.ok) {
    const body = payload as {
      detail?: unknown; message?: unknown; code?: unknown;
      error?: { code?: string; message?: string; [k: string]: unknown };
    } | null;
    const detail = typeof body?.error?.message === "string"
      ? body.error.message
      : typeof body?.detail === "string"
        ? body.detail
        : typeof body?.message === "string"
          ? body.message
          : `Request failed (${response.status})`;
    const code = body?.error?.code ?? (typeof body?.code === "string" ? body.code : undefined);
    const err = new ApiError(detail, response.status, code);
    err.extra = body?.error;
    throw err;
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


export type ProductCreateInput = {
  name: string;
  description?: string | null;
  sku: string;
  barcode?: string | null;
  category: string;
  selling_price_paise: number;
};

export type ProductUpdateInput = Partial<ProductCreateInput> & {
  is_active?: boolean;
};

/** Create a product. */
export async function createProduct(
  input: ProductCreateInput,
): Promise<Product> {
  return api<Product>("/catalog/", {
    method: "POST",
    body: JSON.stringify(input),
  });
}

/** Update selected product fields. */
export async function updateProduct(
  productId: string,
  input: ProductUpdateInput,
): Promise<Product> {
  return api<Product>(`/catalog/${encodeURIComponent(productId)}`, {
    method: "PATCH",
    body: JSON.stringify(input),
  });
}

/** Deactivate a product instead of permanently deleting it. */
export async function deleteProduct(
  productId: string,
): Promise<Product> {
  return api<Product>(`/catalog/${encodeURIComponent(productId)}`, {
    method: "DELETE",
  });
}

export type ProductVariant = {
  id: string;
  product_id: string;
  size: string;
  color: string;
  sku: string;
  selling_price_paise: number;
  stock_quantity: number;
  is_active: boolean;
};

/** Fetch active variants belonging to a product. */
export async function getProductVariants(
  productId: string,
): Promise<ProductVariant[]> {
  return api<ProductVariant[]>(
    `/catalog/${encodeURIComponent(productId)}/variants`,
  );
}


export type ProductVariantCreateInput = {
  size: string;
  color: string;
  sku: string;
  selling_price_paise: number;
  stock_quantity: number;
};

export type ProductVariantUpdateInput = {
  size?: string;
  color?: string;
  sku?: string;
  selling_price_paise?: number;
  stock_quantity?: number;
  is_active?: boolean;
};

/** Create a variant for a product. */
export async function createProductVariant(
  productId: string,
  input: ProductVariantCreateInput,
): Promise<ProductVariant> {
  return api<ProductVariant>(
    `/catalog/${encodeURIComponent(productId)}/variants`,
    {
      method: "POST",
      body: JSON.stringify(input),
    },
  );
}

/** Update an existing product variant. */
export async function updateProductVariant(
  productId: string,
  variantId: string,
  input: ProductVariantUpdateInput,
): Promise<ProductVariant> {
  return api<ProductVariant>(
    `/catalog/${encodeURIComponent(productId)}/variants/${encodeURIComponent(variantId)}`,
    {
      method: "PATCH",
      body: JSON.stringify(input),
    },
  );
}

/** Deactivate an existing product variant. */
export async function deactivateProductVariant(
  productId: string,
  variantId: string,
): Promise<ProductVariant> {
  return api<ProductVariant>(
    `/catalog/${encodeURIComponent(productId)}/variants/${encodeURIComponent(variantId)}`,
    {
      method: "DELETE",
    },
  );
}


/** New WearVerse endpoints answer {success, data, error}. This returns `data`. */
export async function apiData<T>(path: string, init: RequestInit = {}): Promise<T> {
  const body = await api<{ success: boolean; data: T }>(path, init);
  return body.data;
}

export function post<T>(path: string, body?: unknown): Promise<T> {
  return apiData<T>(path, { method: "POST", body: body === undefined ? undefined : JSON.stringify(body) });
}

export function patch<T>(path: string, body: unknown): Promise<T> {
  return apiData<T>(path, { method: "PATCH", body: JSON.stringify(body) });
}

export function errorMessage(err: unknown, fallback = "Something went wrong."): string {
  return err instanceof Error ? err.message : fallback;
}
