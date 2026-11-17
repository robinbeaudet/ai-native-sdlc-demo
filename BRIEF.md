# Project Specification & Master Intent: Enterprise AI-Native SDLC Showcase (`expense-flow-api`)

## 1. Overview & Core Objectives

The primary intent of this repository is to establish a production-grade reference implementation demonstrating Anthropic's **AI-Native SDLC Playbook**: https://claude.com/resources/articles/the-ai-native-sdlc-playbook

Modern engineering organizations face a persistent dilemma: unconstrained AI coding leads to technical debt, architectural drift, security vulnerabilities, and broken database schemas, while overly rigid manual oversight stifles velocity. This project proves that an enterprise can achieve both extreme delivery velocity and rigorous engineering governance by enforcing a strict **artifact-driven lifecycle** paired with risk-based workflow routing (**Human-in-the-Loop Gated** vs. **Autonomous End-to-End**).

## 2. Technology Stack & Architectural Invariants

To resonate with senior technical leaders and engineering management, the system models a realistic corporate microservice: **`expense-flow-api`** (an asynchronous corporate expense submission and approval platform).

* **Language & Typing:** Python 3.13, utilizing strict type annotations across all modules.
* **Toolchain & Dependency Management:** Managed exclusively via `uv` (no raw `pip` or `poetry`).
* **Code Quality:** `ruff` configured for strict linting and formatting in `pyproject.toml`.
* **API & Persistence:** FastAPI with async dependency injection, SQLModel (async engine), and **Alembic** for tracked database schema migrations.
* **Financial Safety:** All monetary calculations must use Python's `decimal.Decimal` class. Floating-point arithmetic for currency is strictly prohibited.
* **Self-Verification & Documentation Sync:** Agents are bound by `CLAUDE.md` to execute deterministic test suites (`pytest`) and linting (`ruff`) after every modification, self-healing until 100% green, and automatically keeping `README.md` and OpenAPI specifications up to date.

## 3. GitOps & Branching Strategy

The repository must follow an enterprise branching topology:
* **`main`:** Production baseline. Protected; only accepts release merges from `dev`.
* **`dev`:** Integration/staging branch. All feature PRs target `dev` and must pass deterministic CI gates and the adversarial Reviewer Agent before merging.
* **`feature/*`:** Ephemeral feature branches created per intent.

## 4. The Artifact-Driven Lifecycle

Every feature, policy change, or bug fix must traverse explicit, version-controlled Markdown stages stored within the repository:

1. **Intent (`intents/intent-<slug>.md`):** Captures the business driver, user impact, functional requirements, and non-goals. It houses YAML frontmatter containing metadata such as `workflow_mode` (`gated` or `autonomous`), `ticket_tag` (`STANDARD` or `LLM`), and `target_branch` (`dev`).
2. **Specification (`specs/spec-<slug>.md`):** Translates the business intent into a rigorous technical blueprint, defining Pydantic/SQLModel contracts, Alembic migration strategies, edge cases (concurrency, timezone handling, rejected claim states), and testing requirements.
3. **Execution Plan (`plans/plan-<slug>.md`):** A step-by-step file modification roadmap generated in Plan Mode before any code is written.

## 5. Dual Workflow Routing: Gated vs. Autonomous

Different changes carry different risk profiles. Claude Desktop acts as the Product Owner entrypoint via a custom skill (`.claude/skills/ai-native-sdlc-demo-capture-intent.md`), stamping workflow metadata into the intent frontmatter so a local orchestrator routes execution dynamically:

* **The Gated Workflow (`workflow_mode: gated`):** Designed for high-stakes changes-such as database schema migrations, breaking API contract updates, or core financial policy modifications. The orchestrator pauses execution at strict Human Approval Gates (GA-2 for specifications, GA-3 for execution plans), allowing a senior engineer or product owner to review, edit, or reject the design before implementation begins.
* **The Autonomous Workflow (`workflow_mode: autonomous` / `"LLM"`-Tagged Ticket):** Designed for well-scoped feature extensions or routine internal updates (simulating an automated Jira ticket labeled `LLM`). Claude Desktop stamps `workflow_mode: autonomous` into the intent frontmatter, allowing the local orchestrator to chain through the specification, plan, implementation, Alembic migration, `pytest` verification, and documentation sync entirely hands-off.

## 6. Database Evolution & Alembic Integration

The architecture treats database changes as first-class citizens:
* Any modification to SQLModel table definitions (`models.py`) must be accompanied by a verified Alembic migration script (`alembic/versions/`).
* Migration scripts must be inspected for data-loss risks, explicit default values for new non-nullable columns, and clean `upgrade()` / `downgrade()` logic.

## 7. Quality Gates, CI/CD, and the Adversarial Reviewer Agent

To eliminate the risk of an agent rubber-stamping its own code, verification is decentralized into two distinct layers:

1. **Deterministic CI/CD Gates (`.github/workflows/ci.yml`):** Automatically executes `ruff` linting checks, verifies that Alembic migrations apply cleanly (`alembic upgrade head`), and runs the full `pytest` suite across unit, integration, and behavioral evaluation tiers.
2. **The Adversarial Reviewer Subagent (`.claude/agents/reviewer.md`):** An independent subagent granted read-only tools (`Read`, `Bash`, `Grep`, `Glob`). Triggered automatically on Pull Requests targeting `dev`, it audits the `git diff` line-by-line against the active specification, inspects Alembic migration scripts for destructive patterns, verifies financial arithmetic safety, and posts a structured verdict (`APPROVE` or `REQUEST_CHANGES`).

## 8. Target Demonstration Tracks

The codebase and orchestration tooling must fully support two live demonstration scenarios:

* **Track 1 (The Gated Migration Flow):** A policy update requiring a database schema change (e.g., adding a mandatory `cost_center` field for claims over €100). Demonstrates PO intent capture in Claude Desktop, an explicit pause at the specification gate to verify nullable/default migration behavior, autogenerated Alembic migrations, and human sign-off before code changes.
* **Track 2 (The Autonomous Feature Flow):** A ticket tagged `[LLM]` for adding a new expense category (`SOFTWARE`) where claims over €100 require a mandatory `reviewer_note` upon approval. Demonstrates automated end-to-end execution from intent capture straight through to a green draft PR targeting `dev`.
