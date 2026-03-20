# QA Insights

- When processing task_complete messages in non-interactive mode, run `python -m pytest` with `-v` flag to verify all tests pass, then do a code review of the implementation against stated requirements. This is sufficient for automated QA when no user is available for manual testing.
- The test suite imports from `artifacts/developer/telegram_bot/` — that's the canonical test location for this project.
