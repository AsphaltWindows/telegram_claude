# QA Agent Insights

- Test files from developer are in `artifacts/developer/` not the main source tree. The developer's task_complete messages reference paths relative to `artifacts/developer/` (e.g., `cd artifacts/developer && python -m pytest ...`). Always run tests from project root using the `artifacts/developer/` prefix.
- In non-interactive mode, QA steps requiring manual/interactive testing can be verified via code inspection when the logic is straightforward. Note this in the report.
