---
name: block-force-push-main
enabled: true
event: bash
pattern: git\s+push\s+.*--force.*\b(main|master)\b|git\s+push\s+.*-f\s.*\b(main|master)\b
action: block
---

Force push to main/master is blocked. This rewrites shared history and can destroy work.
