---
title: Require a cost center on claims over EUR 100
workflow_mode: gated
ticket_tag: STANDARD
target_branch: main
status: captured
created: 2026-11-18
---

# Intent 002: Require a cost center on claims over EUR 100

## Business driver

Finance cannot allocate expense spending to departmental budgets: a claim records who
spent the money and on what, but not which budget pays for it. Today Finance chases the
cost center by email after the fact, for every claim large enough to matter. Requiring a
cost center at submission, for every claim over EUR 100.00, lets spending be allocated to
budgets as it comes in.

## User impact

- **Employees** must give a cost center when they submit a claim over EUR 100.00, and get
  an immediate, explicit error if it is missing or malformed. Smaller claims are unchanged.
- **Managers and VPs** see the cost center on the claim they are deciding.
- **Finance** can allocate every claim over EUR 100.00 to a budget without chasing anyone.

## Functional requirements

1. A claim can carry a **cost center**: the text `CC-` (uppercase) followed by exactly
   4 digits, e.g. `CC-1234`.
2. At submission, a claim with **amount > EUR 100.00** must include a cost center.
   A claim of exactly EUR 100.00 does not need one.
3. A cost center, when given, must match the format in requirement 1, whatever the amount.
   A claim of EUR 100.00 or less may omit it.
4. A missing or malformed cost center is a policy violation with its own stable code,
   reported together with any other violations of the claim (as the existing rules are).
5. The cost center is returned when a claim is read.
6. Existing claims, submitted before this change, stay valid and readable even though
   they have no cost center.

## Non-goals

- A list of valid cost centers, or checking that a cost center exists in a Finance system.
- Changing the cost center after submission.
- Budget tracking, reporting or allocation endpoints.
- Back-filling cost centers on existing claims.
- Any change to the approval rules (the EUR 500.00 VP threshold is unchanged).

## Acceptance criteria

- A claim of EUR 100.01 without a cost center is refused (422) with the cost-center
  violation code; with `CC-1234` it is accepted.
- A claim of EUR 100.00 without a cost center is accepted.
- A claim of EUR 99.99 without a cost center is accepted.
- A claim of EUR 100.01 with `cc-1234`, `CC-123`, `CC-12345`, `1234` or a blank value is
  refused (422) with the malformed-cost-center violation code.
- A claim of EUR 50.00 with `CC-12` is refused as malformed: format is checked at any
  amount.
- A MEALS claim of EUR 120.00 with no receipt and no cost center reports both
  `RECEIPT_REQUIRED` and the cost-center violation in one response.
- `GET /claims/{id}` returns the cost center of a claim that has one, and an empty value
  for a claim submitted before this change.
