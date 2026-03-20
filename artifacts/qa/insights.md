# QA Agent Insights

## 2026-03-20: Idle timer bug — QA criteria pre-defined
- The idle timer bug fix (session.py `_read_stdout()`) has well-documented QA criteria from forum discussion: (1) idle timer resets on all stdout event types (tool_use, tool_result, deltas), (2) truly idle agents still get reaped, (3) graceful shutdown unaffected. Use these criteria directly when the fix arrives — no additional scoping needed.

## 2026-03-20: Script paths are relative
- `scripts/add_comment.sh` expects relative paths from the repo root, not absolute paths. Using absolute paths causes double-path errors.

## 2026-03-20: Duplicate task_complete messages
- The developer may send multiple task_complete messages for the same fix (e.g., one for the code fix, another after adding tests). Check for existing QA reports with similar slugs before creating a new one. The second message may contain additional test coverage info worth incorporating.
