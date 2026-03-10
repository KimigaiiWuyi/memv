---
name: no-print-in-src
enabled: true
event: file
conditions:
  - field: file_path
    operator: regex_match
    pattern: src/memv/.*\.py$
  - field: new_text
    operator: regex_match
    pattern: \bprint\(
action: warn
---

You're adding `print()` to source code. This is likely debug output — remove it before committing.
