---
name: update-plan
description: Update project plan from repo state and conversation
allowed-tools: Read, Write, Bash, Glob
---

Update `notes/PLAN.md` and append to `notes/PROGRESS.md` based on the current state of the repository and this conversation.

## Process

1. Run `~/.claude/scripts/plan-status.sh` to get structured plan status and git state
2. Read `notes/PLAN.md` (previous version — update it, never rewrite from scratch)
3. Review the conversation for decisions, priorities, and tasks discussed
4. Optionally scan recent session logs in `notes/claude/worklog/` for additional context
5. **Update** `notes/PLAN.md`:
   - Flip `[ ]` → `[x]` for items completed (verified in codebase, not just discussed)
   - Add new `[ ]` items if new work was identified
   - Remove items that are no longer relevant
   - Update the "Last updated" timestamp
6. **Append** to `notes/PROGRESS.md` (create if missing):
   - Add a dated entry summarizing what changed in the plan and why
   - This file is append-only — never rewrite or remove previous entries

## Rules

- **Project-scoped only** — only include work that changes this project's code, tests, docs, or architecture. Exclude personal tooling, editor config, etc.
- **Preserve structure** — don't reorganize sections or rewrite prose unless explicitly asked. Only touch checkboxes and add/remove items.
- **Verify before checking off** — mark items `[x]` only if the work is actually in the codebase (committed or staged), not just discussed.
- Ground updates in actual repo state (commits, diffs), not just conversation

## PROGRESS.md format

```markdown
## YYYY-MM-DD

- Checked off: <item> — <brief evidence>
- Added: <new item> — <why>
- Removed: <item> — <why>
- Decision: <what was decided and why>
```

Keep entries concise. One line per change.
