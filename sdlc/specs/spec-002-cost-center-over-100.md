---
title: Require a cost center on claims over €100
intent: sdlc/intents/intent-002-cost-center-over-100.md
status: draft
---

# Spec 002: Require a cost center on claims over €100

## 1. Summary
Claims get an optional `cost_center` field (format `CC-` + 4 digits). On submission, a
claim with `amount > Decimal("100.00")` must have one (`COST_CENTER_REQUIRED`), and any
cost center that is supplied must have the right format (`INVALID_COST_CENTER`). Existing
claims are untouched. Approval and rejection do not change.

## 2. Data model changes
Table `expense_claims`, one new column in `models.py`:

```python
cost_center: Mapped[str | None] = mapped_column(String(7))
```

| Name | Type | Nullable | Default | server_default |
|---|---|---|---|---|
| `cost_center` | `VARCHAR(7)` | yes | none (`NULL`) | none |

Nullable on purpose: existing claims and claims of €100.00 or less have no cost center.
The "required over €100" rule is a business rule in `policy.py`, not a database
constraint. 7 characters is the exact length of a valid value (`CC-1234`), and only valid
values are ever stored.

## 3. Migration strategy
New revision `add cost_center to expense_claims`, `down_revision = e44d115a61f1`.

- `upgrade()`: `op.add_column("expense_claims", sa.Column("cost_center", sa.String(length=7), nullable=True))`.
- Existing rows: get `NULL`. No backfill and no `server_default` is needed, because the
  column is nullable. No data is changed or dropped.
- `downgrade()`: `op.drop_column("expense_claims", "cost_center")`, which restores the
  baseline schema exactly. (Downgrading loses the cost centers entered after upgrading;
  that is inherent to a downgrade and acceptable.)
- SQLite: `add_column` of a nullable column needs no batch mode. `drop_column` is
  supported natively by SQLite 3.35+; if Alembic needs it, use
  `with op.batch_alter_table("expense_claims") as batch: batch.drop_column("cost_center")`.

## 4. API contract changes
`ExpenseClaimCreate` (request body of `POST /claims`):

```python
cost_center: str | None = Field(default=None, max_length=64)
```

- A blank value (`""` or whitespace only) is normalised to `None` by a
  `field_validator` (it counts as "no cost center", as the intent asks).
- A non-blank value is kept **as is**: no trimming, no upper-casing. `" CC-1234"` and
  `"cc-1234"` are invalid.
- `max_length=64` is only a sanity bound on the input size. Any string up to 64 characters
  reaches the policy, so a wrong format always returns the `INVALID_COST_CENTER` violation
  code rather than a generic schema error. Over 64 characters: the usual schema `422`
  (no violation code), like other oversized fields.

`ExpenseClaimRead` (responses of `POST /claims`, `GET /claims/{id}`, approve, reject):

```python
cost_center: str | None
```

Returned as `null` when the claim has none.

Status codes and violations (in the existing `422` body, `violations: [{code, message}]`):

| Code | When | Message |
|---|---|---|
| `COST_CENTER_REQUIRED` | `amount > 100.00` and no cost center (missing, `null` or blank) | `Claims over EUR 100.00 require a cost_center` |
| `INVALID_COST_CENTER` | a cost center is supplied and does not match `^CC-\d{4}$` | `cost_center must be CC- followed by 4 digits, e.g. CC-1234` |

No new endpoint. No change to approve or reject.

## 5. Business rules
In `policy.py`, inside `evaluate_submission`:

- `COST_CENTER_THRESHOLD = Decimal("100.00")`; the comparison is **strictly `>`**:
  `claim.amount > COST_CENTER_THRESHOLD and claim.cost_center is None`
  → `COST_CENTER_REQUIRED`. `100.00` passes, `100.01` fails.
- `COST_CENTER_PATTERN = re.compile(r"CC-\d{4}", re.ASCII)`, checked with `fullmatch`
  (`re.ASCII` so that `\d` means only `0-9`, not other Unicode digits):
  `claim.cost_center is not None and not COST_CENTER_PATTERN.fullmatch(claim.cost_center)`
  → `INVALID_COST_CENTER`. This applies at any amount, in every category.
- The two codes are mutually exclusive: "required" only fires with no cost center,
  "invalid" only with one.
