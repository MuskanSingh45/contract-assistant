# Frontend Components

Components by area. File names in `frontend/src/components/` may differ slightly; the behaviour below exists.

## Layout
- AppShell, Navigation (Dashboard, Contracts, Obligations, Renewals, Review with pending count), Header

## Contracts
- ContractTable, ContractStatusBadge (lifecycle), ContractOverview, VersionSelector

## Upload / Analysis
- FileDropzone, AnalysisProgress (stepper), AnalysisSummary

## Extraction & citations
- ExtractedField, ConfidenceBadge, ReviewStatusBadge, SourceCitation (section · page + "View source"), SourceDrawer, CitationWarning (not_found)

## Obligations / Renewals
- ObligationTable, ObligationStatusSelect (PATCH), RenewalTable, DeadlineCell ("in N days", overdue style, "unreviewed" hint)

## Review
- ReviewQueue, ReviewItem, ReviewActions (approve/edit/reject), EditValueForm (per field_name), ReviewHistory
- ClarificationList, ClarificationCard (options side by side, select / custom / dismiss)

## Versions
- VersionList, VersionUpload, VersionChanges (added/removed/modified, potentially stale tag)
