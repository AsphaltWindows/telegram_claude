# add-session-death-notifications

## Metadata
- **From**: task_planner
- **To**: developer

## Content

### Requirements

1. When a session is terminated by idle timeout, the bot must send the user: "Session with `<agent_name>` timed out after 10 minutes of inactivity. Work has been saved."
2. When a session ends due to an unexpected agent process crash, the bot must send the user: "Session with `<agent_name>` ended unexpectedly: {last stderr lines}" — including the last few lines of stderr for diagnostics.
3. When a session ends due to the consecutive send failure circuit breaker (5 failures), the bot must attempt to send: "Session ended due to repeated message delivery failures. Please start a new session." (no retry if this also fails).
4. After ANY session termination (timeout, crash, circuit breaker), the bot must fully clean up session state so that subsequent user messages follow the normal "no active session" flow and the bot remains responsive.
5. Silent session death — where the bot stops responding without notifying the user — must not occur under any termination scenario.

### QA Steps

1. Simulate an idle timeout (wait 10 minutes or temporarily lower the timeout). Verify the user receives the timeout notification message in Telegram.
2. Kill the agent subprocess externally (e.g., `kill -9` the claude process). Verify the user receives the unexpected crash notification with stderr content.
3. Simulate 5 consecutive Telegram send failures (e.g., mock the send method to raise NetworkError). Verify the circuit breaker triggers and attempts to send the circuit breaker notification.
4. After each termination scenario, send a new message to the bot and verify it responds with the "No active session" prompt (confirming session state was cleaned up).
5. Review all session termination code paths and confirm each one sends a user-facing message before cleanup.

### Technical Context

#### Relevant Files

- **`telegram_bot/bot.py`** (lines 381-395) — `on_end()` callback closure inside `agent_command_handler()`. This is where death notification messages are sent. **Messages need updating to match the spec.**
- **`telegram_bot/bot.py`** (lines 341-379) — `on_response()` callback with circuit breaker logic. The circuit breaker notification message (line 369-370) already matches the spec.
- **`telegram_bot/bot.py`** (lines 243-269) — `send_long_message()` function. Returns `bool`. Used by both `on_response` and `on_end`.
- **`telegram_bot/bot.py`** (lines 165-240) — `retry_send_message()` function. Used for circuit breaker notification (no retry wrapper needed per req 3).
- **`telegram_bot/session.py`** (lines 324-359) — `_finish()` method. Calls `_cleanup(chat_id)` FIRST (removes from `_sessions`), THEN calls `_on_end` callback. This ordering is correct — cleanup happens before notification.
- **`telegram_bot/session.py`** (lines 256-302) — `shutdown()` method. Called for timeout and explicit shutdown.
- **`telegram_bot/session.py`** (lines 416-426) — End of `_read_stdout()` where crash is detected (unexpected process exit triggers `_finish("crash")`).
- **`telegram_bot/session.py`** (lines 200-219) — `stderr_tail` property. Returns buffered stderr output for crash diagnostics.
- **`artifacts/developer/telegram_bot/tests/test_bot.py`** — Existing bot tests with helpers `_make_update()` and `_make_context()`.
- **`artifacts/developer/telegram_bot/tests/test_session_idle_timer.py`** — Session test patterns to follow.

#### Patterns and Conventions

- `on_end` receives `(cid, aname, reason, *, stderr_tail="")` — keyword arg for stderr.
- `reason` values are: `"shutdown"`, `"timeout"`, `"crash"`.
- Closures in `agent_command_handler()` capture `bot` from outer scope. Mutable state uses dicts (e.g., `failure_state`).
- `send_long_message` returns `bool` — `True` if all chunks sent, `False` if any failed. The `on_end` callback currently wraps this in try/except but discards the return value.
- Tests use `mock.AsyncMock`, `mock.MagicMock`, `@pytest.mark.asyncio`.

#### Dependencies and Integration Points

- `Session._finish()` ordering: `_cleanup(chat_id)` removes session from `_sessions` BEFORE `_on_end` fires. This means the session is already gone when the notification is sent. This is intentional — if the notification send fails, session state is still clean.
- `SessionManager.end_session()` calls `session.shutdown()` which calls `_finish()`. The circuit breaker in `on_response` calls `session_manager.end_session()` after sending its own notification.
- `plain_text_handler()` (bot.py line 464-479): After session cleanup, `session_manager.has_session(chat_id)` returns `False`, so the user gets "No active session. Start one with /<agent_name>." on next message.

#### Implementation Notes

- **The `on_end` callback messages need updating** (bot.py lines 384-388). Current vs required:
  - `"timeout"`: Currently `"Session with {aname} timed out due to inactivity."` → Should be `"Session with \`{aname}\` timed out after 10 minutes of inactivity. Work has been saved."`
  - `"crash"`: Currently `"Session with {aname} ended unexpectedly."` + separate diagnostics block → Should be `"Session with \`{aname}\` ended unexpectedly: {stderr_tail}"` (inline, not in a separate code block). Review the exact format — the current code appends stderr in a markdown code block which may be acceptable.
  - `"shutdown"`: Current message `"Session with {aname} ended."` is fine (explicit user /end).
- **The circuit breaker notification** (bot.py lines 365-377) already matches the spec. It uses `retry_send_message` (which retries up to 3 times), but req 3 says "no retry if this also fails". Consider using `max_attempts=1` for the circuit breaker notification, since the channel is already unreliable.
- **Log on notification failure**: The `on_end` callback catches exceptions and logs them (line 394-395). Also consider logging the return value of `send_long_message` when it returns `False`.
- **Race condition in `plain_text_handler`**: If a user sends a message exactly as timeout fires, `session.send()` may raise `RuntimeError("Session is no longer active.")` which is currently unhandled. Wrap the `send_message` call in a try/except RuntimeError to handle this edge case gracefully.
- **Write tests** for the `on_end` callback to verify correct messages are sent for each reason. Mock `send_long_message` and verify the message text.

### Design Context

Silent session death was identified as a critical UX problem — users had no way to know their session had ended and the bot appeared permanently unresponsive. This ticket ensures every termination path notifies the user. See `artifacts/designer/design.md`, section "Session Death Notifications".
