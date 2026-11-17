---
name: ai-native-sdlc-demo-capture-intent
description: "Capture a product owner's feature request or ticket as a versioned intent file (intents/intent-NNN-slug.md) for expense-flow-api, choosing the Gated or Autonomous workflow. Use when the user describes a new feature, policy change or ticket for this repo, or pastes a ticket tagged [LLM]."
---

# Capture intent (AI-native SDLC, stage 1)

You turn a product owner's request into an **intent**: the first artifact of the
lifecycle (intent -> spec -> plan -> code). You capture *what* and *why*, never *how*.
Do not write specs, plans or code in this skill.

## Step 1: Learn the context

1. List `intents/` and read the frontmatter and title of every existing intent.
2. Work out the next number: highest `NNN` + 1, zero-padded to 3 digits.
3. Note any existing intent that overlaps or conflicts with the request, and mention it
   to the user.
4. Skim `README.md` (policy table, endpoints) so you use the product's vocabulary.

## Step 2: Choose the workflow mode

- If the request contains the tag **`[LLM]`** (a ticket pre-approved for automation), use
  `workflow_mode: autonomous` and `ticket_tag: LLM` without asking.
- Otherwise, ask the user with these two options:
  - **Gated**: a human approves the spec, the plan and the code. Recommend it for schema
    changes, breaking API changes and changes to financial rules.
  - **Autonomous**: Claude runs end to end, up to a draft PR. Recommend it for
    well-scoped, additive changes.
  Use `ticket_tag: STANDARD` for both.

## Step 3: Clarify (briefly)

Ask at most 3 short questions, and only about things that would change the requirements.
Exact thresholds matter: "over EUR 100" must become "amount > 100.00". Mixing up `>` and
`>=` is the classic bug. Do not ask about implementation details.

## Step 4: Write the intent

Write `intents/intent-<NNN>-<slug>.md`. The slug is 2 to 5 kebab-case words. Use this
exact structure:

```markdown
---
title: <short imperative title>
workflow_mode: gated | autonomous
ticket_tag: STANDARD | LLM
target_branch: dev
status: captured
created: <YYYY-MM-DD>
---

# Intent <NNN>: <title>

## Business driver
<why this matters now: problem, cost, risk, regulation>

## User impact
<who is affected and how; one bullet per persona>

## Functional requirements
<numbered, testable statements with exact Decimal thresholds and > / >= spelled out>

## Non-goals
<what is explicitly out of scope>

## Acceptance criteria
<concrete examples with amounts at and around each boundary>
```

## Step 5: Hand off

- **Gated** (GA-1): stop. Show the file path and a 3-line summary, then say:
  > Review the intent. When it's right, start delivery with
  > `/ai-native-sdlc-demo-run-intent intents/intent-<NNN>-<slug>.md`.
  > I'll pause for your approval after the spec (GA-2), the plan (GA-3) and before the PR (GA-4).

  Do **not** start delivery yourself in gated mode.

- **Autonomous**: continue immediately with the `ai-native-sdlc-demo-run-intent` skill on
  the new intent. It runs straight through to a draft PR.
