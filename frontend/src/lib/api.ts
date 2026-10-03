// The ONLY place the frontend talks to the backend. One function per endpoint in docs/api/.
import type {
  AnalysisState,
  Citation,
  CitationDetail,
  Clarification,
  ContractDetail,
  ContractSummary,
  Dashboard,
  EntityType,
  ExtractedItem,
  Health,
  ItemDetail,
  Obligation,
  ObligationStatus,
  QueueItem,
  RecentReview,
  Renewal,
  ReviewEntry,
  Version,
  VersionChanges,
} from "./types";

const BASE = (import.meta.env.VITE_API_BASE_URL as string | undefined) ?? "http://localhost:8000/api";

/** Default per-request timeout. Uploads get longer; analysis itself runs in the background. */
export const TIMEOUT_MS = 30_000;
const UPLOAD_TIMEOUT_MS = 120_000;

export class ApiError extends Error {
  constructor(
    public code: string,
    message: string,
    public status: number,
    public details: unknown = null,
    /** Server request ID (X-Request-ID): matches the backend log line for this failure. */
    public requestId: string | null = null,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

async function request<T>(path: string, init?: RequestInit, timeoutMs = TIMEOUT_MS): Promise<T> {
  const method = init?.method ?? "GET";
  let res: Response;
  try {
    res = await fetch(`${BASE}${path}`, { ...init, signal: AbortSignal.timeout(timeoutMs) });
  } catch (e) {
    if (e instanceof DOMException && e.name === "TimeoutError") {
      console.warn(`[api] ${method} ${path} timed out after ${timeoutMs} ms`);
      throw new ApiError("TIMEOUT", "The server took too long to respond. Try again.", 0);
    }
    console.warn(`[api] ${method} ${path} network error`, e);
    throw new ApiError("NETWORK_ERROR", "Cannot reach the server. Is the backend running?", 0);
  }
  const body = res.status === 204 ? null : await res.json().catch(() => null);
  if (!res.ok) {
    const err = body?.error;
    const requestId = err?.request_id ?? res.headers.get("X-Request-ID");
    const error = new ApiError(
      err?.code ?? (res.status >= 500 ? "INTERNAL_ERROR" : "REQUEST_FAILED"),
      err?.message ?? `Request failed (${res.status})`,
      res.status,
      err?.details ?? null,
      requestId,
    );
    // 4xx are expected outcomes the UI handles; 5xx are bugs or outages worth a console trace.
    (res.status >= 500 ? console.error : console.warn)(`[api] ${method} ${path} -> ${res.status} ${error.code}`, {
      requestId,
      message: error.message,
    });
    throw error;
  }
  return body as T;
}

/** Message for any thrown value, for toasts and inline errors. */
export function errorMessage(e: unknown): string {
  if (e instanceof ApiError) return e.message;
  if (e instanceof Error) return e.message;
  return String(e);
}

function json(method: string, data: unknown): RequestInit {
  return { method, headers: { "Content-Type": "application/json" }, body: JSON.stringify(data) };
}

function qs(params: Record<string, string | number | boolean | null | undefined>): string {
  const p = new URLSearchParams();
  for (const [k, v] of Object.entries(params)) if (v !== undefined && v !== null && v !== "") p.set(k, String(v));
  const s = p.toString();
  return s ? `?${s}` : "";
}

type Items<T> = { items: T[] };

export const api = {
  health: () => request<Health>("/health"),
  dashboard: () => request<Dashboard>("/dashboard"),

  // contracts
  listContracts: (q: { search?: string; lifecycle_status?: string; needs_review?: boolean } = {}) =>
    request<Items<ContractSummary>>(`/contracts${qs(q)}`).then((r) => r.items),
  getContract: (id: string, versionId?: string) =>
    request<ContractDetail>(`/contracts/${id}${qs({ version_id: versionId })}`),
  extractedItems: (id: string, versionId?: string) =>
    request<Items<ExtractedItem>>(`/contracts/${id}/extracted-items${qs({ version_id: versionId })}`).then(
      (r) => r.items,
    ),
  uploadContract: (file: File, name?: string) => {
    const form = new FormData();
    form.append("file", file);
    if (name) form.append("name", name);
    return request<{ contract: ContractSummary; version: Version }>(
      "/contracts",
      { method: "POST", body: form },
      UPLOAD_TIMEOUT_MS,
    );
  },

  // analysis
  analyze: (id: string, versionId?: string) =>
    request<{ contract_id: string; version_id: string; analysis_status: string }>(
      `/contracts/${id}/analyze`,
      json("POST", versionId ? { version_id: versionId } : {}),
    ),
  analysis: (id: string, versionId?: string) =>
    request<AnalysisState>(`/contracts/${id}/analysis${qs({ version_id: versionId })}`),

  // versions
  versions: (id: string) => request<Items<Version>>(`/contracts/${id}/versions`).then((r) => r.items),
  uploadVersion: (id: string, file: File) => {
    const form = new FormData();
    form.append("file", file);
    return request<Version>(`/contracts/${id}/versions`, { method: "POST", body: form }, UPLOAD_TIMEOUT_MS);
  },
  versionChanges: (id: string, versionId: string) =>
    request<VersionChanges>(`/contracts/${id}/versions/${versionId}/changes`),

  // obligations & renewals
  obligations: (
    q: {
      contract_id?: string;
      version_id?: string;
      status?: string;
      review_status?: string;
      responsible_party?: string;
      due_before?: string;
    } = {},
  ) => request<Items<Obligation>>(`/obligations${qs(q)}`).then((r) => r.items),
  obligation: (id: string) => request<Obligation>(`/obligations/${id}`),
  setObligationStatus: (id: string, status: ObligationStatus) =>
    request<Obligation>(`/obligations/${id}`, json("PATCH", { status })),
  renewals: (q: { within_days?: number; calculation_status?: string } = {}) =>
    request<Items<Renewal>>(`/renewals${qs(q)}`).then((r) => r.items),

  // reviews
  reviewQueue: (q: { contract_id?: string; entity_type?: EntityType } = {}) =>
    request<Items<QueueItem>>(`/reviews/queue${qs(q)}`).then((r) => r.items),
  recentReviews: (limit = 10) => request<Items<RecentReview>>(`/reviews/recent${qs({ limit })}`).then((r) => r.items),
  review: (body: {
    entity_type: EntityType;
    entity_id: string;
    action: "approve" | "edit" | "reject";
    value?: unknown;
    note?: string;
  }) =>
    request<{ item: ExtractedItem | Obligation; review: ReviewEntry; renewal: Renewal | null }>(
      "/reviews",
      json("POST", body),
    ),
  item: (entityType: EntityType, entityId: string) => request<ItemDetail>(`/items/${entityType}/${entityId}`),
  reviewHistory: (entity_type: EntityType, entity_id: string) =>
    request<Items<ReviewEntry>>(`/reviews${qs({ entity_type, entity_id })}`).then((r) => r.items),

  // clarifications & citations
  clarifications: (q: { contract_id?: string; status?: "open" | "resolved" | "dismissed" } = {}) =>
    request<Items<Clarification>>(`/clarifications${qs(q)}`).then((r) => r.items),
  resolveClarification: (
    id: string,
    body: { action: "select" | "custom" | "dismiss"; entity_id?: string; value?: unknown; note?: string },
  ) =>
    request<{ clarification: Clarification; renewal: Renewal | null }>(
      `/clarifications/${id}/resolve`,
      json("POST", body),
    ),
  citation: (id: string) => request<CitationDetail>(`/citations/${id}`),
};

export type { Citation };
