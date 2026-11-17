import { useCallback, useEffect, useRef, useState } from "react";

/** Loads data with explicit loading/error states and a reload function. */
export function useResource<T>(loader: () => Promise<T>, deps: unknown[]) {
  const [data, setData] = useState<T | null>(null);
  const [error, setError] = useState<unknown>(null);
  const [loading, setLoading] = useState(true);
  const loaderRef = useRef(loader);
  loaderRef.current = loader;

  const reload = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const value = await loaderRef.current();
      setData(value);
      return value;
    } catch (err) {
      setError(err);
      return null;
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void reload();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, deps);

  return { data, setData, error, loading, reload };
}

/** Runs a mutation and tracks its busy/error state. */
export function useAction() {
  const [busy, setBusy] = useState<string | null>(null);
  const [error, setError] = useState<unknown>(null);
  const run = useCallback(async <T,>(key: string, fn: () => Promise<T>): Promise<T | null> => {
    setBusy(key);
    setError(null);
    try {
      return await fn();
    } catch (err) {
      setError(err);
      return null;
    } finally {
      setBusy(null);
    }
  }, []);
  return { busy, error, setError, run };
}
