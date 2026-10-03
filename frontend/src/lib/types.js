// API data shapes as JSDoc typedefs, mirroring docs/api/*.md exactly. If the API docs change, change these.
// Editors use them for hints; import with `/** @typedef {import("@/lib/types").Obligation} Obligation */`.

/** @typedef {"high" | "medium" | "low"} Confidence */
/** @typedef {"pending" | "approved" | "edited" | "rejected"} ReviewStatus */
/** @typedef {"not_started" | "queued" | "processing" | "completed" | "failed"} AnalysisStatus */
/** @typedef {"parsing" | "extracting" | "validating" | "analyzing" | "complete"} AnalysisStage */
/** @typedef {"active" | "expiring_soon" | "expired" | "unknown"} LifecycleStatus */
/** @typedef {"calculated" | "incomplete" | "blocked_by_conflict"} CalculationStatus */
/** @typedef {"open" | "completed" | "not_applicable"} ObligationStatus */
/** @typedef {"extracted_item" | "obligation"} EntityType */
/** @typedef {"party" | "effective_date" | "expiration_date" | "initial_term" | "renewal_terms" | "notice_period" | "termination_clause"} FieldName */
/**
 * @typedef {Object} ApiErrorBody
 * @property {string} code
 * @property {string} message
 * @property {unknown} details
 * @property {string | null} request_id
 */

/**
 * @typedef {Object} Citation
 * @property {string} id
 * @property {string} contract_version_id
 * @property {number | null} page
 * @property {string | null} section
 * @property {string} source_text
 * @property {"verified" | "approximate" | "not_found"} validation_status
 */

/**
 * @typedef {Object} VersionBrief
 * @property {string} id
 * @property {number} version_number
 * @property {AnalysisStatus} analysis_status
 */

/**
 * @typedef {Object} ContractSummary
 * @property {string} id
 * @property {string} name
 * @property {string[]} parties
 * @property {string | null} effective_date
 * @property {string | null} expiration_date
 * @property {string | null} current_term_end
 * @property {"automatic" | "optional" | "none" | null} renewal_type
 * @property {string | null} notice_deadline
 * @property {number | null} days_until_notice_deadline
 * @property {LifecycleStatus} lifecycle_status
 * @property {VersionBrief | null} latest_version
 * @property {number} pending_review_count
 * @property {number} open_clarification_count
 * @property {string} created_at
 * @property {string} updated_at
 */

/**
 * @typedef {Object} Renewal
 * @property {string} contract_id
 * @property {string} contract_name
 * @property {string} contract_version_id
 * @property {string | null} effective_date
 * @property {string | null} expiration_date
 * @property {"explicit" | "calculated" | null} expiration_source
 * @property {"automatic" | "optional" | "none" | null} renewal_type
 * @property {{ value: number, unit: string } | null} renewal_period
 * @property {string | null} current_term_end
 * @property {{ value: number, unit: string, anchor: string } | null} notice_period
 * @property {string | null} notice_deadline
 * @property {number | null} days_until_notice_deadline
 * @property {number | null} days_until_term_end
 * @property {LifecycleStatus} lifecycle_status
 * @property {CalculationStatus} calculation_status
 * @property {string | null} calculation_note
 * @property {boolean} inputs_reviewed
 * @property {string[]} input_item_ids
 */

/**
 * @typedef {Object} ContractDetail
 * @property {string} id
 * @property {string} name
 * @property {{ id: string, version_number: number, file_name: string, uploaded_at: string, analysis_status: AnalysisStatus, is_latest: boolean }} version
 * @property {number} version_count
 * @property {{ item_id: string, name: string, role: string | null, confidence: Confidence, review_status: ReviewStatus }[]} parties
 * @property {Renewal | null} renewal
 * @property {{ extracted_items: number, obligations: number, pending_reviews: number, open_clarifications: number }} counts
 * @property {LifecycleStatus} lifecycle_status
 * @property {string} created_at
 * @property {string} updated_at
 */

/**
 * @typedef {Object} ExtractedItem
 * @property {string} id
 * @property {string} contract_version_id
 * @property {FieldName} field_name
 * @property {string} label
 * @property {Record<string, unknown>} value
 * @property {Record<string, unknown>} original_value
 * @property {string} display_value
 * @property {string} original_display_value
 * @property {Confidence} confidence
 * @property {ReviewStatus} review_status
 * @property {string | null} ambiguity_note
 * @property {"ai" | "human"} origin
 * @property {boolean} in_open_clarification
 * @property {string | null} clarification_id
 * @property {Citation[]} citations
 * @property {string} updated_at
 */

/**
 * @typedef {Object} DueRule
 * @property {"explicit_date" | "effective_date_anniversary" | "calendar_period_end" | "renewal_notice_deadline" | "unspecified"} basis
 * @property {number} offset_days
 * @property {string} [due_date_text]
 */

/**
 * @typedef {Object} Obligation
 * @property {string} id
 * @property {string} contract_id
 * @property {string} contract_name
 * @property {string} contract_version_id
 * @property {string} description
 * @property {string | null} responsible_party
 * @property {"one_time" | "monthly" | "quarterly" | "annually" | "other" | null} frequency
 * @property {string | null} frequency_text
 * @property {DueRule | null} due_rule
 * @property {string | null} due_date
 * @property {"explicit" | "calculated" | null} due_date_source
 * @property {number | null} days_until_due
 * @property {ObligationStatus} status
 * @property {Confidence} confidence
 * @property {ReviewStatus} review_status
 * @property {Record<string, unknown>} original_value
 * @property {string | null} ambiguity_note
 * @property {boolean} in_open_clarification
 * @property {Citation[]} citations
 * @property {string} updated_at
 */

