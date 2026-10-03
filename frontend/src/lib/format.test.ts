import { describe, expect, it } from "vitest";
import { citationLabel, fmtDate, fmtDaysUntil, fmtLongDate, plural, reviewStatusKind, unitLabel } from "./format";

describe("format", () => {
  it("formats date-only values without a timezone shift", () => {
    expect(fmtDate("2025-01-31")).toBe("Jan 31, 2025");
    expect(fmtLongDate("2026-12-31")).toBe("December 31, 2026");
    expect(fmtDate(null)).toBe("—");
  });

  it("describes days until a deadline", () => {
    expect(fmtDaysUntil(0)).toBe("today");
    expect(fmtDaysUntil(1)).toBe("tomorrow");
    expect(fmtDaysUntil(30)).toBe("in 30 days");
    expect(fmtDaysUntil(-1)).toBe("1 day ago");
    expect(fmtDaysUntil(-5)).toBe("5 days ago");
    expect(fmtDaysUntil(null)).toBe("");
  });

  it("labels citations by section and page", () => {
    expect(citationLabel({ section: "8.2", page: 14 })).toBe("Section 8.2 · Page 14");
    expect(citationLabel({ section: "Renewal", page: null })).toBe("Renewal");
    expect(citationLabel({ section: null, page: null })).toBe("Source");
  });

  it("pluralizes counts and units", () => {
    expect(plural(1, "item")).toBe("1 item");
    expect(plural(3, "item")).toBe("3 items");
    expect(unitLabel(30, "business_days")).toBe("30 business days");
    expect(unitLabel(1, "months")).toBe("1 month");
  });

  it("lets an open conflict win over a pending review status", () => {
    expect(reviewStatusKind("pending", { conflict: true })).toBe("conflict");
    expect(reviewStatusKind("pending")).toBe("needs_review");
    expect(reviewStatusKind("approved", { conflict: true })).toBe("approved");
  });
});
