import { useCallback, useEffect, useRef, useState } from "react";
import { ApiError, apiData } from "../../lib/api/client";
import { kvGet, kvSet, queueAll, queueDelete, queuePut, type QueuedBill } from "../../lib/offline/db";
import type { Snapshot } from "./types";

const PUSH_EVERY_MS = 5000;
const PULL_EVERY_MS = 60000;

/** Offline-first sync (SRS 5.2): send queued bills in order, then pull the latest snapshot.
 *  A bill the server rejects for a business reason stays in the queue, marked failed, for the cashier. */
export function usePosSync(counterId: string) {
  const [snapshot, setSnapshot] = useState<Snapshot | null>(null);
  const [queue, setQueue] = useState<QueuedBill[]>([]);
  const [online, setOnline] = useState(navigator.onLine);
  const [lastSync, setLastSync] = useState<string | null>(null);
  const [syncError, setSyncError] = useState("");
  const busy = useRef(false);
  const lastPull = useRef(0);

  const refreshQueue = useCallback(async () => setQueue(await queueAll()), []);

  const pull = useCallback(async () => {
    const snap = await apiData<Snapshot>(`/pos/sync?counter_id=${counterId}`);
    // Never move the local bill counter backwards (bills may be waiting offline).
    const localNext = (await kvGet<number>(`next:${counterId}`)) ?? 0;
    if (snap.series.next_number > localNext) await kvSet(`next:${counterId}`, snap.series.next_number);
    await kvSet("snapshot", snap);
    setSnapshot(snap);
    setLastSync(snap.token);
    lastPull.current = Date.now();
  }, [counterId]);

  const cycle = useCallback(async (forcePull = false) => {
    if (busy.current) return;
    busy.current = true;
    try {
      for (const bill of await queueAll()) {
        if (bill.status === "failed") continue;
        try {
          await apiData("/pos/bills", { method: "POST", body: JSON.stringify(bill.body) });
          await queueDelete(bill.key);
        } catch (err) {
          if (err instanceof ApiError && err.status >= 400 && err.status < 500 && err.status !== 401 && err.status !== 429) {
            await queuePut({ ...bill, status: "failed", error: err.message, code: err.code });
            continue;
          }
          throw err; // offline / server down: stop and keep order
        }
      }
      if (forcePull || Date.now() - lastPull.current > PULL_EVERY_MS) await pull();
      setOnline(true);
      setSyncError("");
    } catch (err) {
      setOnline(false);
      setSyncError(err instanceof Error ? err.message : "offline");
    } finally {
      busy.current = false;
      await refreshQueue();
    }
  }, [pull, refreshQueue]);

  useEffect(() => {
    void (async () => {
      const cached = await kvGet<Snapshot>("snapshot");
      if (cached) { setSnapshot(cached); setLastSync(cached.token); }
      await refreshQueue();
      await cycle(true);
    })();
    const timer = window.setInterval(() => void cycle(), PUSH_EVERY_MS);
    const goOnline = () => void cycle(true);
    const goOffline = () => setOnline(false);
    window.addEventListener("online", goOnline);
    window.addEventListener("offline", goOffline);
    return () => {
      window.clearInterval(timer);
      window.removeEventListener("online", goOnline);
      window.removeEventListener("offline", goOffline);
    };
  }, [cycle, refreshQueue]);

  /** Next bill number for this counter, e.g. C1-26-000124. Stored locally so offline bills stay unique. */
  const nextBillNo = useCallback(async () => {
    const prefix = snapshot?.series.prefix ?? `${counterId}-`;
    const n = Math.max((await kvGet<number>(`next:${counterId}`)) ?? 1, snapshot?.series.next_number ?? 1);
    await kvSet(`next:${counterId}`, n + 1);
    return `${prefix}${String(n).padStart(6, "0")}`;
  }, [snapshot, counterId]);

  const enqueue = useCallback(async (bill: QueuedBill) => {
    await queuePut(bill);
    await refreshQueue();
    void cycle();
  }, [cycle, refreshQueue]);

  const retry = useCallback(async (bill: QueuedBill, patchBody?: Record<string, unknown>) => {
    await queuePut({ ...bill, status: "queued", error: undefined, code: undefined, body: { ...bill.body, ...patchBody } });
    await cycle();
  }, [cycle]);

  const discard = useCallback(async (bill: QueuedBill) => {
    await queueDelete(bill.key);
    await refreshQueue();
  }, [refreshQueue]);

  return { snapshot, queue, online, lastSync, syncError, enqueue, retry, discard, nextBillNo, syncNow: () => cycle(true) };
}