- Order of violations in the list: `RECEIPT_REQUIRED`, `AMOUNT_EXCEEDS_MAXIMUM`, then the
  cost-center violation. All violations are reported together.
- Update the module docstring table in `policy.py`.

## 6. Edge cases
| Case | Result |
|---|---|
| `99.99`, `100.00`, no cost center | accepted, `cost_center: null` |
| `100.01`, no cost center / `null` / `""` / `"   "` | `422`, `COST_CENTER_REQUIRED` |
| `100.01`, `CC-1234` | `201`, `cost_center: "CC-1234"` |
| `2500.00`, `CC-0001` | `201` |
| `100.01`, `cc-1234`, `CC-123`, `CC-12345`, `" CC-1234"`, `CC-١٢٣٤` (Arabic-Indic digits) | `422`, `INVALID_COST_CENTER` |
| `50.00`, `ABC` | `422`, `INVALID_COST_CENTER` |
| `50.00`, `""` | `201`, `cost_center: null` |
| `MEALS`, `60.00`, no receipt, `ABC` | `422`, `[RECEIPT_REQUIRED, INVALID_COST_CENTER]` |
| `EQUIPMENT`, `3000.00`, no cost center | `422`, `[AMOUNT_EXCEEDS_MAXIMUM, COST_CENTER_REQUIRED]` |
| Existing claim of `300.00` with `cost_center = NULL` | can be approved by a VP and rejected as before; `GET` returns `cost_center: null` |
| Already-decided claims | unchanged (`409` on a second decision) |

## 7. Test plan
**Unit** (`tests/unit/test_policy.py`, `tests/unit/test_schemas.py`):
- Threshold boundary: `99.99`, `100.00` with no cost center → no violation; `100.01` →
  `COST_CENTER_REQUIRED`; `100.01` with `CC-1234` → none.
- Format: valid `CC-0000`, `CC-1234`, `CC-9999`; invalid `cc-1234`, `CC-123`, `CC-12345`,
  `CC1234`, `" CC-1234"`, `"CC-1234 "`, `CC-12a4`, Unicode digits; also invalid on a `50.00` claim.
- Rule applies to every category (parametrised over `ExpenseCategory`).
- Combined violations (meal + invalid cost center; over maximum + missing cost center).
- Schema: `""` and `"   "` become `None`; non-blank values are not modified; 65
  characters are refused.

**Integration** (`tests/integration/test_claims_api.py`):
- `POST /claims` `100.01` without cost center → `422` + `COST_CENTER_REQUIRED`;
  `100.00` without → `201` with `cost_center: null`; `100.01` with `CC-1234` → `201` and
  `GET` returns `CC-1234`; `cc-1234` → `422` + `INVALID_COST_CENTER`.
- A claim of `300.00` inserted directly in the database with `cost_center = NULL` (as an
  existing row would be) can be approved by a VP.

**Eval** (`tests/evals/`): no new eval; the existing ones must stay green (no `float`).

**Migration** (`tests/integration/test_migrations.py`): the existing tests cover
`alembic check` and upgrade/downgrade/upgrade. Add a test that a row inserted at the
baseline revision survives the upgrade with `cost_center = NULL`, and that after
`downgrade -1` the column is gone and the row is still there.

**Existing tests updated because the expected behaviour changes** (not weakened):
- `submit_claim` fixture (`tests/conftest.py`) and the `claim()` helper in
  `tests/unit/test_policy.py`: default `cost_center="CC-1234"`, since their default or
  overridden amounts (`120.00`, `400.00`, `2500.00`, ...) are over €100 and would otherwise
  hit the new rule. Tests can still pass `cost_center=None` explicitly.
- `test_claim_over_maximum_is_rejected` (`2500.01`): send a valid cost center, so it still
  asserts exactly `["AMOUNT_EXCEEDS_MAXIMUM"]`.

## 8. README updates
- Expense policy table: add `COST_CENTER_REQUIRED` (on submission: claims over €100.00 need
  a `cost_center`) and `INVALID_COST_CENTER` (on submission: a `cost_center`, if given, must
  be `CC-` + 4 digits). Note the exclusive threshold.
- Data model table: add `cost_center` (text, optional, `CC-1234`; empty on claims created
  before this change).

## 9. Out of scope
Validating against a list of real cost centers; backfilling existing claims; blocking
the approval of existing claims without a cost center; editing a cost center after
submission; budget reporting; any change to the other rules.
