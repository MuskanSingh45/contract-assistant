// Types mirroring docs/api/*.md exactly. If the API docs change, change these.

export type Confidence = "high" | "medium" | "low";
export type ReviewStatus = "pending" | "approved" | "edited" | "rejected";
export type AnalysisStatus = "not_started" | "queued" | "processing" | "completed" | "failed";
export type AnalysisStage = "parsing" | "extracting" | "validating" | "analyzing" | "complete";
export type LifecycleStatus = "active" | "expiring_soon" | "expired" | "unknown";
export type CalculationStatus = "calculated" | "incomplete" | "blocked_by_conflict";
export type ObligationStatus = "open" | "completed" | "not_applicable";
export type EntityType = "extracted_item" | "obligation";
export type FieldName =
  | "party"
  | "effective_date"
  | "expiration_date"
  | "initial_term"
  | "renewal_terms"
  | "notice_period"
  | "termination_clause";

export interface ApiErrorBody {
  code: string;
  message: string;
  details: unknown;
}

export interface Citation {
  id: string;
  contract_version_id: string;
  page: number | null;
  section: string | null;
  source_text: string;
  validation_status: "verified" | "approximate" | "not_found";
}

export interface VersionBrief {
  id: string;
  version_number: number;
  analysis_status: AnalysisStatus;
}

export interface ContractSummary {
  id: string;
  name: string;
  parties: string[];
  effective_date: string | null;
  expiration_date: string | null;
  current_term_end: string | null;
  renewal_type: "automatic" | "optional" | "none" | null;
  notice_deadline: string | null;
  days_until_notice_deadline: number | null;
  lifecycle_status: LifecycleStatus;
  latest_version: VersionBrief | null;
  pending_review_count: number;
  open_clarification_count: number;
  created_at: string;
  updated_at: string;
}

export interface Renewal {
  contract_id: string;
  contract_name: string;
  contract_version_id: string;
  effective_date: string | null;
  expiration_date: string | null;
  expiration_source: "explicit" | "calculated" | null;
  renewal_type: "automatic" | "optional" | "none" | null;
  renewal_period: { value: number; unit: string } | null;
  current_term_end: string | null;
  notice_period: { value: number; unit: string; anchor: string } | null;
  notice_deadline: string | null;
  days_until_notice_deadline: number | null;
  days_until_term_end: number | null;
  lifecycle_status: LifecycleStatus;
  calculation_status: CalculationStatus;
  calculation_note: string | null;
  inputs_reviewed: boolean;
  input_item_ids: string[];
}

export interface ContractDetail {
  id: string;
  name: string;
  version: {
    id: string;
    version_number: number;
    file_name: string;
    uploaded_at: string;
    analysis_status: AnalysisStatus;
    is_latest: boolean;
  };
  version_count: number;
  parties: {
    item_id: string;
    name: string;
    role: string | null;
    confidence: Confidence;
    review_status: ReviewStatus;
  }[];
  renewal: Renewal | null;
  counts: { extracted_items: number; obligations: number; pending_reviews: number; open_clarifications: number };
  lifecycle_status: LifecycleStatus;
  created_at: string;
  updated_at: string;
}

export interface ExtractedItem {
  id: string;
  contract_version_id: string;
  field_name: FieldName;
  label: string;
  value: Record<string, unknown>;
  original_value: Record<string, unknown>;
  display_value: string;
  original_display_value: string;
  confidence: Confidence;
  review_status: ReviewStatus;
  ambiguity_note: string | null;
  origin: "ai" | "human";
  in_open_clarification: boolean;
  clarification_id: string | null;
  citations: Citation[];
  updated_at: string;
}

export interface DueRule {
  basis:
    "explicit_date" | "effective_date_anniversary" | "calendar_period_end" | "renewal_notice_deadline" | "unspecified";
  offset_days: number;
  due_date_text?: string;
}

export interface Obligation {
  id: string;
  contract_id: string;
  contract_name: string;
  contract_version_id: string;
  description: string;
  responsible_party: string | null;
  frequency: "one_time" | "monthly" | "quarterly" | "annually" | "other" | null;
  frequency_text: string | null;
  due_rule: DueRule | null;
  due_date: string | null;
  due_date_source: "explicit" | "calculated" | null;
  days_until_due: number | null;
  status: ObligationStatus;
  confidence: Confidence;
  review_status: ReviewStatus;
  original_value: Record<string, unknown>;
  ambiguity_note: string | null;
  in_open_clarification: boolean;
  citations: Citation[];
  updated_at: string;
}

