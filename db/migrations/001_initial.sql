-- 001_initial.sql
-- Initial schema for the Contract Obligation and Renewal Assistant.
--
-- This directory (db/migrations/) is the ONLY place where DDL lives.
-- docs/database/schema.md describes this file; if they disagree, this file wins
-- and the doc must be updated.
--
-- Conventions:
--   ids         TEXT, prefixed (ctr_, ver_, seg_, itm_, obl_, ren_, cit_, clq_, rev_, chg_)
--   dates       TEXT 'YYYY-MM-DD'
--   timestamps  TEXT ISO-8601 UTC, e.g. '2026-10-03T10:00:00Z'
--   JSON        TEXT containing JSON (validated by the backend, not by SQLite)
--   booleans    INTEGER 0/1

PRAGMA foreign_keys = ON;

CREATE TABLE schema_migrations (
    version     TEXT PRIMARY KEY,
    applied_at  TEXT NOT NULL
);

-- A logical agreement. Display fields (parties, dates, deadlines) are NOT stored
-- here; they are derived from the latest version's extracted items and renewal.
CREATE TABLE contracts (
    id          TEXT PRIMARY KEY,
    name        TEXT NOT NULL,
    created_at  TEXT NOT NULL,
    updated_at  TEXT NOT NULL
);

-- One uploaded document. Never overwritten; a new upload creates a new row.
CREATE TABLE contract_versions (
    id              TEXT PRIMARY KEY,
    contract_id     TEXT NOT NULL REFERENCES contracts(id) ON DELETE CASCADE,
    version_number  INTEGER NOT NULL,
    file_name       TEXT NOT NULL,
    file_path       TEXT NOT NULL,
    file_hash       TEXT NOT NULL,                 -- sha256 of the uploaded bytes
    mime_type       TEXT NOT NULL,
    page_count      INTEGER,                       -- NULL for DOCX
    uploaded_at     TEXT NOT NULL,
    analysis_status TEXT NOT NULL DEFAULT 'not_started'
        CHECK (analysis_status IN ('not_started', 'queued', 'processing', 'completed', 'failed')),
    analysis_stage  TEXT
        CHECK (analysis_stage IN ('parsing', 'extracting', 'validating', 'analyzing', 'complete')),
    analysis_error_code    TEXT,                   -- error code from docs/api/errors.md
    analysis_error_message TEXT,
    analysis_started_at    TEXT,
    analysis_completed_at  TEXT,
    model_name      TEXT,                          -- e.g. 'qwen3:8b'
    prompt_version  TEXT,                          -- e.g. 'terms-v1+obligations-v1'
    UNIQUE (contract_id, version_number)
);

-- Normalized text of a version, split into citable segments.
-- The model cites segments by label ('S12'); the backend resolves page/section
-- from this table. The model never supplies page numbers.
CREATE TABLE document_segments (
    id                  TEXT PRIMARY KEY,
    contract_version_id TEXT NOT NULL REFERENCES contract_versions(id) ON DELETE CASCADE,
    seq                 INTEGER NOT NULL,          -- 1-based; label shown to the model is 'S' || seq
    page                INTEGER,                   -- 1-based; NULL for DOCX
    section             TEXT,                      -- nearest heading, e.g. '4.2 Reporting Obligations'
    text                TEXT NOT NULL,
    UNIQUE (contract_version_id, seq)
);

