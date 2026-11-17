# CLAUDE.md: rules for working on expense-flow-api

These rules apply to every change, made by a human or by Claude.

## Commands (always through `uv`)

| Task | Command |
|---|---|
| Install | `uv sync` |
| Lint / format | `uv run ruff check .` / `uv run ruff format .` |
| Test | `uv run pytest` |
| Migrate the database | `uv run alembic upgrade head` |
| New migration | `uv run alembic revision --autogenerate -m "<what changed>"` |
| Run the API | `uv run uvicorn expense_flow.main:app --reload` |

## Where things live

- `src/expense_flow/policy.py`: business rules (pure functions)
- `src/expense_flow/models.py`: database tables. `schemas.py`: API request/response bodies
- `src/expense_flow/service.py` and `router.py`: use cases and HTTP routes (no business rules)
- `alembic/versions/`: database migrations

## Rules

1. **Money is `Decimal`, never `float`.** Write `Decimal("50.00")`. Amounts have 2 decimals.
2. **A table change needs a migration.** After editing `models.py`, generate one with Alembic,
   then read it: a new required column needs a default for existing rows, and `downgrade()`
   must undo `upgrade()`.
3. **Test before you say "done".** Run `ruff check`, `ruff format` and `pytest` until all
   green. Add tests for new behaviour. Never delete or weaken a test to get green.
4. **Keep the README in sync**: endpoints, policy rules and data model.
5. **Follow the approved spec.** If the spec seems wrong, stop and ask.

## How a change is delivered

`intent` -> `spec` -> `plan` -> `code` -> `PR`, as files in `intents/`, `specs/` and `plans/`.

- **Gated** intents: a human approves the spec, the plan and the PR.
- **Autonomous** intents (`[LLM]` tickets): Claude goes straight through to a draft PR.

Branches: `feature/<slug>` -> `dev` -> `main`. Never force-push.

## Reviews

- Before each `git commit`, the **reviewer agent** checks the change and can block it.
  Fix what it reports, then commit again.
- On each PR, **Claude reviews it in GitHub** (`.github/workflows/claude-review.yml`), using `REVIEW.md`.
- Don't change `.claude/`, `scripts/`, `.github/`, `REVIEW.md` or this file unless asked:
  those changes need a human.
