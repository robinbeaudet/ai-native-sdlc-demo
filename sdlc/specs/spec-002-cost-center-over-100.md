---
title: Require a cost center on claims over EUR 100
intent: sdlc/intents/intent-002-cost-center-over-100.md
status: draft
---

# Spec 002: Require a cost center on claims over EUR 100

## 1. Summary

Claims get an optional `cost_center` field, format `CC-` + 4 digits (e.g. `CC-1234`).
At submission, a claim with `amount > 100.00` must carry one; a cost center that is given
must have the right format at any amount. Both rules are policy violations (422 with a
`violations` list), reported together with the existing rules. Existing claims keep
`cost_center = NULL` and stay valid. Approval and rejection are unchanged.

## 2. Data model changes

`src/expense_flow/models.py`, table `expense_claims`, one new column:

| Column | SQLAlchemy | Nullable | Default |
|---|---|---|---|
| `cost_center` | `Mapped[str \| None] = mapped_column(String(7))` | yes | none (`NULL`) |

Why nullable: the field is only required above EUR 100.00, and claims submitted before
this change have no cost center. Nothing else in the table changes.

## 3. Migration strategy

One new Alembic revision, `down_revision = "e44d115a61f1"`:

- `upgrade()`: `batch_alter_table("expense_claims")` → `add_column(sa.Column("cost_center",
  sa.String(length=7), nullable=True))`.
- **Existing rows:** kept as they are, with `cost_center = NULL`. The column is nullable,
  so no `server_default` and no backfill are needed (the intent excludes back-filling).
  Existing claims over EUR 100.00 are **not** re-validated: the rule applies at submission
  only.
- `downgrade()`: `batch_alter_table("expense_claims")` → `drop_column("cost_center")`. This
  restores the baseline schema exactly. Downgrading discards the cost centers recorded
  since the upgrade; that is inherent to undoing the column and is the only data dropped.
- Verified with `upgrade head` → `downgrade -1` → `upgrade head`, and `alembic check`.

## 4. API contract changes

`src/expense_flow/schemas.py`:

- `ExpenseClaimCreate.cost_center: str | None = None`. No length or pattern constraint in
  the schema: the format is checked by the policy, so a bad value returns a violation
  code (requirement 4 of the intent) instead of a generic Pydantic error.
- `ExpenseClaimRead.cost_center: str | None` (returned by every endpoint that returns a
  claim; `null` for claims without one).

Endpoints and status codes are unchanged. `POST /claims` returns `422` with these new
violation codes:

| Code | When |
|---|---|
| `COST_CENTER_REQUIRED` | `amount > 100.00` and `cost_center` is absent or `null` |
| `COST_CENTER_INVALID` | `cost_center` is given (not `null`) and does not match `^CC-[0-9]{4}$` |

At most one of the two is reported per claim.

## 5. Business rules

In `src/expense_flow/policy.py`, inside `evaluate_submission`:

- `COST_CENTER_THRESHOLD = Decimal("100.00")`.
- **Required:** `claim.amount > COST_CENTER_THRESHOLD and claim.cost_center is None`
  → `COST_CENTER_REQUIRED`. Strictly greater: EUR 100.00 needs none, EUR 100.01 does.
- **Format:** `claim.cost_center is not None and not re.fullmatch(r"CC-[0-9]{4}",
  claim.cost_center)` → `COST_CENTER_INVALID`, at any amount.
  - Case-sensitive: `cc-1234` is invalid.
  - No trimming: `" CC-1234"` and `"CC-1234 "` are invalid.
  - `[0-9]`, not `\d`, so non-ASCII digits are invalid.
  - An empty or blank string counts as given, so it is `COST_CENTER_INVALID`, not
    `COST_CENTER_REQUIRED`.
- Order in the `violations` list: `RECEIPT_REQUIRED`, `AMOUNT_EXCEEDS_MAXIMUM`, then the
  cost-center violation (new rules are appended, existing order is unchanged).
