import { act, renderHook, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { ApiError } from "./api";
import { useApi } from "./useApi";

describe("useApi", () => {
  it("loads data and exposes loading state", async () => {
    const { result } = renderHook(() => useApi(() => Promise.resolve([1, 2])));
    expect(result.current.loading).toBe(true);
    await waitFor(() => expect(result.current.data).toEqual([1, 2]));
    expect(result.current.loading).toBe(false);
    expect(result.current.error).toBeUndefined();
  });

  it("wraps non-API errors so the UI always gets an ApiError", async () => {
    const { result } = renderHook(() => useApi(() => Promise.reject(new Error("boom"))));
    await waitFor(() => expect(result.current.error).toBeInstanceOf(ApiError));
    expect(result.current.error?.code).toBe("INTERNAL_ERROR");
  });

  it("reload re-runs the loader and clears a previous error", async () => {
    const loader = vi
      .fn<() => Promise<string>>()
      .mockRejectedValueOnce(new ApiError("NETWORK_ERROR", "down", 0))
      .mockResolvedValueOnce("ok");
    const { result } = renderHook(() => useApi(loader));
    await waitFor(() => expect(result.current.error?.code).toBe("NETWORK_ERROR"));
    act(() => result.current.reload());
    await waitFor(() => expect(result.current.data).toBe("ok"));
    expect(result.current.error).toBeUndefined();
  });

  it("ignores a slow earlier response once the deps changed", async () => {
    let resolveFirst!: (v: string) => void;
    const first = new Promise<string>((r) => (resolveFirst = r));
    const { result, rerender } = renderHook(
      ({ id }) => useApi(() => (id === 1 ? first : Promise.resolve("second")), [id]),
      {
        initialProps: { id: 1 },
      },
    );
    rerender({ id: 2 });
    await waitFor(() => expect(result.current.data).toBe("second"));
    await act(async () => resolveFirst("first"));
    expect(result.current.data).toBe("second");
  });
});
