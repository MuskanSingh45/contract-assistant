const BASE = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000/api";

const WORKSPACE_KEY = "contract-assistant.workspace";
let memoryWorkspace = null; // used when localStorage is unavailable (private mode, blocked storage)

function newWorkspaceId() {
  const random = globalThis.crypto?.randomUUID?.() ?? `${Date.now()}-${Math.random()}`;
  return `ws_${random.replace(/[^A-Za-z0-9]/g, "")}`;
}

/**
 * This browser's private workspace ID, sent as X-Workspace-ID on every request. On the public
 * deployment the backend keeps a separate database per workspace, so one visitor's uploads and
 * reviews are never visible to another. Locally the backend ignores it.
 */
export function workspaceId() {
  try {
    let id = localStorage.getItem(WORKSPACE_KEY);
    if (!id) {
      id = newWorkspaceId();
      localStorage.setItem(WORKSPACE_KEY, id);
    }
    return id;
  } catch {
    memoryWorkspace ??= newWorkspaceId();
    return memoryWorkspace;
  }
}

/** Forget this browser's workspace; the next request starts a fresh one with the demo data. */
export function resetWorkspace() {
  memoryWorkspace = null;
  try {
    localStorage.removeItem(WORKSPACE_KEY);
  } catch {
    /* storage unavailable: the in-memory ID was already cleared */
  }
}

/** Default per-request timeout. Uploads get longer; analysis itself runs in the background. */
export const TIMEOUT_MS = 30_000;
const UPLOAD_TIMEOUT_MS = 120_000;

export class ApiError extends Error {
  constructor(
    code,
    message,
    status,
    details = null,
    /** Server request ID (X-Request-ID): matches the backend log line for this failure. */
    requestId = null,
  ) {
    super(message);
    this.code = code;
    this.status = status;
    this.details = details;
    this.requestId = requestId;
    this.name = "ApiError";
  }
}

async function request(path, init, timeoutMs = TIMEOUT_MS) {
  const method = init?.method ?? "GET";
  let res;
  try {
    const headers = new Headers(init?.headers);
    headers.set("X-Workspace-ID", workspaceId());
    res = await fetch(`${BASE}${path}`, { ...init, headers, signal: AbortSignal.timeout(timeoutMs) });
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
  return body;
}

/** Message for any thrown value, for toasts and inline errors. */
export function errorMessage(e) {
  if (e instanceof ApiError) return e.message;
  if (e instanceof Error) return e.message;
  return String(e);
}

function json(method, data) {
  return { method, headers: { "Content-Type": "application/json" }, body: JSON.stringify(data) };
}

function qs(params) {
  const p = new URLSearchParams();
  for (const [k, v] of Object.entries(params)) if (v !== undefined && v !== null && v !== "") p.set(k, String(v));
  const s = p.toString();
  return s ? `?${s}` : "";
}

export const api = {
  health: () => request("/health"),
  dashboard: () => request("/dashboard"),

  // contracts
  listContracts: (q = {}) => request(`/contracts${qs(q)}`).then((r) => r.items),
  getContract: (id, versionId) => request(`/contracts/${id}${qs({ version_id: versionId })}`),
  extractedItems: (id, versionId) =>
    request(`/contracts/${id}/extracted-items${qs({ version_id: versionId })}`).then((r) => r.items),
  uploadContract: (file, name) => {
    const form = new FormData();
    form.append("file", file);
    if (name) form.append("name", name);
    return request("/contracts", { method: "POST", body: form }, UPLOAD_TIMEOUT_MS);
  },

  // analysis
  analyze: (id, versionId) =>
    request(`/contracts/${id}/analyze`, json("POST", versionId ? { version_id: versionId } : {})),
  analysis: (id, versionId) => request(`/contracts/${id}/analysis${qs({ version_id: versionId })}`),

  // versions
  versions: (id) => request(`/contracts/${id}/versions`).then((r) => r.items),
  uploadVersion: (id, file) => {
    const form = new FormData();
    form.append("file", file);
    return request(`/contracts/${id}/versions`, { method: "POST", body: form }, UPLOAD_TIMEOUT_MS);
  },
  versionChanges: (id, versionId) => request(`/contracts/${id}/versions/${versionId}/changes`),

  // obligations & renewals
  obligations: (q = {}) => request(`/obligations${qs(q)}`).then((r) => r.items),
  obligation: (id) => request(`/obligations/${id}`),
  setObligationStatus: (id, status) => request(`/obligations/${id}`, json("PATCH", { status })),
  renewals: (q = {}) => request(`/renewals${qs(q)}`).then((r) => r.items),

  // reviews
  reviewQueue: (q = {}) => request(`/reviews/queue${qs(q)}`).then((r) => r.items),
  recentReviews: (limit = 10) => request(`/reviews/recent${qs({ limit })}`).then((r) => r.items),
  review: (body) => request("/reviews", json("POST", body)),
  item: (entityType, entityId) => request(`/items/${entityType}/${entityId}`),
  reviewHistory: (entity_type, entity_id) => request(`/reviews${qs({ entity_type, entity_id })}`).then((r) => r.items),

  // clarifications & citations
  clarifications: (q = {}) => request(`/clarifications${qs(q)}`).then((r) => r.items),
  resolveClarification: (id, body) => request(`/clarifications/${id}/resolve`, json("POST", body)),
  citation: (id) => request(`/citations/${id}`),
};
