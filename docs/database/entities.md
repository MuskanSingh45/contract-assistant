# Database Entities

**Contract**: logical agreement. Display fields are derived from its latest version.

**ContractVersion**: one uploaded document. It is never overwritten. It carries the analysis status/stage.

**DocumentSegment**: a piece of a version's normalized text (page, section heading, text). It is what citations point at.

**ExtractedItem**: an AI-extracted fact (party, dates, term, renewal terms, notice period, termination clause). It has a current value, the original AI value, confidence and review status.

**Obligation**: a contractual requirement with responsible party, rule (frequency/due rule), due date, operational status, confidence and review status.

**Renewal**: the calculated renewal/notice result for a version. It is deterministic output, not AI output.

**Citation**: evidence quote plus segment/page/section for an item, obligation or clarification, with a validation status.

**ClarificationQuestion**: a conflict, ambiguity or missing input that needs a human decision. Its options are linked through **ClarificationOption**.

**Review**: one human action (approve/edit/reject) in the append-only history.

**VersionChange**: one added/removed/modified difference between a version and its predecessor.

Table details: [schema.md](schema.md).
