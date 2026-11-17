---
name: ai-native-sdlc-demo-run-intent
description: "Deliver an intent of expense-flow-api end to end: spec, plan, implementation, verification, review and a draft PR to main. Gated intents pause for human approval after each step; autonomous ([LLM]) intents run straight through. Use when asked to run, implement or deliver an intents/intent-*.md file."
---

# Run an intent (AI-native SDLC, stages 2 to 6)

You take one intent file through the lifecycle:

```
intent -> spec (GA-2) -> plan (GA-3) -> code + tests + migration -> commit (reviewer) -> PR (GA-4)
```

## 0. Read the intent and pick the mode

- Read the intent file you were given, `CLAUDE.md` and `REVIEW.md`.
- `<slug>` is the file name without `intent-` and `.md` (e.g. `002-cost-center`).
- **Autonomous** if `workflow_mode: autonomous` or `ticket_tag: LLM`; otherwise **gated**.
  Tell the user which mode you are running in.

**Gated:** at each gate (GA-2, GA-3, GA-4) summarise what the human must check, then ask
with AskUserQuestion: *Approve* / *Request changes*. On changes, apply them (or let the
user edit the file), and ask again. Never continue without an explicit approval.

**Autonomous:** don't ask. Record `approved_by: claude (autonomous)` at GA-2 and GA-3, and
skip GA-4. Stop and ask the human only when you are blocked (see "When to stop").

## 1. Branch

```bash
git switch main && git pull && git switch -c feature/<slug>   # or switch to it if it exists
git add intents/intent-<slug>.md && git commit -m "docs(intent): <slug>"
```

## 2. Spec: `specs/spec-<slug>.md` (GA-2)

Frontmatter: `title`, `intent: intents/intent-<slug>.md`, `status: draft`. Sections:

1. Summary
2. Data model changes: exact SQLAlchemy columns (name, type, nullable, default)
3. Migration strategy: what happens to existing rows, `server_default` for new NOT NULL
   columns, and how `downgrade()` restores the previous schema
4. API contract changes: Pydantic schemas, status codes, violation codes
5. Business rules: exact `Decimal` thresholds, and whether each comparison is `>` or `>=`
6. Edge cases: existing rows, boundary amounts, already-decided claims
7. Test plan: unit, integration, eval, migration
8. README updates
9. Out of scope

Commit it (`docs(spec): <slug>`). **GA-2:** the human checks above all the migration
strategy and the exact thresholds. Once approved, set `status: approved`, `approved_by`
(`git config user.name`, or `claude (autonomous)`) and `approved_at` (UTC), and commit
(`docs(spec): approve <slug>`).

## 3. Plan: `plans/plan-<slug>.md` (GA-3)

Same frontmatter. An ordered checklist of file changes (path, change, reason), the exact
Alembic commands, the tests to add and the verification commands. Commit, run **GA-3**
like GA-2, and commit the approval.

## 4. Implement

Follow the approved plan and every rule in `CLAUDE.md`:
- money is `Decimal`, never `float`;
- a `models.py` change ships with an Alembic migration (CLAUDE.md section 4), read and fixed
  by you before use;
- tests for every behaviour in the spec's test plan, including the boundaries;
- `README.md` updated (endpoints, policy rules, data model).

Then loop until all three are green: `uv run ruff check .`, `uv run ruff format .`,
`uv run pytest`. Never weaken a test to get green.

## 5. Commit: the reviewer agent decides

```bash
git add -A && git commit -m "feat(<slug>): <title>"
```

The pre-commit hook runs the **reviewer agent** (checklist: `REVIEW.md`) before the commit.
If it blocks the commit, fix every Important finding, re-run the gates and commit again.

## 6. Pull request (GA-4)

**GA-4 (gated only):** show the user `git diff main --stat`, the reviewer's verdict and what
changed for the business. Push only after approval.

```bash
git push -u origin feature/<slug>
gh pr create --draft --base main --title "<title>" --body "<summary + links to intent, spec, plan>"
```

Finish with the PR link. On GitHub, Claude reviews the PR automatically, and
`@claude <request>` makes Claude push fixes.

## When to stop and ask a human (both modes)

- The gates are still red after 3 fix attempts.
- The reviewer blocks the commit twice in a row.
- The intent or spec is ambiguous in a way that changes behaviour (amounts, `>` vs `>=`).
- The change would touch `.claude/`, `scripts/`, `.github/`, `CLAUDE.md` or `REVIEW.md`.
- `git push` or `gh` fails.
