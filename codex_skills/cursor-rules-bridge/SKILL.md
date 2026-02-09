---
name: cursor-rules-bridge
description: "Apply merged Cursor operating rules for software tasks: enforce 3-layer architecture (directive/orchestration/execution), run a mandatory security and quality gate before completion, and execute on-demand compound review, auto-compound, or Ralph loop workflows. Use when users mention compound review, auto-compound, Ralph, project governance, or security hardening."
---

# Cursor Rules Bridge

Use this skill as an operating layer that ports Cursor rule behavior into Codex workflows.

## Core Workflow

1. Route work using the 3-layer model.
- Read SOPs in `directives/` first when available.
- Orchestrate by selecting and sequencing tools/scripts.
- Prefer deterministic implementations in `execution/`.

2. Enforce a completion gate before finalizing work.
- Check for secret leakage and insecure credential handling.
- Check for injection and traversal vulnerabilities.
- Validate user-input handling and auth/permission boundaries.
- Run tests and type checks when available.
- Report executed checks and any skipped checks.

3. Apply trigger-specific workflows when requested.
- `run compound review` or similar: process `logs/daily-context.md` and merge learnings into persistent rules.
- `run auto-compound` or similar: take the highest-priority report item, draft short tasks, and implement it.
- `run Ralph` or autonomous-loop requests: guide or execute Ralph terminal flow.

## Operational Rules

- Check for existing scripts/tools before creating new scripts.
- Self-anneal failures: fix tool, retest, and update SOP/rules with the learned constraint.
- Keep updates concise, actionable, and durable.
- Ask before paid-token or high-risk operations.

## Resource Files

- Use `references/merged-rules.md` for the consolidated guidance.
- Use the imported source files in `references/*.mdc` when exact source wording is needed.
