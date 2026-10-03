# Contract Obligation and Renewal Assistant

## 1. Overview

The Contract Obligation and Renewal Assistant is a web application that
helps users upload contracts, extract important contractual information,
identify obligations, calculate renewal/notice dates, and review AI-generated
results with source citations.

The application is an information-management and analysis tool.

It is NOT legal advice.

---

## 2. Problem

Important contract information is often distributed across lengthy documents.

Users need to quickly identify:

- Contract parties
- Effective date
- Expiration date
- Renewal terms
- Notice periods
- Obligations
- Responsible parties
- Important deadlines
- Supporting source text

The system reduces manual contract review by extracting this information
and presenting it in a structured format.

---

## 3. Core Features

### Contract Management

Users can:

- Upload a contract
- View uploaded contracts
- Search contracts
- Filter contracts
- Open contract details
- View contract versions

### Contract Analysis

The system extracts:

- Parties
- Effective date
- Expiration date
- Renewal terms
- Initial term length
- Termination clauses (one-sentence summary, informational only)
- Notice periods
- Obligations
- Responsible parties

Conflicting or ambiguous terms are surfaced as clarification questions and never resolved
silently.

### Obligation Management

Users can:

- View obligations
- View due dates
- View responsible parties
- View obligation status
- Open the source citation

### Renewal Management

The system identifies:

- Expiration dates
- Renewal periods
- Notice periods
- Calculated notice deadlines
- Renewal status

### Human Review

AI-generated information must be reviewable.

Users can:

- Approve
- Reject
- Edit
- Save changes
- Resolve clarification questions (conflicts, ambiguities, missing information)

Each extracted item should have:

- Confidence
- Review status
- Source citation

---

## 4. Non-Goals

For the initial version:

- No legal advice
- No legal interpretation
- No automated legal decisions
- No multi-user permission system
- No complex authentication
- No OCR requirement
- No advanced analytics
- No external calendar integration
- No email notification system

---

## 5. Initial Screens

The MVP contains:

1. Dashboard
2. Contracts
3. Upload Contract
4. Analysis Progress
5. Contract Details
6. Obligations
7. Renewals
8. Review

Contract Details contains:

- Overview
- Extracted Information
- Obligations
- Versions

---

## 6. Supported Documents

Initial supported formats:

- PDF (text-based; scanned PDFs are not supported because there is no OCR)
- DOCX

Maximum 20 MB per file.

---

## 7. Success Criteria

The prototype should demonstrate:

1. Contract upload
2. Contract analysis
3. Structured extraction
4. Obligation detection
5. Renewal/notice information
6. Source citations
7. Confidence values
8. Human review
9. Contract version handling

The system should provide traceability from an extracted value back to
the original document.