export interface AnalysisState {
  contract_id: string;
  version_id: string;
  analysis_status: AnalysisStatus;
  analysis_stage: AnalysisStage | null;
  progress: { current: number; total: number } | null;
  error: { code: string; message: string } | null;
  started_at: string | null;
  completed_at: string | null;
  summary: {
    extracted_items: number;
    obligations: number;
    pending_reviews: number;
    open_clarifications: number;
    citations_not_found: number;
    renewal_calculation_status: CalculationStatus | null;
  } | null;
}

export interface Version {
  id: string;
  contract_id: string;
  version_number: number;
  file_name: string;
  mime_type: string;
  page_count: number | null;
  uploaded_at: string;
  analysis_status: AnalysisStatus;
  analysis_completed_at: string | null;
  is_latest: boolean;
  change_count: number | null;
}

export interface VersionChange {
  id: string;
  entity_type: EntityType;
  field_name: string;
  change_type: "added" | "removed" | "modified";
  previous_entity_id: string | null;
  new_entity_id: string | null;
  previous_display: string | null;
  new_display: string | null;
  previous_review_status: ReviewStatus | null;
}

export interface VersionChanges {
  version_id: string;
  previous_version_id: string | null;
  items: VersionChange[];
}

export interface QueueItem {
  entity_type: EntityType;
  entity_id: string;
  contract_id: string;
  contract_name: string;
  contract_version_id: string;
  field_name: FieldName | null;
  label: string;
  display_value: string;
  value: Record<string, unknown>;
  confidence: Confidence;
  review_status: ReviewStatus;
  ambiguity_note: string | null;
  clarification_id: string | null;
  citations: Citation[];
}

export interface ReviewEntry {
  id: string;
  entity_type: EntityType;
  entity_id: string;
  action: "approve" | "edit" | "reject";
  previous_review_status: ReviewStatus;
  new_review_status: ReviewStatus;
  previous_value: unknown;
  new_value: unknown;
  note: string | null;
  clarification_id: string | null;
  reviewed_at: string;
}

export interface RecentReview extends ReviewEntry {
  contract_id: string;
  contract_name: string;
  label: string;
}

export interface ClarificationOption {
  entity_type: EntityType;
  entity_id: string;
  display_value: string;
  review_status: ReviewStatus;
  citations: Citation[];
}

export interface Clarification {
  id: string;
  contract_id: string;
  contract_name: string;
  contract_version_id: string;
  kind: "conflict" | "ambiguity" | "missing";
  field_name: FieldName | null;
  question: string;
  status: "open" | "resolved" | "dismissed";
  options: ClarificationOption[];
  citations: Citation[];
  resolution: Record<string, unknown> | null;
  resolution_note: string | null;
  created_at: string;
  resolved_at: string | null;
}

export interface CitationDetail {
  id: string;
  contract_id: string;
  contract_version_id: string;
  version_number: number;
  file_name: string;
  entity_type: string;
  entity_id: string;
  page: number | null;
  section: string | null;
  source_text: string;
  validation_status: Citation["validation_status"];
  segment: { text: string; highlight: { start: number; end: number } | null } | null;
  context_before: string | null;
  context_after: string | null;
}

export interface Dashboard {
  counts: {
    contracts: number;
    contracts_needing_review: number;
    upcoming_notice_deadlines: number;
    open_obligations: number;
    open_clarifications: number;
  };
  upcoming_deadlines: {
    type: "notice_deadline" | "obligation";
    contract_id: string;
    contract_name: string;
    label: string;
    date: string;
    days_until: number;
    entity_id: string | null;
  }[];
  recent_activity: {
    type: "upload" | "analysis" | "review" | "clarification";
    contract_id: string;
    contract_name: string;
    description: string;
    at: string;
  }[];
}

export interface ItemDetail {
  entity_type: EntityType;
  item: ExtractedItem | Obligation;
  contract_id: string;
  contract_name: string;
  version_number: number;
  is_latest_version: boolean;
}

export interface Health {
  status: "ok" | "degraded";
  database: string;
  ollama: { reachable: boolean; model: string; model_available: boolean };
}
