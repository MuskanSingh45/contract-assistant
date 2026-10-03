-- development.sql
-- Demo data for local development. Apply after db/migrations/*.sql.
--
-- Contract 1: Acme Services Agreement — clean, fully calculated.
--   90 days before 2027-01-31 = 2026-11-02 (notice deadline).
-- Contract 2: Globex Hosting Agreement — conflicting notice periods (90 vs 60 days),
--   so the renewal calculation is blocked and a clarification question is open.
--
-- Values that depend on "today" (calculated obligation due dates, current_term_end)
-- were computed for 2026-10-03. The backend recalculates them on analysis/review.

PRAGMA foreign_keys = ON;

-- ---------------------------------------------------------------- contracts
INSERT INTO contracts (id, name, created_at, updated_at) VALUES
 ('ctr_acme',   'Acme Services Agreement',  '2026-09-28T09:00:00Z', '2026-09-29T14:10:00Z'),
 ('ctr_globex', 'Globex Hosting Agreement', '2026-10-01T11:00:00Z', '2026-10-01T11:04:00Z');

INSERT INTO contract_versions (id, contract_id, version_number, file_name, file_path, file_hash,
    mime_type, page_count, uploaded_at, analysis_status, analysis_stage,
    analysis_started_at, analysis_completed_at, model_name, prompt_version) VALUES
 ('ver_acme_1', 'ctr_acme', 1, 'acme-services-agreement.pdf',
  'uploads/ctr_acme/ver_acme_1/acme-services-agreement.pdf',
  'seed-acme-1', 'application/pdf', 14, '2026-09-28T09:00:00Z', 'completed', 'complete',
  '2026-09-28T09:00:05Z', '2026-09-28T09:02:40Z', 'qwen3:8b', 'terms-v1+obligations-v1'),
 ('ver_globex_1', 'ctr_globex', 1, 'globex-hosting-agreement.docx',
  'uploads/ctr_globex/ver_globex_1/globex-hosting-agreement.docx',
  'seed-globex-1', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document', NULL,
  '2026-10-01T11:00:00Z', 'completed', 'complete',
  '2026-10-01T11:00:03Z', '2026-10-01T11:04:00Z', 'qwen3:8b', 'terms-v1+obligations-v1');

-- ---------------------------------------------------------------- segments
INSERT INTO document_segments (id, contract_version_id, seq, page, section, text) VALUES
 ('seg_acme_1', 'ver_acme_1', 1, 1, 'Preamble',
  'This Services Agreement is entered into as of January 31, 2025 (the "Effective Date") by and between Acme Corporation ("Customer") and Example Services Ltd. ("Service Provider").'),
 ('seg_acme_2', 'ver_acme_1', 2, 2, '2.1 Term',
  'The initial term of this Agreement shall commence on the Effective Date and expire on January 31, 2027.'),
 ('seg_acme_3', 'ver_acme_1', 3, 2, '2.2 Renewal',
  'This Agreement shall automatically renew for successive twelve (12) month periods unless either party provides written notice of non-renewal at least ninety (90) days before the expiration of the then-current term.'),
 ('seg_acme_4', 'ver_acme_1', 4, 12, '4.2 Reporting Obligations',
  'Service Provider shall submit a compliance report to Customer within thirty (30) days after the end of each calendar quarter.'),
 ('seg_acme_5', 'ver_acme_1', 5, 13, '6.1 Insurance',
  'Service Provider shall deliver a current certificate of insurance to Customer annually on each anniversary of the Effective Date.'),
 ('seg_globex_1', 'ver_globex_1', 1, NULL, '1. Parties',
  'This Hosting Agreement is made on January 1, 2025 between Globex Inc. ("Client") and Initech Hosting LLC ("Provider").'),
 ('seg_globex_2', 'ver_globex_1', 2, NULL, '3.2 Renewal',
  'The Agreement expires on December 31, 2026 and renews automatically for one (1) year unless terminated by written notice given at least ninety (90) days prior to expiration.'),
 ('seg_globex_3', 'ver_globex_1', 3, NULL, '12.1 Notices',
  'Any notice of non-renewal must be delivered no later than sixty (60) days before the expiration date.');

-- ---------------------------------------------------------------- extracted items: Acme
INSERT INTO extracted_items (id, contract_version_id, field_name, value_json, original_value_json,
    display_value, confidence, review_status, ambiguity_note, created_at, updated_at) VALUES
 ('itm_acme_party_1', 'ver_acme_1', 'party',
  '{"name": "Acme Corporation", "role": "customer"}', '{"name": "Acme Corporation", "role": "customer"}',
  'Acme Corporation (customer)', 'high', 'pending', NULL, '2026-09-28T09:02:40Z', '2026-09-28T09:02:40Z'),
 ('itm_acme_party_2', 'ver_acme_1', 'party',
  '{"name": "Example Services Ltd.", "role": "service provider"}', '{"name": "Example Services Ltd.", "role": "service provider"}',
  'Example Services Ltd. (service provider)', 'high', 'pending', NULL, '2026-09-28T09:02:40Z', '2026-09-28T09:02:40Z'),
 ('itm_acme_eff', 'ver_acme_1', 'effective_date',
  '{"date": "2025-01-31", "date_text": "January 31, 2025"}', '{"date": "2025-01-31", "date_text": "January 31, 2025"}',
  '2025-01-31', 'high', 'approved', NULL, '2026-09-28T09:02:40Z', '2026-09-29T14:10:00Z'),
 ('itm_acme_exp', 'ver_acme_1', 'expiration_date',
  '{"date": "2027-01-31", "date_text": "January 31, 2027"}', '{"date": "2027-01-31", "date_text": "January 31, 2027"}',
  '2027-01-31', 'high', 'pending', NULL, '2026-09-28T09:02:40Z', '2026-09-28T09:02:40Z'),
 ('itm_acme_ren', 'ver_acme_1', 'renewal_terms',
  '{"type": "automatic", "period_value": 12, "period_unit": "months"}', '{"type": "automatic", "period_value": 12, "period_unit": "months"}',
  'Automatic, 12 months', 'high', 'pending', NULL, '2026-09-28T09:02:40Z', '2026-09-28T09:02:40Z'),
 ('itm_acme_notice', 'ver_acme_1', 'notice_period',
  '{"value": 90, "unit": "days", "anchor": "expiration_date", "purpose": "non_renewal"}', '{"value": 90, "unit": "days", "anchor": "expiration_date", "purpose": "non_renewal"}',
  '90 days before expiration (non-renewal)', 'high', 'pending', NULL, '2026-09-28T09:02:40Z', '2026-09-28T09:02:40Z');

-- ---------------------------------------------------------------- extracted items: Globex
INSERT INTO extracted_items (id, contract_version_id, field_name, value_json, original_value_json,
    display_value, confidence, review_status, ambiguity_note, created_at, updated_at) VALUES
 ('itm_globex_party_1', 'ver_globex_1', 'party',
  '{"name": "Globex Inc.", "role": "client"}', '{"name": "Globex Inc.", "role": "client"}',
  'Globex Inc. (client)', 'high', 'pending', NULL, '2026-10-01T11:04:00Z', '2026-10-01T11:04:00Z'),
 ('itm_globex_party_2', 'ver_globex_1', 'party',
  '{"name": "Initech Hosting LLC", "role": "provider"}', '{"name": "Initech Hosting LLC", "role": "provider"}',
  'Initech Hosting LLC (provider)', 'high', 'pending', NULL, '2026-10-01T11:04:00Z', '2026-10-01T11:04:00Z'),
 ('itm_globex_eff', 'ver_globex_1', 'effective_date',
  '{"date": "2025-01-01", "date_text": "January 1, 2025"}', '{"date": "2025-01-01", "date_text": "January 1, 2025"}',
  '2025-01-01', 'medium', 'pending', 'Date the agreement was made; no separate effective date clause.', '2026-10-01T11:04:00Z', '2026-10-01T11:04:00Z'),
 ('itm_globex_exp', 'ver_globex_1', 'expiration_date',
  '{"date": "2026-12-31", "date_text": "December 31, 2026"}', '{"date": "2026-12-31", "date_text": "December 31, 2026"}',
  '2026-12-31', 'high', 'pending', NULL, '2026-10-01T11:04:00Z', '2026-10-01T11:04:00Z'),
 ('itm_globex_ren', 'ver_globex_1', 'renewal_terms',
  '{"type": "automatic", "period_value": 1, "period_unit": "years"}', '{"type": "automatic", "period_value": 1, "period_unit": "years"}',
  'Automatic, 1 year', 'high', 'pending', NULL, '2026-10-01T11:04:00Z', '2026-10-01T11:04:00Z'),
 ('itm_globex_notice_90', 'ver_globex_1', 'notice_period',
  '{"value": 90, "unit": "days", "anchor": "expiration_date", "purpose": "non_renewal"}', '{"value": 90, "unit": "days", "anchor": "expiration_date", "purpose": "non_renewal"}',
  '90 days before expiration (non-renewal)', 'medium', 'pending', NULL, '2026-10-01T11:04:00Z', '2026-10-01T11:04:00Z'),
 ('itm_globex_notice_60', 'ver_globex_1', 'notice_period',
  '{"value": 60, "unit": "days", "anchor": "expiration_date", "purpose": "non_renewal"}', '{"value": 60, "unit": "days", "anchor": "expiration_date", "purpose": "non_renewal"}',
  '60 days before expiration (non-renewal)', 'medium', 'pending', NULL, '2026-10-01T11:04:00Z', '2026-10-01T11:04:00Z');

-- ---------------------------------------------------------------- obligations
INSERT INTO obligations (id, contract_version_id, description, responsible_party, frequency,
    frequency_text, due_rule_json, due_date, due_date_source, status, confidence, review_status,
    original_value_json, ambiguity_note, created_at, updated_at) VALUES
 ('obl_acme_report', 'ver_acme_1', 'Submit quarterly compliance report', 'Example Services Ltd.',
  'quarterly', 'within thirty (30) days after the end of each calendar quarter',
  '{"basis": "calendar_period_end", "offset_days": 30}',
  '2026-10-30', 'calculated', 'open', 'high', 'pending',
  '{"description": "Submit quarterly compliance report", "responsible_party": "Example Services Ltd.", "frequency": "quarterly"}',
  NULL, '2026-09-28T09:02:40Z', '2026-09-28T09:02:40Z'),
 ('obl_acme_insurance', 'ver_acme_1', 'Deliver annual certificate of insurance', 'Example Services Ltd.',
  'annually', 'annually on each anniversary of the Effective Date',
  '{"basis": "effective_date_anniversary", "offset_days": 0}',
  '2027-01-31', 'calculated', 'open', 'high', 'pending',
  '{"description": "Deliver annual certificate of insurance", "responsible_party": "Example Services Ltd.", "frequency": "annually"}',
  NULL, '2026-09-28T09:02:40Z', '2026-09-28T09:02:40Z'),
 ('obl_acme_nonrenewal', 'ver_acme_1', 'Provide written notice of non-renewal (if not renewing)', 'Either party',
  'one_time', 'at least ninety (90) days before the expiration of the then-current term',
  '{"basis": "renewal_notice_deadline", "offset_days": 0}',
  '2026-11-02', 'calculated', 'open', 'medium', 'pending',
  '{"description": "Provide written notice of non-renewal (if not renewing)", "responsible_party": "Either party", "frequency": "one_time"}',
  'Conditional: only required if a party chooses not to renew.', '2026-09-28T09:02:40Z', '2026-09-28T09:02:40Z');

-- ---------------------------------------------------------------- renewals (calculated)
INSERT INTO renewals (id, contract_version_id, effective_date, expiration_date, expiration_source,
    renewal_type, renewal_period_value, renewal_period_unit, current_term_end,
    notice_period_value, notice_period_unit, notice_anchor, notice_deadline,
    calculation_status, calculation_note, calculated_at) VALUES
 ('ren_acme_1', 'ver_acme_1', '2025-01-31', '2027-01-31', 'explicit',
  'automatic', 12, 'months', '2027-01-31',
  90, 'days', 'expiration_date', '2026-11-02',
  'calculated', NULL, '2026-09-29T14:10:00Z'),
 ('ren_globex_1', 'ver_globex_1', '2025-01-01', '2026-12-31', 'explicit',
  'automatic', 1, 'years', '2026-12-31',
  NULL, NULL, NULL, NULL,
  'blocked_by_conflict', 'Two notice periods were found (90 days and 60 days). Resolve the clarification question to calculate the notice deadline.',
  '2026-10-01T11:04:00Z');

-- ---------------------------------------------------------------- citations
INSERT INTO citations (id, contract_version_id, entity_type, entity_id, segment_id, page, section,
    source_text, char_start, char_end, validation_status) VALUES
 ('cit_acme_party_1', 'ver_acme_1', 'extracted_item', 'itm_acme_party_1', 'seg_acme_1', 1, 'Preamble',
  'Acme Corporation ("Customer")', 101, 130, 'verified'),
 ('cit_acme_party_2', 'ver_acme_1', 'extracted_item', 'itm_acme_party_2', 'seg_acme_1', 1, 'Preamble',
  'Example Services Ltd. ("Service Provider")', 135, 177, 'verified'),
 ('cit_acme_eff', 'ver_acme_1', 'extracted_item', 'itm_acme_eff', 'seg_acme_1', 1, 'Preamble',
  'as of January 31, 2025 (the "Effective Date")', 40, 85, 'verified'),
 ('cit_acme_exp', 'ver_acme_1', 'extracted_item', 'itm_acme_exp', 'seg_acme_2', 2, '2.1 Term',
  'expire on January 31, 2027', 76, 102, 'verified'),
 ('cit_acme_ren', 'ver_acme_1', 'extracted_item', 'itm_acme_ren', 'seg_acme_3', 2, '2.2 Renewal',
  'shall automatically renew for successive twelve (12) month periods', 15, 81, 'verified'),
 ('cit_acme_notice', 'ver_acme_1', 'extracted_item', 'itm_acme_notice', 'seg_acme_3', 2, '2.2 Renewal',
  'at least ninety (90) days before the expiration of the then-current term', 141, 213, 'verified'),
 ('cit_acme_obl_report', 'ver_acme_1', 'obligation', 'obl_acme_report', 'seg_acme_4', 12, '4.2 Reporting Obligations',
  'Service Provider shall submit a compliance report to Customer within thirty (30) days after the end of each calendar quarter.', 0, 125, 'verified'),
 ('cit_acme_obl_ins', 'ver_acme_1', 'obligation', 'obl_acme_insurance', 'seg_acme_5', 13, '6.1 Insurance',
  'Service Provider shall deliver a current certificate of insurance to Customer annually', 0, 86, 'verified'),
 ('cit_acme_obl_nonren', 'ver_acme_1', 'obligation', 'obl_acme_nonrenewal', 'seg_acme_3', 2, '2.2 Renewal',
  'unless either party provides written notice of non-renewal at least ninety (90) days before the expiration of the then-current term', 82, 213, 'verified'),
 ('cit_globex_party_1', 'ver_globex_1', 'extracted_item', 'itm_globex_party_1', 'seg_globex_1', NULL, '1. Parties',
  'Globex Inc. ("Client")', 58, 80, 'verified'),
 ('cit_globex_party_2', 'ver_globex_1', 'extracted_item', 'itm_globex_party_2', 'seg_globex_1', NULL, '1. Parties',
  'Initech Hosting LLC ("Provider")', 85, 117, 'verified'),
 ('cit_globex_eff', 'ver_globex_1', 'extracted_item', 'itm_globex_eff', 'seg_globex_1', NULL, '1. Parties',
  'made on January 1, 2025', 26, 49, 'verified'),
 ('cit_globex_exp', 'ver_globex_1', 'extracted_item', 'itm_globex_exp', 'seg_globex_2', NULL, '3.2 Renewal',
  'expires on December 31, 2026', 14, 42, 'verified'),
 ('cit_globex_ren', 'ver_globex_1', 'extracted_item', 'itm_globex_ren', 'seg_globex_2', NULL, '3.2 Renewal',
  'renews automatically for one (1) year', 47, 84, 'verified'),
 ('cit_globex_notice_90', 'ver_globex_1', 'extracted_item', 'itm_globex_notice_90', 'seg_globex_2', NULL, '3.2 Renewal',
  'at least ninety (90) days prior to expiration', 127, 172, 'verified'),
 ('cit_globex_notice_60', 'ver_globex_1', 'extracted_item', 'itm_globex_notice_60', 'seg_globex_3', NULL, '12.1 Notices',
  'no later than sixty (60) days before the expiration date', 44, 100, 'verified'),
 ('cit_globex_clq_90', 'ver_globex_1', 'clarification_question', 'clq_globex_notice', 'seg_globex_2', NULL, '3.2 Renewal',
  'at least ninety (90) days prior to expiration', 127, 172, 'verified'),
 ('cit_globex_clq_60', 'ver_globex_1', 'clarification_question', 'clq_globex_notice', 'seg_globex_3', NULL, '12.1 Notices',
  'no later than sixty (60) days before the expiration date', 44, 100, 'verified');

-- ---------------------------------------------------------------- clarification
INSERT INTO clarification_questions (id, contract_version_id, kind, field_name, question, status,
    resolution_json, resolution_note, created_at, resolved_at) VALUES
 ('clq_globex_notice', 'ver_globex_1', 'conflict', 'notice_period',
  'Two sections specify different notice periods (90 days in 3.2 Renewal, 60 days in 12.1 Notices). Which provision should be treated as the applicable notice rule?',
  'open', NULL, NULL, '2026-10-01T11:04:00Z', NULL);

INSERT INTO clarification_options (clarification_id, entity_type, entity_id) VALUES
 ('clq_globex_notice', 'extracted_item', 'itm_globex_notice_90'),
 ('clq_globex_notice', 'extracted_item', 'itm_globex_notice_60');

-- ---------------------------------------------------------------- review history
INSERT INTO reviews (id, entity_type, entity_id, action, previous_review_status, new_review_status,
    previous_value_json, new_value_json, note, clarification_id, reviewed_at) VALUES
 ('rev_acme_eff', 'extracted_item', 'itm_acme_eff', 'approve', 'pending', 'approved',
  NULL, NULL, NULL, NULL, '2026-09-29T14:10:00Z');
