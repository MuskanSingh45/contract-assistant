// Minimal API objects in the documented shapes (docs/api/). Override fields per test.
import type { Citation, Clarification, ContractSummary } from "@/lib/types";

export const citation = (over: Partial<Citation> = {}): Citation => ({
  id: "cit_1",
  contract_version_id: "ver_1",
  page: 2,
  section: "2.2 Renewal",
  source_text: "either party gives notice at least 90 days before",
  validation_status: "verified",
  ...over,
});

export const contract = (over: Partial<ContractSummary> = {}): ContractSummary => ({
  id: "ctr_acme",
  name: "Acme Services Agreement",
  parties: ["Acme Corporation", "Example Services Ltd."],
  effective_date: "2025-01-01",
  expiration_date: "2026-12-31",
  current_term_end: "2026-12-31",
  renewal_type: "automatic",
  notice_deadline: "2026-11-02",
  days_until_notice_deadline: 30,
  lifecycle_status: "expiring_soon",
  latest_version: { id: "ver_1", version_number: 1, analysis_status: "completed" },
  pending_review_count: 0,
  open_clarification_count: 0,
  created_at: "2026-10-01T10:00:00Z",
  updated_at: "2026-10-01T10:00:00Z",
  ...over,
});

export const conflict = (over: Partial<Clarification> = {}): Clarification => ({
  id: "clr_1",
  contract_id: "ctr_globex",
  contract_name: "Globex Hosting Agreement",
  contract_version_id: "ver_g1",
  kind: "conflict",
  field_name: "notice_period",
  question: "Which notice period applies: 90 days or 60 days?",
  status: "open",
  options: [
    {
      entity_type: "extracted_item",
      entity_id: "itm_90",
      display_value: "90 days before expiration",
      review_status: "pending",
      citations: [citation({ id: "cit_90", section: "4.1" })],
    },
    {
      entity_type: "extracted_item",
      entity_id: "itm_60",
      display_value: "60 days before expiration",
      review_status: "pending",
      citations: [citation({ id: "cit_60", section: "12.3", source_text: "sixty (60) days" })],
    },
  ],
  citations: [],
  resolution: null,
  resolution_note: null,
  created_at: "2026-10-03T09:00:00Z",
  resolved_at: null,
  ...over,
});
