/** Tiny IndexedDB store for the POS (SRS 5.2): catalog snapshot, bill queue, settings.
 *  Falls back to memory if IndexedDB is blocked, so billing never stops (it just won't survive a reload). */

const DB_NAME = "wearverse-pos";
const VERSION = 1;
const memory: Record<string, Map<string, unknown>> = { kv: new Map(), queue: new Map() };
let dbPromise: Promise<IDBDatabase | null> | null = null;

function open(): Promise<IDBDatabase | null> {
  dbPromise ??= new Promise((resolve) => {
    try {
      const req = indexedDB.open(DB_NAME, VERSION);
      req.onupgradeneeded = () => {
        const db = req.result;
        if (!db.objectStoreNames.contains("kv")) db.createObjectStore("kv");
        if (!db.objectStoreNames.contains("queue")) db.createObjectStore("queue");
      };
      req.onsuccess = () => resolve(req.result);
      req.onerror = () => resolve(null);
    } catch {
      resolve(null);
    }
  });
  return dbPromise;
}

async function tx<T>(store: "kv" | "queue", mode: IDBTransactionMode, fn: (s: IDBObjectStore) => IDBRequest<T>): Promise<T | undefined> {
  const db = await open();
  if (!db) return undefined;
  return new Promise((resolve, reject) => {
    const t = db.transaction(store, mode);
    const req = fn(t.objectStore(store));
    req.onsuccess = () => resolve(req.result);
    req.onerror = () => reject(req.error);
  });
}

export async function kvGet<T>(key: string): Promise<T | undefined> {
  const db = await open();
  if (!db) return memory.kv.get(key) as T | undefined;
  return tx<T>("kv", "readonly", (s) => s.get(key) as IDBRequest<T>);
}

export async function kvSet(key: string, value: unknown): Promise<void> {
  const db = await open();
  if (!db) { memory.kv.set(key, value); return; }
  await tx("kv", "readwrite", (s) => s.put(value, key));
}

export type QueuedBill = {
  key: string;                 // bill number = idempotency key
  body: Record<string, unknown>;
  createdAt: string;
  status: "queued" | "failed";
  error?: string;
  code?: string;
  summary: { total_paise: number; customer?: string; lines: number };
};

export async function queueAll(): Promise<QueuedBill[]> {
  const db = await open();
  const rows = db ? ((await tx<QueuedBill[]>("queue", "readonly", (s) => s.getAll() as IDBRequest<QueuedBill[]>)) ?? [])
    : [...memory.queue.values()] as QueuedBill[];
  return rows.sort((a, b) => a.createdAt.localeCompare(b.createdAt));
}

export async function queuePut(bill: QueuedBill): Promise<void> {
  const db = await open();
  if (!db) { memory.queue.set(bill.key, bill); return; }
  await tx("queue", "readwrite", (s) => s.put(bill, bill.key));
}

export async function queueDelete(key: string): Promise<void> {
  const db = await open();
  if (!db) { memory.queue.delete(key); return; }
  await tx("queue", "readwrite", (s) => s.delete(key));
}
