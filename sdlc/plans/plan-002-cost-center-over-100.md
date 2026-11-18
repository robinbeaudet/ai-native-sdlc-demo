---
title: Require a cost center on claims over EUR 100
intent: sdlc/intents/intent-002-cost-center-over-100.md
spec: sdlc/specs/spec-002-cost-center-over-100.md
status: approved
approved_by: Robin Beaudet
approved_at: 2026-11-18T16:16:23Z
---

# Plan 002: Require a cost center on claims over EUR 100

## Checklist

1. [ ] **Database up to date.** `uv run alembic upgrade head` (fresh `expense_flow.db`,
   baseline revision `e44d115a61f1`).
2. [ ] **`src/expense_flow/models.py`**: add
   `cost_center: Mapped[str | None] = mapped_column(String(7))` after `receipt_url`.
   Reason: spec §2.
3. [ ] **Migration.** `uv run alembic revision --autogenerate -m "add cost_center to expense_claims"`,
   then read and fix the file:
   - `upgrade()`: only `batch_alter_table` + `add_column("cost_center", String(7), nullable=True)`;
     no `server_default` (nullable column, spec §3).
   - `downgrade()`: only `drop_column("cost_center")`.
   - Remove anything else autogenerate may have added.
   Then `uv run alembic upgrade head`, `uv run alembic downgrade -1`,
   `uv run alembic upgrade head`, `uv run alembic check` ("No new upgrade operations detected").
4. [ ] **`src/expense_flow/schemas.py`**: `ExpenseClaimCreate.cost_center: str | None = None`
   (no length/pattern constraint, spec §4); `ExpenseClaimRead.cost_center: str | None`.
5. [ ] **`src/expense_flow/policy.py`**: add `COST_CENTER_THRESHOLD = Decimal("100.00")` and
   `COST_CENTER_PATTERN = re.compile(r"CC-[0-9]{4}")`; in `evaluate_submission`, after the
   existing two rules, append `COST_CENTER_INVALID` (given and not `fullmatch`) or else
   `COST_CENTER_REQUIRED` (`amount > COST_CENTER_THRESHOLD` and `cost_center is None`).
   Update the module docstring table. Reason: spec §5.
6. [ ] **`service.py` / `router.py`**: no change (`ExpenseClaim(**payload.model_dump())` already
   carries the new field; no business rule goes there).
7. [ ] **Tests** (spec §7):
   - `tests/unit/test_policy.py`: `claim()` helper gets a `cost_center=None` parameter;
     new parametrised tests for the required rule (99.99, 100.00, 100.01, 100.01 + `CC-1234`)
     and the format rule (`cc-1234`, `CC-123`, `CC-12345`, `1234`, `""`, `"   "`, `" CC-1234"`,
     `"CC-1234 "` at 100.01 and 50.00; `CC-0000`, `CC-9999`, `CC-1234` at 50.00 valid);
     combined MEALS 120.00 test. Update `test_maximum_claim_rule` (pass `CC-1234`) and
     `test_a_claim_can_break_several_rules` (expects `COST_CENTER_REQUIRED` too).
   - `tests/unit/test_schemas.py`: `cost_center` defaults to `None`.
   - `tests/conftest.py`: `submit_claim` default payload gets `"cost_center": "CC-1234"`.
   - `tests/integration/test_claims_api.py`: 100.01 without → 422 `COST_CENTER_REQUIRED`;
     100.00 without → 201 with `cost_center: null`; 100.01 + `cc-1234` → 422
     `COST_CENTER_INVALID`; 100.01 + `CC-1234` → 201 and round-trips through `GET`;
     `test_claim_over_maximum_is_rejected` sends `CC-1234`.
   - `tests/integration/test_migrations.py`: new test — upgrade to `e44d115a61f1`, insert a
     claim with raw SQL, upgrade to head (row intact, `cost_center` NULL), downgrade to
     `e44d115a61f1` (column gone, row intact).
8. [ ] **`README.md`**: policy table (two new codes) and data model table (`cost_center`).
   Reason: CLAUDE.md rule 4, spec §8.
9. [ ] **Verify**: `uv run ruff check .`, `uv run ruff format .`, `uv run pytest` until green.
10. [ ] **Commit** `feat(002-cost-center-over-100): require a cost center on claims over EUR 100`
    (reviewer agent runs in the pre-commit hook).

## Files not touched

`.claude/`, `.github/`, `scripts/`, `REVIEW.md`, `CLAUDE.md`, `service.py`, `router.py`,
`main.py`, the baseline migration.