-- AI-extracted facts about a version. Multiple rows with the same field_name are
-- allowed (multiple parties, or conflicting candidates for a single-valued field).
CREATE TABLE extracted_items (
    id                  TEXT PRIMARY KEY,
    contract_version_id TEXT NOT NULL REFERENCES contract_versions(id) ON DELETE CASCADE,
    field_name          TEXT NOT NULL
        CHECK (field_name IN ('party', 'effective_date', 'expiration_date', 'initial_term',
                              'renewal_terms', 'notice_period', 'termination_clause')),
    value_json          TEXT NOT NULL,             -- current value (AI value, or human edit)
    original_value_json TEXT NOT NULL,             -- AI value as extracted; never modified
    display_value       TEXT NOT NULL,             -- human-readable rendering, set by backend
    confidence          TEXT NOT NULL CHECK (confidence IN ('high', 'medium', 'low')),
    review_status       TEXT NOT NULL DEFAULT 'pending'
        CHECK (review_status IN ('pending', 'approved', 'edited', 'rejected')),
    ambiguity_note      TEXT,                      -- model-reported ambiguity, if any
    origin              TEXT NOT NULL DEFAULT 'ai'
        CHECK (origin IN ('ai', 'human')),         -- 'human' = entered via clarification 'custom'
    created_at          TEXT NOT NULL,
    updated_at          TEXT NOT NULL
);
CREATE INDEX idx_extracted_items_version ON extracted_items (contract_version_id, field_name);

CREATE TABLE obligations (
    id                  TEXT PRIMARY KEY,
    contract_version_id TEXT NOT NULL REFERENCES contract_versions(id) ON DELETE CASCADE,
    description         TEXT NOT NULL,
    responsible_party   TEXT,
    frequency           TEXT
        CHECK (frequency IN ('one_time', 'monthly', 'quarterly', 'annually', 'other')),
    frequency_text      TEXT,                      -- the rule as written in the contract
    due_rule_json       TEXT,                      -- structured rule, see docs/architecture/date-calculation.md
    due_date            TEXT,                      -- explicit or calculated; NULL if unknown
    due_date_source     TEXT CHECK (due_date_source IN ('explicit', 'calculated')),
    status              TEXT NOT NULL DEFAULT 'open'
        CHECK (status IN ('open', 'completed', 'not_applicable')),   -- operational status
    confidence          TEXT NOT NULL CHECK (confidence IN ('high', 'medium', 'low')),
    review_status       TEXT NOT NULL DEFAULT 'pending'
        CHECK (review_status IN ('pending', 'approved', 'edited', 'rejected')),
    original_value_json TEXT NOT NULL,             -- AI output for this obligation; never modified
    ambiguity_note      TEXT,
    created_at          TEXT NOT NULL,
    updated_at          TEXT NOT NULL
);
CREATE INDEX idx_obligations_version ON obligations (contract_version_id);

-- Deterministic calculation output for a version. Not AI output and not reviewed
-- directly: it is recomputed from extracted_items whenever an input item changes.
CREATE TABLE renewals (
    id                   TEXT PRIMARY KEY,
    contract_version_id  TEXT NOT NULL UNIQUE REFERENCES contract_versions(id) ON DELETE CASCADE,
    effective_date       TEXT,
    expiration_date      TEXT,
    expiration_source    TEXT CHECK (expiration_source IN ('explicit', 'calculated')),
    renewal_type         TEXT CHECK (renewal_type IN ('automatic', 'optional', 'none')),
    renewal_period_value INTEGER,
    renewal_period_unit  TEXT CHECK (renewal_period_unit IN ('days', 'months', 'years')),
    current_term_end     TEXT,                     -- expiration rolled forward for auto-renewal
    notice_period_value  INTEGER,
    notice_period_unit   TEXT CHECK (notice_period_unit IN ('days', 'business_days', 'months')),
    notice_anchor        TEXT CHECK (notice_anchor IN ('expiration_date', 'renewal_date', 'other')),
    notice_deadline      TEXT,                     -- last day notice can be given
    calculation_status   TEXT NOT NULL
        CHECK (calculation_status IN ('calculated', 'incomplete', 'blocked_by_conflict')),
    calculation_note     TEXT,
    calculated_at        TEXT NOT NULL
);

