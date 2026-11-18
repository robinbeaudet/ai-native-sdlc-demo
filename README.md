# expense-flow-api

A small expense submission and approval API, used to demonstrate Anthropic's
[AI-Native SDLC Playbook](https://claude.com/resources/articles/the-ai-native-sdlc-playbook).

The app is deliberately simple. What matters is the process around it: every change goes
**intent → spec → plan → code → pull request**, either **gated** (a human approves each
step) or **autonomous** (Claude goes straight to a PR). Claude reviews each code commit it
makes, and every pull request.

Stack: Python 3.13, `uv`, FastAPI, SQLAlchemy (async) + SQLite, Alembic, `ruff`, `pytest`.
Money is always `Decimal`, never `float`.

## Quick start

```bash
brew install uv
uv sync                          # installs Python 3.13 and the dependencies
uv run alembic upgrade head      # creates the database
uv run uvicorn expense_flow.main:app --reload
```

API docs: http://127.0.0.1:8000/docs. The app never creates tables itself: always run the
migrations first. Settings come from environment variables (`DATABASE_URL`, `ENVIRONMENT`,
`SQL_ECHO`).

Tests: `uv run pytest` (tiers: `unit`, `integration`, `eval`; e.g. `uv run pytest -m eval`).

## API

| Method | Path | What it does |
|---|---|---|
| `GET` | `/health` | Health check |
| `POST` | `/claims` | Submit a claim (checked against the policy) |
| `GET` | `/claims/{id}` | Get a claim |
| `POST` | `/claims/{id}/approve` | Approve a submitted claim |
| `POST` | `/claims/{id}/reject` | Reject a submitted claim, with a reason |

Amounts are sent and returned as strings, e.g. `"49.99"`. Errors: `404` unknown claim,
`409` claim already decided, `422` invalid input or policy violation (with a `violations` list).

## Expense policy

From [`policy.py`](src/expense_flow/policy.py). Thresholds are exclusive: exactly €50.00 needs no receipt,
and exactly €100.00 needs no cost center.

| Code | Rule |
|---|---|
| `RECEIPT_REQUIRED` | On submission: `MEALS` claims over €50.00 need a `receipt_url` |
| `AMOUNT_EXCEEDS_MAXIMUM` | On submission: a claim cannot exceed €2,500.00 |
| `COST_CENTER_REQUIRED` | On submission: claims over €100.00 need a `cost_center` |
| `COST_CENTER_INVALID` | On submission: a `cost_center`, when given, must be `CC-` followed by 4 digits (e.g. `CC-1234`), at any amount |
| `VP_APPROVAL_REQUIRED` | On approval: claims over €500.00 can only be approved by a `VP` |

## Data model

One table, `expense_claims` ([`models.py`](src/expense_flow/models.py)):

| Field | Type | Notes |
|---|---|---|
| `id` | int | Primary key |
| `employee_id` | text | Required |
| `category` | enum | `MEALS`, `TRAVEL`, `LODGING`, `EQUIPMENT`, `OTHER` |
| `amount` | Decimal | Required; stored as integer cents |
| `currency` | text | Always `EUR` |
| `description` | text | Required |
| `receipt_url` | text | Optional |
| `cost_center` | text | Optional; format `CC-1234`; required on submission over €100.00. `null` on claims submitted before this rule |
| `status` | enum | `SUBMITTED` → `APPROVED` or `REJECTED` |
| `submitted_at` | datetime | Required, UTC |
| `decided_at`, `approver_id`, `approver_role`, `rejection_reason` | | Optional; set when the claim is decided. Role: `MANAGER` or `VP` |

## How the AI-native SDLC works here

| File | Role |
|---|---|
| [`CLAUDE.md`](CLAUDE.md) | The rules Claude follows in this repo |
| [`REVIEW.md`](REVIEW.md) | The review checklist |
| [`capture-intent` skill](.claude/skills/ai-native-sdlc-demo-capture-intent/SKILL.md) | Turns a request into an intent file, gated or autonomous |
| [`run-intent` skill](.claude/skills/ai-native-sdlc-demo-run-intent/SKILL.md) | Takes an intent through spec, plan, code and PR |
| [`reviewer` agent](.claude/agents/reviewer.md) + [`review_gate.py`](scripts/review_gate.py) | Reviews each code commit Claude makes, and can block it (commits of only intents, specs or plans, and commits you make yourself, are not reviewed) |
| [`ci.yml`](.github/workflows/ci.yml) | Runs lint, migrations and tests on every PR |
| [`claude-review.yml`](.github/workflows/claude-review.yml) | Claude reviews every PR in GitHub |
| [`claude.yml`](.github/workflows/claude.yml) | Comment `@claude <request>` on a PR and Claude pushes a fix |
| [`CODEOWNERS`](.github/CODEOWNERS) | Changes to these SDLC files need a human's approval |

Intents, specs and plans are stored in `sdlc/intents/`, `sdlc/specs/` and `sdlc/plans/`.
Each change lives on a `feature/<slug>` branch and reaches `main` through a pull request.

## Running the demos

Open this repository in Claude Code (run `claude` from the repo root), on an up-to-date `main`.

**Track 1: gated (a schema change, so a human approves each step).**
Say: *"Finance wants every claim over €100 to carry a cost center. Make `cost_center`
mandatory for claims over €100."* Choose **Gated**, then run
`/ai-native-sdlc-demo-run-intent sdlc/intents/intent-002-....md`. Claude pauses for your
approval after the spec (check the migration: what happens to existing rows?), after the
plan, and before opening the PR.

**Track 2: autonomous (a pre-approved `[LLM]` ticket).**
Paste: *"[LLM] Add a new expense category SOFTWARE. SOFTWARE claims over €100 must include
a `reviewer_note` when they are approved."* Claude runs on its own up to a draft PR,
and only stops if it is blocked.

## GitHub setup (once)

1. Install the Claude GitHub App on the repository: https://github.com/apps/claude
2. Run `claude setup-token` and save the token as the repository secret
   `CLAUDE_CODE_OAUTH_TOKEN` (Settings → Secrets and variables → Actions).
3. Protect `main` (Settings → Branches): require a pull request, require the
   `Deterministic verification` check, and turn on **Require review from Code Owners**.

The Claude workflows use your Claude subscription, so they count toward its usage limits.
