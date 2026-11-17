---
title: Require a cost center on claims over €100
workflow_mode: gated
ticket_tag: STANDARD
target_branch: main
status: captured
created: 2026-11-17
---

# Intent 002: Require a cost center on claims over €100

## Business driver
Finance cannot allocate spending to budgets today: claims carry no cost center, so
larger expenses have to be traced back to a budget by hand. Finance wants every claim
over €100 to name the cost center it is charged to, so spending can be allocated
to budgets.

## User impact
- **Employee**: must enter a cost center when submitting a claim over €100.00. Smaller
  claims can still be submitted without one.
- **Approver (Manager / VP)**: sees the cost center on the claim. The approval flow does
  not change.
- **Finance**: can allocate every new claim over €100.00 to a budget using its cost center.

## Functional requirements
1. A claim has an optional `cost_center` field, sent on submission and returned whenever
   the claim is read.
2. A valid cost center is `CC-` followed by exactly 4 digits (regex `^CC-\d{4}$`), uppercase
   only, e.g. `CC-1234`.
3. On submission, a claim with `amount > Decimal("100.00")` must have a `cost_center`.
   If it is missing or blank, the claim is rejected (`422`) with the violation
   `COST_CENTER_REQUIRED`.
4. The threshold is exclusive: a claim of exactly `Decimal("100.00")` does not need a cost
   center.
5. If a `cost_center` is supplied (for any amount), it must match the format in (2).
   Otherwise the claim is rejected (`422`) with the violation `INVALID_COST_CENTER`.
6. The rule applies to every category.
7. Claims already in the database are left as they are: their cost center is empty, and
   they can still be approved or rejected as before.
8. The new rule is reported together with any other policy violations on the same
   submission (e.g. a €60 meal with no receipt and an invalid cost center gets both
   violations).

## Non-goals
- Checking cost centers against a list of real cost centers or budgets.
- Backfilling cost centers on existing claims, or blocking the approval of existing
  claims that have none.
- Budget tracking, reporting or allocation features.
- Editing the cost center of a claim after submission.
- Any change to the receipt, maximum-amount or VP-approval rules.

## Acceptance criteria
| Amount | `cost_center` | Result |
|---|---|---|
| `100.00` | none | Accepted |
| `99.99` | none | Accepted |
| `100.01` | none | `422`, `COST_CENTER_REQUIRED` |
| `100.01` | `""` or `"   "` | `422`, `COST_CENTER_REQUIRED` |
| `100.01` | `CC-1234` | Accepted, `cost_center` returned as `CC-1234` |
| `2500.00` | `CC-0001` | Accepted |
| `100.01` | `cc-1234` | `422`, `INVALID_COST_CENTER` |
| `100.01` | `CC-123` or `CC-12345` | `422`, `INVALID_COST_CENTER` |
| `50.00` | `ABC` | `422`, `INVALID_COST_CENTER` |
| `50.00` | `CC-1234` | Accepted |

- An existing claim of €300.00 with no cost center (created before this change) can still
  be approved by a VP.
- `GET /claims/{id}` returns `cost_center` (or `null` when there isn't one).
