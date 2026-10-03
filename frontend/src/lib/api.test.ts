import { afterEach, describe, expect, it, vi } from "vitest";
import { jsonResponse } from "@/test/render";
import { api, ApiError, errorMessage } from "./api";

function stubFetch(impl: (url: string, init?: RequestInit) => Promise<Response>) {
  const fetchMock = vi.fn(impl);
  vi.stubGlobal("fetch", fetchMock);
  return fetchMock;
}

async function caught(p: Promise<unknown>): Promise<ApiError> {
  try {
    await p;
  } catch (e) {
    return e as ApiError;
  }
  throw new Error("expected a rejection");
}

describe("api client", () => {
  afterEach(() => vi.restoreAllMocks());

  it("unwraps list responses and builds query strings without empty params", async () => {
    const fetchMock = stubFetch(async () => jsonResponse({ items: [{ id: "ctr_1" }] }));
    const items = await api.listContracts({ search: "acme", lifecycle_status: "", needs_review: true });
    expect(items).toEqual([{ id: "ctr_1" }]);
    expect(fetchMock.mock.calls[0][0]).toBe("http://localhost:8000/api/contracts?search=acme&needs_review=true");
  });

  it("sends JSON bodies with the right method and content type", async () => {
    const fetchMock = stubFetch(async () => jsonResponse({ id: "obl_1", status: "completed" }));
    await api.setObligationStatus("obl_1", "completed");
    const init = fetchMock.mock.calls[0][1]!;
    expect(init.method).toBe("PATCH");
    expect(new Headers(init.headers).get("Content-Type")).toBe("application/json");
    expect(JSON.parse(init.body as string)).toEqual({ status: "completed" });
  });

  it("maps the documented error body to ApiError, including the request ID", async () => {
    vi.spyOn(console, "warn").mockImplementation(() => {});
    stubFetch(async () =>
      jsonResponse(
        { error: { code: "CONTRACT_NOT_FOUND", message: "Contract not found", details: null, request_id: "req_abc" } },
        404,
      ),
    );
    const e = await caught(api.getContract("nope"));
    expect(e).toBeInstanceOf(ApiError);
    expect(e).toMatchObject({
      code: "CONTRACT_NOT_FOUND",
      status: 404,
      message: "Contract not found",
      requestId: "req_abc",
    });
  });

  it("falls back to the X-Request-ID header and a generic code when the body is not JSON", async () => {
    const error = vi.spyOn(console, "error").mockImplementation(() => {});
    stubFetch(
      async () => new Response("<html>Bad gateway</html>", { status: 502, headers: { "X-Request-ID": "req_hdr" } }),
    );
    const e = await caught(api.dashboard());
    expect(e).toMatchObject({ code: "INTERNAL_ERROR", status: 502, requestId: "req_hdr" });
    expect(e.message).toBe("Request failed (502)");
    expect(error).toHaveBeenCalledOnce(); // 5xx are logged as errors for debugging
  });

  it("keeps validation details for forms", async () => {
    vi.spyOn(console, "warn").mockImplementation(() => {});
    const details = { fields: [{ field: "value.date", problem: "not a valid date" }] };
    stubFetch(async () =>
      jsonResponse({ error: { code: "VALIDATION_ERROR", message: "Request is invalid", details } }, 422),
    );
    const e = await caught(
      api.review({ entity_type: "extracted_item", entity_id: "itm_1", action: "edit", value: {} }),
    );
    expect(e.details).toEqual(details);
  });

  it("reports an unreachable backend as NETWORK_ERROR", async () => {
    vi.spyOn(console, "warn").mockImplementation(() => {});
    stubFetch(async () => {
      throw new TypeError("Failed to fetch");
    });
    const e = await caught(api.health());
    expect(e).toMatchObject({ code: "NETWORK_ERROR", status: 0 });
    expect(e.message).toMatch(/backend running/);
  });

  it("reports a request that exceeds the timeout as TIMEOUT", async () => {
    vi.spyOn(console, "warn").mockImplementation(() => {});
    stubFetch(async () => {
      throw new DOMException("signal timed out", "TimeoutError");
    });
    expect(await caught(api.dashboard())).toMatchObject({ code: "TIMEOUT" });
  });

  it("passes an abort signal so hung requests end", async () => {
    const fetchMock = stubFetch(async () => jsonResponse({ status: "ok" }));
    await api.health();
    expect(fetchMock.mock.calls[0][1]?.signal).toBeInstanceOf(AbortSignal);
  });

  it("uploads as multipart without forcing a content type", async () => {
    const fetchMock = stubFetch(async () => jsonResponse({ contract: { id: "ctr_1" }, version: { id: "ver_1" } }, 201));
    await api.uploadContract(new File(["%PDF"], "a.pdf", { type: "application/pdf" }), "Acme");
    const init = fetchMock.mock.calls[0][1]!;
    const form = init.body as FormData;
    expect(form.get("name")).toBe("Acme");
    expect((form.get("file") as File).name).toBe("a.pdf");
    expect(init.headers).toBeUndefined();
  });
});

describe("errorMessage", () => {
  it("never shows the error class name to users", () => {
    expect(errorMessage(new ApiError("X", "Readable message", 400))).toBe("Readable message");
    expect(errorMessage(new Error("plain"))).toBe("plain");
    expect(errorMessage("text")).toBe("text");
  });
});
