# Terminology

**Contract** — Logical agreement tracked by the application.

**Contract Version** — A specific uploaded document belonging to a contract.

**Extracted Item** — A structured value identified from a document, such as a party or date.

**Obligation** — A contractual requirement that must be performed by a party.

**Renewal** — A contractual mechanism that extends the agreement.

**Notice Period** — A period or rule defining when notice must be provided.

**Citation** — Evidence linking an extracted item to document version, page, section, and source text.

**Confidence** — AI confidence in an extraction: high, medium, or low.

**Review Status** — Human workflow state: pending, approved, edited, or rejected.

**Potentially Stale** — Information from an earlier version that may no longer represent the current contract.

**Clarification Question** — A question created when information is ambiguous, conflicting, or insufficiently supported.

**Segment**: a small piece of a document's parsed text (with page and section). Citations point at segments.

**Notice Deadline**: the last day on which notice can be given, calculated by the backend.

**Current Term End**: the expiration date, rolled forward by renewal periods if the contract auto-renewed.

**Lifecycle Status**: calculated contract state: active, expiring_soon, expired, unknown.

**Obligation Status**: operational state of an obligation (open, completed, not_applicable). This is separate from review status.

**Calculation Status**: whether a renewal could be calculated (calculated, incomplete, blocked_by_conflict).
