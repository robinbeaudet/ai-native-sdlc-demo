# Review instructions

Review like a skeptical senior engineer: this is a financial system, and the author
(often an AI agent) may be confidently wrong. The project rules are in `CLAUDE.md`.

## Always check

1. **The spec is respected.** Every requirement in the matching `sdlc/specs/spec-*.md` is
   implemented, with the exact amounts and the right comparison (`>` or `>=`). Nothing extra.
2. **Money is exact.** No `float` anywhere near amounts. `Decimal` values are written as strings.
3. **Migrations are safe.** A change to `models.py` comes with an Alembic migration. A new
   required column has a default for existing rows. No data is dropped unless the spec says so.
4. **Tests prove it.** New rules are tested at the boundary (exactly at the threshold, and
   0.01 either side). No existing test was removed or weakened.
5. **Docs are updated.** The README tables (endpoints, policy rules, data model) match the code.

Mark a problem with any of these as **Important**.

## Do not report

- Formatting and import order (`ruff` checks them in CI).
- `uv.lock` contents.

## Cap the nits

Report at most five Nits per review.
