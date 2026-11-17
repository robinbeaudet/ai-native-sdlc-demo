---
title: Require a cost center on claims over €100
intent: sdlc/intents/intent-002-cost-center-over-100.md
spec: sdlc/specs/spec-002-cost-center-over-100.md
status: approved
approved_by: Robin Beaudet
approved_at: 2026-11-17T16:11:00Z
---

# Plan 002: Require a cost center on claims over €100

## Steps (in order)

| # | Path | Change | Reason |
|---|---|---|---|
| 1 | — | `uv run alembic upgrade head` on a fresh `expense_flow.db` (done at branch creation) | Migration must start from `main`'s schema |
| 2 | `src/expense_flow/models.py` | Add `cost_center: Mapped[str \| None] = mapped_column(String(7))` after `receipt_url` | Spec §2 |
| 3 | `alembic/versions/<rev>_add_cost_center_to_expense_claims.py` | Autogenerate, then read and fix: nullable `add_column`, no `server_default`; `downgrade()` drops exactly that column (batch mode if SQLite needs it) | Spec §3 |
| 4 | `src/expense_flow/schemas.py` | `ExpenseClaimCreate.cost_center: str \| None = Field(default=None, max_length=64)` + `field_validator` turning blank strings into `None`; `ExpenseClaimRead.cost_center: str \| None` | Spec §4 |
| 5 | `src/expense_flow/policy.py` | `COST_CENTER_THRESHOLD = Decimal("100.00")`, `COST_CENTER_PATTERN = re.compile(r"CC-\d{4}", re.ASCII)`; in `evaluate_submission`, after the existing rules: `INVALID_COST_CENTER` if supplied and not `fullmatch`, else `COST_CENTER_REQUIRED` if `amount > threshold` and `None`. Update docstring table | Spec §5 |
| 6 | `src/expense_flow/service.py`, `router.py` | No change (`ExpenseClaim(**payload.model_dump())` already carries the new field) | — |
| 7 | `tests/conftest.py` | `submit_claim` default payload gets `"cost_center": "CC-1234"` | Spec §7 (behaviour change) |
| 8 | `tests/unit/test_policy.py` | `claim()` helper gets `cost_center="CC-1234"` default; add threshold boundary, format, every-category and combined-violation tests | Spec §7 |
| 9 | `tests/unit/test_schemas.py` | Blank → `None`, non-blank kept verbatim, 65 chars refused | Spec §7 |
| 10 | `tests/integration/test_claims_api.py` | `test_claim_over_maximum_is_rejected` sends `CC-1234`; add API tests for `100.00`/`100.01`, valid round-trip via `GET`, `cc-1234`, and VP approval of a `NULL` cost-center row inserted directly | Spec §7 |
| 11 | `tests/integration/test_migrations.py` | Add test: row inserted at baseline survives upgrade with `cost_center` NULL; after `downgrade -1` the column is gone and the row remains | Spec §7 |
| 12 | `README.md` | Policy table: `COST_CENTER_REQUIRED`, `INVALID_COST_CENTER`; data model table: `cost_center` | Spec §8 |

## Alembic commands
```bash
uv run alembic revision --autogenerate -m "add cost_center to expense_claims"
# read and fix the generated file
uv run alembic upgrade head
uv run alembic downgrade -1
uv run alembic upgrade head
uv run alembic check          # "No new upgrade operations detected"
```

## Verification
```bash
uv run ruff check .
uv run ruff format .
uv run pytest
```
All green, then `git add -A && git commit -m "feat(002-cost-center-over-100): ..."` (the
reviewer agent runs before the commit).
