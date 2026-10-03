import { useCallback, useEffect, useRef, useState } from "react";
import { ApiError } from "./api";

/** Load data from the API. `deps` re-run the loader (like useEffect deps). */
export function useApi(loader, deps = []) {
  const [data, setData] = useState();
  const [error, setError] = useState();
  const [loading, setLoading] = useState(true);
  const [tick, setTick] = useState(0);
  const seq = useRef(0);

  useEffect(() => {
    const id = ++seq.current;
    setLoading(true);
    loader()
      .then((d) => {
        if (id === seq.current) {
          setData(d);
          setError(undefined);
        }
      })
      .catch(
        (e) => id === seq.current && setError(e instanceof ApiError ? e : new ApiError("INTERNAL_ERROR", String(e), 0)),
      )
      .finally(() => id === seq.current && setLoading(false));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [...deps, tick]);

  const reload = useCallback(() => setTick((t) => t + 1), []);
  return { data, error, loading, reload, setData };
}
