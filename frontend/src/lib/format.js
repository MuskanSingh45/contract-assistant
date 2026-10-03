const short = new Intl.DateTimeFormat("en-US", { month: "short", day: "numeric", year: "numeric", timeZone: "UTC" });
const long = new Intl.DateTimeFormat("en-US", { month: "long", day: "numeric", year: "numeric", timeZone: "UTC" });
const dateTime = new Intl.DateTimeFormat("en-US", {
  month: "short",
  day: "numeric",
  year: "numeric",
  hour: "2-digit",
  minute: "2-digit",
  hour12: false,
});

/** "Jan 31, 2025" from "2025-01-31" (or an ISO timestamp). */
export function fmtDate(value) {
  if (!value) return "—";
  return short.format(new Date(value.length === 10 ? `${value}T00:00:00Z` : value));
}

/** "January 31, 2025". */
export function fmtLongDate(value) {
  if (!value) return "—";
  return long.format(new Date(value.length === 10 ? `${value}T00:00:00Z` : value));
}

/** "Oct 3, 2026, 10:42" for timestamps. */
export function fmtDateTime(value) {
  return value ? dateTime.format(new Date(value)) : "—";
}

/** "in 30 days" / "today" / "2 days ago", from a days_until value returned by the API. */
export function fmtDaysUntil(days) {
  if (days === null || days === undefined) return "";
  if (days === 0) return "today";
  if (days === 1) return "tomorrow";
  if (days > 0) return `in ${days} days`;
  return days === -1 ? "1 day ago" : `${-days} days ago`;
}

/** "Section 8.2 · Page 14" (page omitted for DOCX). */
export function citationLabel(c) {
  const parts = [];
  if (c.section) parts.push(/^\d/.test(c.section) ? `Section ${c.section}` : c.section);
  if (c.page) parts.push(`Page ${c.page}`);
  return parts.join(" · ") || "Source";
}

export const confidenceLabel = {
  high: "High confidence",
  medium: "Medium confidence",
  low: "Low confidence",
};

export function plural(n, word) {
  return `${n} ${word}${n === 1 ? "" : "s"}`;
}

export function unitLabel(value, unit) {
  const u = unit.replace("_", " ").replace(/s$/, "");
  return `${value} ${u}${value === 1 ? "" : "s"}`;
}

/** Badge for an item's review status, letting an open clarification win. */
export function reviewStatusKind(status, opts = {}) {
  if (opts.conflict && status === "pending") return "conflict";
  return { pending: "needs_review", approved: "approved", edited: "edited", rejected: "rejected" }[status];
}
