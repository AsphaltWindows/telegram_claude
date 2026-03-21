# QA Agent Insights

## Scheduler vs Interactive Work

- The scheduler may launch the QA agent when pending task_complete messages exist. In non-interactive mode, automated QA (running tests, code review) can still be performed. Full interactive QA with live bot testing requires a user session.

## Automated QA for Pending Messages

- When launched by scheduler with pending task_complete messages but no forum topics, run the full test suite and do code review. Create QA reports noting "automated only" and recommend manual live-bot testing for steps that require it. This is better than doing nothing.
- Run tests from both `artifacts/developer/tests/` and `artifacts/developer/telegram_bot/tests/` to cover the full suite.
