import { describe, expect, it } from "vitest";
import { isIsoDate, validateEditValue as v } from "./validation";

describe("validateEditValue", () => {
  it("party: name is required, role is optional", () => {
    expect(v("party", { name: "Acme", role: null })).toEqual({});
    expect(v("party", { name: "  ", role: "Customer" })).toEqual({ name: "Enter a name" });
  });

  it("dates: required and a real YYYY-MM-DD date", () => {
    expect(v("expiration_date", { date: "2026-12-31", date_text: "2026-12-31" })).toEqual({});
    expect(v("effective_date", { date: "", date_text: "" })).toEqual({ date: "Enter a date" });
    expect(v("effective_date", { date: "2026-02-30" })).toEqual({ date: "Enter a valid date" });
    expect(v("expiration_date", { date: "31/12/2026" })).toEqual({ date: "Enter a valid date" });
  });

  it("initial_term: whole number above 0 and a unit", () => {
    expect(v("initial_term", { value: 3, unit: "years" })).toEqual({});
    expect(v("initial_term", { value: null, unit: "years" })).toEqual({ value: "Enter a number" });
    for (const bad of [0, -2, 1.5, NaN])
      expect(v("initial_term", { value: bad, unit: "days" })).toEqual({ value: "Must be a whole number above 0" });
    expect(v("initial_term", { value: 1, unit: "weeks" })).toEqual({ unit: "Choose a unit" });
  });

  it("renewal_terms: type required; period optional but positive when given", () => {
    expect(v("renewal_terms", { type: "automatic", period_value: 12, period_unit: "months" })).toEqual({});
    expect(v("renewal_terms", { type: "none", period_value: null, period_unit: null })).toEqual({});
    expect(v("renewal_terms", { type: "", period_value: 0, period_unit: "weeks" })).toEqual({
      type: "Choose a renewal type",
      period_value: "Must be a whole number above 0",
      period_unit: "Choose a unit",
    });
  });

  it("notice_period: length, unit, anchor and purpose", () => {
    const ok = { value: 90, unit: "business_days", anchor: "renewal_date", purpose: "termination" };
    expect(v("notice_period", ok)).toEqual({});
    expect(v("notice_period", { value: 0 })).toEqual({
      value: "Must be a whole number above 0",
      unit: "Choose a unit",
      anchor: "Choose what the notice is before",
      purpose: "Choose a purpose",
    });
    expect(v("notice_period", { ...ok, unit: "years" })).toEqual({ unit: "Choose a unit" });
  });

  it("termination_clause: summary required, at most 300 characters", () => {
    expect(v("termination_clause", { summary: "Either party may terminate on 30 days notice." })).toEqual({});
    expect(v("termination_clause", { summary: "" })).toEqual({ summary: "Enter a summary" });
    expect(v("termination_clause", { summary: "x".repeat(301) })).toEqual({
      summary: "Keep it to 300 characters or fewer",
    });
  });

  it("obligation: description required (max 120); frequency and due date optional but valid", () => {
    expect(v("obligation", { description: "Send report", responsible_party: null, frequency: null })).toEqual({});
    expect(
      v("obligation", { description: "Pay", responsible_party: "Acme", frequency: "monthly", due_date: "2027-01-31" }),
    ).toEqual({});
    expect(v("obligation", { description: "", frequency: "weekly", due_date: "2027-13-01" })).toEqual({
      description: "Enter a description",
      frequency: "Choose a frequency",
      due_date: "Enter a valid date",
    });
    expect(v("obligation", { description: "x".repeat(121) })).toEqual({
      description: "Keep it to 120 characters or fewer",
    });
  });

  it("isIsoDate rejects impossible dates", () => {
    expect(isIsoDate("2028-02-29")).toBe(true);
    expect(isIsoDate("2027-02-29")).toBe(false);
    expect(isIsoDate(null)).toBe(false);
  });
});
