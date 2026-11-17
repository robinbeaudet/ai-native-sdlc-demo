---
title: Core expense submission and approval policy
workflow_mode: gated
ticket_tag: STANDARD
target_branch: dev
status: merged
created: 2026-11-17
---

# Intent 001: Core expense submission and approval policy

> Baseline intent, recorded when the repository was bootstrapped. It documents the
> behaviour of the initial code; it has no spec or plan of its own.

## Business driver

Finance processes about 4,000 expense claims a month by email and spreadsheet. Approvals
are inconsistent, receipts go missing, and last quarter's audit found three claims over
EUR 500 approved by line managers without VP sign-off. We need one system that applies
the expense policy the same way every time and records who approved what, and when.

## User impact

- **Employees** submit a claim and get an immediate, explicit answer if it breaks policy
  (for example "receipt required"), instead of a rejection days later.
- **Managers** can approve routine claims; the system stops them approving claims above
  their authority.
- **VPs** approve high-value claims.
- **Finance and audit** get an exact, tamper-evident record: amounts with no rounding
  drift, approver identity and role, decision timestamps.

## Functional requirements

1. An employee submits a claim: employee id, category (MEALS, TRAVEL, LODGING, EQUIPMENT,
   OTHER), amount in EUR, description, optional receipt URL.
2. Policy at submission:
   - MEALS claims **over EUR 50.00** require a receipt URL.
   - No single claim may **exceed EUR 2,500.00**.
   - All broken rules are reported at once, each with a stable code.
3. A submitted claim can be approved or rejected exactly once.
4. Claims **over EUR 500.00** can only be approved by someone with the VP role.
5. A rejection must include a reason.
6. Each decision records the approver id, approver role and time (UTC).

## Non-functional requirements

- Amounts are exact to the cent: `decimal.Decimal` end to end, never floating point.
- Amounts travel in the API as decimal strings (`"49.99"`).
- Every schema change ships as a reviewed Alembic migration.

## Non-goals

- Authentication and authorisation (the approver identity is trusted input for now).
- Multi-currency support (EUR only).
- Reimbursement / payment execution.
- Listing, search and reporting endpoints.

## Acceptance criteria

- A MEALS claim of EUR 50.01 without a receipt is refused with `RECEIPT_REQUIRED`;
  EUR 50.00 is accepted.
- A claim of EUR 2,500.01 is refused with `AMOUNT_EXCEEDS_MAXIMUM`.
- A MANAGER approving a EUR 500.01 claim gets `VP_APPROVAL_REQUIRED`, and the claim
  stays SUBMITTED; a VP can then approve it.
- Deciding an already-decided claim returns 409.
- 10,000 claims of EUR 0.01 total exactly EUR 100.00.
