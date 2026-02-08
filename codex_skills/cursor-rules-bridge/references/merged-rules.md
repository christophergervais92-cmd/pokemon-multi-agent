# Merged Cursor Rules (Imported)

This file consolidates the behavior from these source files:
- `agents-compound.mdc`
- `agents-running-on-cursor.mdc`
- `ralph.mdc`
- `security-gate.mdc`
- `security-prompts.mdc`
- `three-layer-architecture.mdc`

## Always-on behavior

### 1) 3-layer architecture
- Treat Markdown SOPs in `directives/` as Layer 1 (directive: what to do).
- Operate as Layer 2 (orchestration: route work, invoke tools, handle errors, update SOPs).
- Prefer deterministic scripts in `execution/` as Layer 3 (execution: APIs, processing, file/database ops).
- Before writing new scripts, check existing `execution/` tools first.
- Self-anneal on failure: fix script, retest, then update directive with the new constraint/flow.

### 2) Security and quality gate
Before marking a task complete:
- Scan for secrets and hardcoded credentials.
- Check for SQL/shell injection and path traversal.
- Verify user input validation and auth/permission boundaries.
- Run tests and type checks.
- Report what passed/failed and what was not run.

## On-demand workflows

### Compound review (on demand)
Trigger phrases include: `run compound review`, `compound learnings`, `extract learnings from today`.

Flow:
1. Read `logs/daily-context.md` if present (otherwise use existing rules only).
2. Extract durable patterns, gotchas, and context.
3. Merge into `RULE.md` or `.cursor/rules/compound-learnings.mdc`.
4. Keep entries concise and actionable.

### Auto-compound (on demand)
Trigger phrases include: `run auto-compound`, `pick next priority`, `implement top priority`.

Flow:
1. Read `reports/priorities.md` (or `reports/*.md`).
2. Choose top priority and write a short PRD/task plan (`tasks/`).
3. Implement tasks, tests, and docs updates.
4. Continue until done or explicitly stopped.

### Ralph autonomous loop
Trigger phrases include: `run Ralph`, `autonomous loop`, `headless task execution`.

Flow:
1. Use Ralph in terminal (`ralph-enable`, then `ralph` or `ralph --monitor`).
2. Keep Cursor/Codex for editing and review, Ralph for loop execution.
3. For nightly compound integration, wire `AGENT_CMD` to Ralph or a wrapper that syncs priority into `.ralph/fix_plan.md`.

## Optional hardening prompts
Use when explicitly reviewing/hardening:
- "Write 20 unit tests designed to break this function."
- "Find every security vulnerability in this file. Think like a pentester."
- "Generate 50 edge cases: null, empty strings, negatives, unicode, huge arrays."
- "Audit this codebase for leaked secrets."
