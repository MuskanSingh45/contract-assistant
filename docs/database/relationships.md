# Database Relationships

```text
contracts 1 ─── N contract_versions

contract_versions 1 ─── N document_segments
contract_versions 1 ─── N extracted_items
contract_versions 1 ─── N obligations
contract_versions 1 ─── 1 renewals                 (calculated; absent until analysis completes)
contract_versions 1 ─── N citations
contract_versions 1 ─── N clarification_questions
contract_versions 1 ─── N version_changes          (as the newer version)

document_segments 1 ─── N citations

citations N ─── 1 {extracted_item | obligation | clarification_question}   (polymorphic: entity_type + entity_id)
reviews   N ─── 1 {extracted_item | obligation}                            (polymorphic: entity_type + entity_id)

clarification_questions 1 ─── N clarification_options ─── 1 {extracted_item | obligation}
clarification_questions 1 ─── N reviews            (reviews created by resolving it)
```

Tree view:

```text
Contract
 └── ContractVersion
      ├── DocumentSegment ◄──────────────┐
      ├── ExtractedItem ── Citation ─────┤
      │        └── Review                │
      ├── Obligation ───── Citation ─────┤
      │        └── Review                │
      ├── ClarificationQuestion ─ Citation┘
      │        └── ClarificationOption → ExtractedItem / Obligation
      ├── Renewal  (calculated from ExtractedItems)
      └── VersionChange → previous version's items
```

Foreign keys enforce every non-polymorphic relationship (`PRAGMA foreign_keys = ON`). The
service layer validates polymorphic `entity_id`s.
