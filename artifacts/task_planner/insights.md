# Task Planner Insights

- The telegram_bot code lives in TWO locations: `telegram_bot/` (deployed) and `artifacts/developer/telegram_bot/` (developer workspace with tests). Tests are in `artifacts/developer/telegram_bot/tests/`. The developer works in the artifacts copy.
- `bot.py` callbacks (`on_response`, `on_end`) are closures defined inside `agent_command_handler()`. State shared between them must use mutable containers (dict/list) or `nonlocal`, since closures can't rebind enclosing-scope integers.
- python-telegram-bot exceptions are in `telegram.error` module. `RetryAfter` has a `retry_after` attribute (integer seconds).
- `send_long_message()` currently returns None and calls `bot.send_message()` directly. Both the retry wrapper and circuit breaker tickets require it to return a bool.
- The `on_response` callback is only invoked for Claude response delivery (from `Session._read_stdout`), making it the natural place for response-delivery-only failure counting.
- `SessionManager.end_session()` handles full cleanup including `_remove_session()` which removes from `_sessions` dict, enabling the normal "no active session" flow for subsequent messages.
