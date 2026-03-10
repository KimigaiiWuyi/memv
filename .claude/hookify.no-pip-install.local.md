---
name: no-pip-install
enabled: true
event: bash
pattern: pip\s+install
action: warn
---

This project uses **uv**, not pip. Use `uv add <package>` or `uv sync` instead.
