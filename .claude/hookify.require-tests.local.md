---
name: require-tests
enabled: true
event: stop
pattern: .*
action: warn
---

Before finishing, verify tests pass:

```bash
uv run pytest
```

If you modified extraction logic, temporal handling, or retrieval, run the full suite — these areas have subtle interactions.
