# Developer Insights

- **Dual bot.py copies**: The codebase has two copies of `telegram_bot/bot.py` — one at the project root and one at `artifacts/developer/telegram_bot/bot.py`. Tests in `artifacts/developer/telegram_bot/tests/` import from the artifacts copy. Always apply changes to BOTH copies, or tests will silently test the old code.
- **Closure-scoped mutable state**: To track state across async callback invocations in Python closures, use a mutable container (dict) rather than `nonlocal` with simple variables. The `failure_state = {"key": value}` pattern works cleanly for circuit breaker counters.
- **Mock patching and closures**: `patch("telegram_bot.bot.send_long_message")` works correctly with closures defined in the same module because the closure looks up the name in module globals at call time, not definition time.