-- Evidence for an extracted item, obligation, or clarification question.
-- entity_id is polymorphic (no FK); the service layer enforces it.
CREATE TABLE citations (
    id                  TEXT PRIMARY KEY,
    contract_version_id TEXT NOT NULL REFERENCES contract_versions(id) ON DELETE CASCADE,
    entity_type         TEXT NOT NULL
        CHECK (entity_type IN ('extracted_item', 'obligation', 'clarification_question')),
    entity_id           TEXT NOT NULL,
    segment_id          TEXT REFERENCES document_segments(id) ON DELETE SET NULL,
    page                INTEGER,                   -- copied from the segment
    section             TEXT,                      -- copied from the segment
    source_text         TEXT NOT NULL,             -- quote as returned by the model
    char_start          INTEGER,                   -- offsets in segment text when located
    char_end            INTEGER,
    validation_status   TEXT NOT NULL
        CHECK (validation_status IN ('verified', 'approximate', 'not_found'))
);
CREATE INDEX idx_citations_entity ON citations (entity_type, entity_id);

-- Conflicts, ambiguities and missing critical information that need a human.
CREATE TABLE clarification_questions (
    id                  TEXT PRIMARY KEY,
    contract_version_id TEXT NOT NULL REFERENCES contract_versions(id) ON DELETE CASCADE,
    kind                TEXT NOT NULL CHECK (kind IN ('conflict', 'ambiguity', 'missing')),
    field_name          TEXT,
    question            TEXT NOT NULL,
    status              TEXT NOT NULL DEFAULT 'open'
        CHECK (status IN ('open', 'resolved', 'dismissed')),
    resolution_json     TEXT,                      -- what the human chose; separate from extraction
    resolution_note     TEXT,
    created_at          TEXT NOT NULL,
    resolved_at         TEXT
);
CREATE INDEX idx_clarifications_version ON clarification_questions (contract_version_id, status);

-- The candidate items a clarification question is about (e.g. the 90-day and
-- the 60-day notice_period items).
CREATE TABLE clarification_options (
    clarification_id TEXT NOT NULL REFERENCES clarification_questions(id) ON DELETE CASCADE,
    entity_type      TEXT NOT NULL CHECK (entity_type IN ('extracted_item', 'obligation')),
    entity_id        TEXT NOT NULL,
    PRIMARY KEY (clarification_id, entity_type, entity_id)
);

-- Append-only audit log of human review actions. The current review_status lives
-- on the item itself; this table is the history.
CREATE TABLE reviews (
    id                     TEXT PRIMARY KEY,
    entity_type            TEXT NOT NULL CHECK (entity_type IN ('extracted_item', 'obligation')),
    entity_id              TEXT NOT NULL,
    action                 TEXT NOT NULL CHECK (action IN ('approve', 'edit', 'reject')),
    previous_review_status TEXT NOT NULL,
    new_review_status      TEXT NOT NULL,
    previous_value_json    TEXT,
    new_value_json         TEXT,
    note                   TEXT,
    clarification_id       TEXT REFERENCES clarification_questions(id) ON DELETE SET NULL,
    reviewed_at            TEXT NOT NULL
);
CREATE INDEX idx_reviews_entity ON reviews (entity_type, entity_id);

-- Result of comparing a version with the previous version. Rows whose
-- change_type is 'modified' or 'removed' mark the previous item as potentially stale.
CREATE TABLE version_changes (
    id                  TEXT PRIMARY KEY,
    contract_version_id TEXT NOT NULL REFERENCES contract_versions(id) ON DELETE CASCADE,
    previous_version_id TEXT NOT NULL REFERENCES contract_versions(id) ON DELETE CASCADE,
    entity_type         TEXT NOT NULL CHECK (entity_type IN ('extracted_item', 'obligation')),
    field_name          TEXT,                      -- extracted_items.field_name, or 'obligation'
    change_type         TEXT NOT NULL CHECK (change_type IN ('added', 'removed', 'modified')),
    previous_entity_id  TEXT,
    new_entity_id       TEXT,
    previous_display    TEXT,
    new_display         TEXT,
    created_at          TEXT NOT NULL
);
CREATE INDEX idx_version_changes_version ON version_changes (contract_version_id);

INSERT INTO schema_migrations (version, applied_at)
VALUES ('001_initial', strftime('%Y-%m-%dT%H:%M:%SZ', 'now'));
