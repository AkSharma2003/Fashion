import { useCallback, useEffect, useRef, useState } from "react";
import { errorMessage } from "../api/client";

/** Load data on mount (and when deps change); `reload` fetches again. */
export function useApi<T>(loader: () => Promise<T>, deps: unknown[] = []) {
  const [data, setData] = useState<T | null>(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  const loaderRef = useRef(loader);
  loaderRef.current = loader;

  const reload = useCallback(async () => {
    setLoading(true);
    try {
      setData(await loaderRef.current());
      setError("");
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void reload();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, deps);

  return { data, error, loading, reload, setData };
}

/** Wrap a form action: tracks busy state and the last error / success notice. */
export function useAction() {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");

  const run = useCallback(async <R,>(fn: () => Promise<R>, success?: string): Promise<R | undefined> => {
    setBusy(true);
    setError("");
    setNotice("");
    try {
      const result = await fn();
      if (success) setNotice(success);
      return result;
    } catch (err) {
      setError(errorMessage(err));
      return undefined;
    } finally {
      setBusy(false);
    }
  }, []);

  return { busy, error, notice, run, setError, setNotice };
}
