# CLAUDE.md: rules for working on expense-flow-api

These rules apply to every change, made by a human or by Claude.

## Commands

Always use `uv`:

- Install: `uv sync`
- Check: `uv run ruff check .`, `uv run ruff format .`, `uv run pytest`
- Database: `uv run alembic upgrade head` (migrations: see below)
- Run the API: `uv run uvicorn expense_flow.main:app --reload`

## Code map

- `src/expense_flow/policy.py`: business rules, as pure functions
- `src/expense_flow/models.py`: database tables; `schemas.py`: API request and response bodies
- `src/expense_flow/service.py`, `router.py`: use cases and HTTP routes (no business rules here)
- `alembic/versions/`: database migrations

## Rules

1. **Money is `Decimal`, never `float`.** Write `Decimal("50.00")`. Amounts have 2 decimals.
2. **A table change needs a migration** (see below).
3. **Run the checks before saying "done"** (see Tests below).
4. **Update the README** when endpoints, policy rules or the data model change.
5. **Follow the approved spec.** If it seems wrong, stop and ask.

## Database migrations

Every change to a table in `models.py` ships with an Alembic migration, in the same change:

1. `uv run alembic upgrade head`: your local database must be up to date first.
2. Edit `models.py`.
3. `uv run alembic revision --autogenerate -m "<what changed>"`.
4. **Read the generated file and fix it.** Autogenerate is a draft:
   - A new required (`NOT NULL`) column on an existing table needs a `server_default`
     (or a backfill), otherwise the existing rows break.
   - Never drop a column or a table unless the spec says so: that loses data.
   - `downgrade()` must exactly undo `upgrade()`.
5. Check it: `uv run alembic upgrade head`, then `uv run alembic downgrade -1`, then
   `upgrade head` again. `uv run alembic check` must say "No new upgrade operations detected".

`tests/integration/test_migrations.py` fails if the models and the migrations disagree.

## Tests

- `tests/unit/`: policy rules and validation (fast, no database).
- `tests/integration/`: the HTTP API against a real database, and the migrations.
- `tests/evals/`: money precision (no floats, exact totals).

For every new rule, test the boundary: exactly at the threshold and €0.01 either side
(e.g. `100.00`, `100.01`). For every new API behaviour, test the status code and the
violation code.

Run `uv run ruff check .`, `uv run ruff format .` and `uv run pytest` until all pass.
Never delete, skip or weaken a test to get green. If the spec changes the expected
behaviour, update the test and say so.

## Workflow

- A change goes intent → spec → plan → code → pull request, with the files in `intents/`,
  `specs/` and `plans/`.
  - **Gated** intents: a human approves the spec, the plan and the pull request.
  - **Autonomous** intents (`[LLM]` tickets): Claude goes straight to a draft pull request.
- Work on a `feature/<slug>` branch and merge into `main` through a pull request.
  Never push to `main` directly, never force-push.
- Before each `git commit`, the reviewer agent checks the change (`scripts/review_gate.py`)
  and can block it. Fix what it reports, then commit again. Claude also reviews every
  pull request in GitHub, using `REVIEW.md`.
- Don't change `.claude/`, `.github/`, `scripts/`, `REVIEW.md` or this file unless asked:
  those changes need a human.