- `evaluate_approval` is unchanged.

## 6. Edge cases

| Case | Result |
|---|---|
| EUR 99.99 / 100.00, no cost center | 201 |
| EUR 100.01, no cost center (field absent or `null`) | 422 `COST_CENTER_REQUIRED` |
| EUR 100.01, `CC-1234` | 201, `cost_center` = `"CC-1234"` |
| EUR 100.01, `cc-1234`, `CC-123`, `CC-12345`, `1234`, `""`, `"   "`, `" CC-1234"` | 422 `COST_CENTER_INVALID` |
| EUR 50.00, `CC-12` | 422 `COST_CENTER_INVALID` |
| EUR 50.00, `CC-1234` | 201 (allowed below the threshold) |
| MEALS EUR 120.00, no receipt, no cost center | 422 `RECEIPT_REQUIRED` + `COST_CENTER_REQUIRED` |
| EUR 3,000.00, no cost center | 422 `AMOUNT_EXCEEDS_MAXIMUM` + `COST_CENTER_REQUIRED` |
| Existing claim (pre-migration) over EUR 100.00, no cost center | still readable (`cost_center: null`), can be approved or rejected |
| Already-decided claims | unchanged: 409 on a second decision |

## 7. Test plan

**Unit** (`tests/unit/test_policy.py`):
- Required rule, boundaries: 99.99 / 100.00 → none; 100.01 → `COST_CENTER_REQUIRED`;
  100.01 + `CC-1234` → none.
- Format rule: each invalid value from section 6 → `COST_CENTER_INVALID` (at 100.01 and
  at 50.00); `CC-0000`, `CC-9999` valid.
- Combined: MEALS 120.00 without receipt and cost center → both codes, in order.
- Existing tests whose amount is now over EUR 100.00 without a cost center
  (`test_maximum_claim_rule`, `test_a_claim_can_break_several_rules`): the maximum-rule
  test passes a valid cost center so it still isolates its rule; the several-rules test
  expects the additional `COST_CENTER_REQUIRED` code. **Expected behaviour changed by
  this spec**, not weakened.

**Unit** (`tests/unit/test_schemas.py`): `cost_center` is optional and defaults to `None`.

**Integration** (`tests/integration/test_claims_api.py`):
- 100.01 without cost center → 422 `COST_CENTER_REQUIRED`; 100.00 → 201.
- 100.01 with `cc-1234` → 422 `COST_CENTER_INVALID`.
- 100.01 with `CC-1234` → 201 and `GET /claims/{id}` returns `"CC-1234"`.
- A claim without cost center returns `"cost_center": null`.
- The `submit_claim` fixture (default amount 120.00) gets a default `cost_center` of
  `CC-1234`; `test_claim_over_maximum_is_rejected` sends a cost center so it still
  isolates its rule.

**Migration** (`tests/integration/test_migrations.py`):
- Existing `test_migrations_match_the_models` and `test_upgrade_downgrade_upgrade` cover
  the new revision.
- New: insert a claim at the baseline revision, upgrade to head, check the row is intact
  and `cost_center` is `NULL`; downgrade, check the column is gone and the row is intact.

**Eval** (`tests/evals/`): no new eval; existing ones must stay green (the new code uses
no float, amounts compare as `Decimal`).

## 8. README updates

- Expense policy table: add `COST_CENTER_REQUIRED` (claims over €100.00 need a
  `cost_center`) and `COST_CENTER_INVALID` (format `CC-` + 4 digits, at any amount).
- Data model table: add `cost_center` (text, optional; `CC-1234`; required on submission
  above €100.00; `null` on claims submitted before this rule).

## 9. Out of scope

- A list of valid cost centers, or checking them against a Finance system.
- Changing a cost center after submission; back-filling existing claims.
- Re-validating existing claims at approval.
- Budget tracking, reporting or allocation endpoints.
- Any change to approval rules or other thresholds.