/**
 * @typedef {Object} AnalysisState
 * @property {string} contract_id
 * @property {string} version_id
 * @property {AnalysisStatus} analysis_status
 * @property {AnalysisStage | null} analysis_stage
 * @property {{ current: number, total: number } | null} progress
 * @property {{ code: string, message: string } | null} error
 * @property {string | null} started_at
 * @property {string | null} completed_at
 * @property {{ extracted_items: number, obligations: number, pending_reviews: number, open_clarifications: number, citations_not_found: number, renewal_calculation_status: CalculationStatus | null } | null} summary
 */

/**
 * @typedef {Object} Version
 * @property {string} id
 * @property {string} contract_id
 * @property {number} version_number
 * @property {string} file_name
 * @property {string} mime_type
 * @property {number | null} page_count
 * @property {string} uploaded_at
 * @property {AnalysisStatus} analysis_status
 * @property {string | null} analysis_completed_at
 * @property {boolean} is_latest
 * @property {number | null} change_count
 */

/**
 * @typedef {Object} VersionChange
 * @property {string} id
 * @property {EntityType} entity_type
 * @property {string} field_name
 * @property {"added" | "removed" | "modified"} change_type
 * @property {string | null} previous_entity_id
 * @property {string | null} new_entity_id
 * @property {string | null} previous_display
 * @property {string | null} new_display
 * @property {ReviewStatus | null} previous_review_status
 */

/**
 * @typedef {Object} VersionChanges
 * @property {string} version_id
 * @property {string | null} previous_version_id
 * @property {VersionChange[]} items
 */

/**
 * @typedef {Object} QueueItem
 * @property {EntityType} entity_type
 * @property {string} entity_id
 * @property {string} contract_id
 * @property {string} contract_name
 * @property {string} contract_version_id
 * @property {FieldName | null} field_name
 * @property {string} label
 * @property {string} display_value
 * @property {Record<string, unknown>} value
 * @property {Confidence} confidence
 * @property {ReviewStatus} review_status
 * @property {string | null} ambiguity_note
 * @property {string | null} clarification_id
 * @property {Citation[]} citations
 */

/**
 * @typedef {Object} ReviewEntry
 * @property {string} id
 * @property {EntityType} entity_type
 * @property {string} entity_id
 * @property {"approve" | "edit" | "reject"} action
 * @property {ReviewStatus} previous_review_status
 * @property {ReviewStatus} new_review_status
 * @property {unknown} previous_value
 * @property {unknown} new_value
 * @property {string | null} note
 * @property {string | null} clarification_id
 * @property {string} reviewed_at
 */

/**
 * @typedef {Object} RecentReviewExtra
 * @property {string} contract_id
 * @property {string} contract_name
 * @property {string} label
 */

/**
 * @typedef {ReviewEntry & RecentReviewExtra} RecentReview
 */

/**
 * @typedef {Object} ClarificationOption
 * @property {EntityType} entity_type
 * @property {string} entity_id
 * @property {string} display_value
 * @property {ReviewStatus} review_status
 * @property {Citation[]} citations
 */

/**
 * @typedef {Object} Clarification
 * @property {string} id
 * @property {string} contract_id
 * @property {string} contract_name
 * @property {string} contract_version_id
 * @property {"conflict" | "ambiguity" | "missing"} kind
 * @property {FieldName | null} field_name
 * @property {string} question
 * @property {"open" | "resolved" | "dismissed"} status
 * @property {ClarificationOption[]} options
 * @property {Citation[]} citations
 * @property {Record<string, unknown> | null} resolution
 * @property {string | null} resolution_note
 * @property {string} created_at
 * @property {string | null} resolved_at
 */

/**
 * @typedef {Object} CitationDetail
 * @property {string} id
 * @property {string} contract_id
 * @property {string} contract_version_id
 * @property {number} version_number
 * @property {string} file_name
 * @property {string} entity_type
 * @property {string} entity_id
 * @property {number | null} page
 * @property {string | null} section
 * @property {string} source_text
 * @property {Citation["validation_status"]} validation_status
 * @property {{ text: string, highlight: { start: number, end: number } | null } | null} segment
 * @property {string | null} context_before
 * @property {string | null} context_after
 */

/**
 * @typedef {Object} Dashboard
 * @property {{ contracts: number, contracts_needing_review: number, upcoming_notice_deadlines: number, open_obligations: number, open_clarifications: number }} counts
 * @property {{ type: "notice_deadline" | "obligation", contract_id: string, contract_name: string, label: string, date: string, days_until: number, entity_id: string | null }[]} upcoming_deadlines
 * @property {{ type: "upload" | "analysis" | "review" | "clarification", contract_id: string, contract_name: string, description: string, at: string }[]} recent_activity
 */

/**
 * @typedef {Object} ItemDetail
 * @property {EntityType} entity_type
 * @property {ExtractedItem | Obligation} item
 * @property {string} contract_id
 * @property {string} contract_name
 * @property {number} version_number
 * @property {boolean} is_latest_version
 */

/**
 * @typedef {Object} Health
 * @property {"ok" | "degraded"} status
 * @property {string} database
 * @property {{ reachable: boolean, model: string, model_available: boolean }} ollama
 */

export {};
