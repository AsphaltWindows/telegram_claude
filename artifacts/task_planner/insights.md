# Task Planner Insights

- The telegram_bot code lives in TWO locations: `telegram_bot/` (deployed) and `artifacts/developer/telegram_bot/` (developer workspace with tests). Tests are in `artifacts/developer/telegram_bot/tests/`. The developer works in the artifacts copy.
- `bot.py` callbacks (`on_response`, `on_end`) are closures defined inside `agent_command_handler()`. State shared between them must use mutable containers (dict/list) or `nonlocal`, since closures can't rebind enclosing-scope integers.
- python-telegram-bot exceptions are in `telegram.error` module. `RetryAfter` has a `retry_after` attribute (integer seconds).
- `send_long_message()` now returns `bool` and uses `retry_send_message()` with retry logic. Circuit breaker is implemented in `on_response` closure.
- The `on_response` callback is only invoked for Claude response delivery (from `Session._read_stdout`), making it the natural place for response-delivery-only failure counting.
- `SessionManager.end_session()` handles full cleanup including `_remove_session()` which removes from `_sessions` dict, enabling the normal "no active session" flow for subsequent messages.
- The idle timer fix is ALREADY IMPLEMENTED in `session.py` lines 385-388. `_read_stdout()` now updates `last_activity` and calls `_reset_idle_timer()` on each non-empty stdout line. Tests exist in `test_session_idle_timer.py`.
- `Session._finish()` ordering: `_cleanup(chat_id)` runs BEFORE `_on_end` callback. This means session is removed from `_sessions` before the end notification is sent to the user. This is correct — send failures in `on_end` don't break cleanup.
- The `on_end` callback already sends timeout messages (bot.py line 386-393). The message exists but doesn't tell the user how to start a new session. Also, `send_long_message` return value is discarded — should log on failure.
- Race condition in `plain_text_handler`: if user sends message exactly as timeout fires, `session.send()` raises `RuntimeError("Session is no longer active.")` which is unhandled. Wrap in try/except.
