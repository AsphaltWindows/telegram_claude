# telegram-send-circuit-breaker

## Metadata
- **From**: task_planner
- **To**: developer

## Content

### Requirements

1. Track consecutive send failures per chat session. Each time the retry wrapper (from ticket telegram-send-retry-with-logging) reports a failed send, increment a per-session consecutive failure counter. Each time a send succeeds, reset the counter to 0.

2. After 5 consecutive send failures within a single session, automatically end the session. Use the existing session-end mechanism (SessionManager.end_session or equivalent).

3. When the circuit breaker triggers, log at ERROR level: 'Session ended: {N} consecutive Telegram send failures for chat {chat_id}'.

4. When the circuit breaker triggers, attempt to send one final notification to the user: 'Session ended due to repeated message delivery failures. Please start a new session.' This notification must use the retry wrapper but if it also fails, log and move on — do not block or enter any additional retry loop.

5. After the circuit breaker ends a session, new messages from the user must follow the normal 'no active session' flow (the existing behavior that prompts them to start a new session). No special handling is required beyond the standard flow.

6. If the 'no active session' notification itself fails to send, log the failure and move on — do not enter any retry loop for non-session messages.

7. The consecutive failure counter must only count response-delivery sends (messages sent as part of an active session's Claude responses), not one-off notifications like session-start confirmations.

### Dependencies

- Depends on ticket **telegram-send-retry-with-logging** (needs the retry wrapper's success/failure signal to track consecutive failures).

### QA Steps

1. **Unit test — counter resets on success**: Simulate 4 consecutive failures followed by 1 success. Verify the counter resets to 0 and the session is NOT ended.

2. **Unit test — circuit breaker triggers at 5**: Simulate exactly 5 consecutive send failures. Verify the session is ended and the ERROR log message includes the failure count and chat_id.

3. **Unit test — circuit breaker final notification**: Simulate 5 consecutive failures triggering circuit breaker. Verify one attempt is made to send the user notification message 'Session ended due to repeated message delivery failures. Please start a new session.'

4. **Unit test — final notification failure is non-blocking**: Simulate 5 failures triggering circuit breaker, and mock the final notification to also fail. Verify no exception propagates and the failure is logged.

5. **Unit test — post-circuit-breaker message routing**: After circuit breaker ends a session, send a new user message. Verify it enters the normal no-active-session flow.

6. **Unit test — counter scoped to session**: Verify that failures in one chat's session do not affect the counter for another chat.

7. **Integration test — end-to-end**: Start a session, mock Telegram API to fail on all sends, send 5 Claude responses. Verify the session is ended, the log contains the circuit breaker message, and a subsequent user message gets the 'no active session' response.

### Technical Context

#### Relevant Files

- **`telegram_bot/bot.py`** (MODIFY) — Primary file to modify. The circuit breaker logic lives here in the callback layer, not in `session.py`. The `on_response` callback (line 252-253) and `on_end` callback (line 255-268) are defined inside `agent_command_handler()` — these closures are where failure tracking and circuit breaker triggering belong.
- **`telegram_bot/session.py`** (READ, possibly MODIFY) — Contains `SessionManager.end_session()` (line 597) which is the mechanism to use when the circuit breaker triggers. The `Session` class itself does NOT need modification — failure tracking is external to the session. However, `SessionManager` is accessed via `context.bot_data["session_manager"]` in the handler.
- **`artifacts/developer/telegram_bot/tests/test_bot.py`** (MODIFY) — Add circuit breaker test classes here following existing patterns.
- **`telegram_bot/bot.py` — `retry_send_message()`** (from previous ticket) — Returns `bool` (True=success, False=failure). The circuit breaker consumes this return value.
- **`telegram_bot/bot.py` — `send_long_message()`** — After the retry ticket, this will return `bool` indicating if all chunks sent successfully. The circuit breaker should use this return value from `on_response`.

#### Patterns and Conventions

- **Closure-scoped state**: The `on_response` and `on_end` callbacks are closures defined inside `agent_command_handler()` (line 252-268). They close over `bot`, `cid` (but receive `cid` as parameter), and the `session_manager` via `context.bot_data`. The consecutive failure counter should be a simple local variable (e.g., a mutable container like a `dict` or a list with one element, since closures can't rebind integers in enclosing scope — use `nonlocal` or a mutable wrapper).
- **Async patterns**: All callbacks are `async def`. `SessionManager.end_session()` is also async.
- **Test patterns**: Same as previous ticket — `pytest.mark.asyncio`, `MagicMock`/`AsyncMock`, test classes grouped by feature.
- **Logging**: Use the existing `logger` in `bot.py`.

#### Dependencies and Integration Points

- **`retry_send_message()` return value** — The boolean from the retry wrapper (True=sent, False=failed). This is the input signal for the failure counter.
- **`send_long_message()` return value** — After the retry ticket, should return `bool`. The `on_response` callback should check this return value to update the failure counter.
- **`SessionManager.end_session(chat_id)`** (line 597-608) — Calls `session.shutdown(reason="shutdown")`. This is the standard session-end mechanism. When the circuit breaker triggers, call this with the chat_id.
- **`SessionManager.has_session(chat_id)`** (line 610-612) — After `end_session` completes, `has_session` returns `False`. New messages will then hit the "No active session" path in `plain_text_handler()` (line 345-349).
- **`Session._cleanup`** (line 349) — Called during `Session._finish()`, invokes `SessionManager._remove_session(chat_id)` to remove from the internal `_sessions` dict. This happens automatically during `end_session`.

#### Implementation Notes

1. **Failure counter location**: Define the counter inside `agent_command_handler()` as a mutable container, accessible to both `on_response` and the circuit breaker logic. Recommended approach:
   ```python
   failure_state = {"consecutive_failures": 0}
   ```
   This is a closure variable shared by `on_response`.

2. **Update `on_response` callback**: After calling `send_long_message()`, check the return value. If `False`, increment `failure_state["consecutive_failures"]`. If `True`, reset to 0. If the counter reaches 5, trigger the circuit breaker.

3. **Circuit breaker trigger sequence**:
   a. Log the ERROR message with failure count and chat_id.
   b. Attempt to send the final user notification via `retry_send_message(bot, cid, "Session ended due to repeated message delivery failures. Please start a new session.")`. Wrap in try/except — if it fails, log and continue.
   c. Call `session_manager.end_session(cid)` to end the session. Access `session_manager` from the closure scope (it is captured from `context.bot_data["session_manager"]`).

4. **Important: `session_manager` access in closure**: Currently `session_manager` is accessed at the top of `agent_command_handler()` (line 223). The `on_response` closure can reference it directly since it's in the enclosing scope. No need to pass it through `bot_data` again.

5. **Requirement 7 — only count response-delivery sends**: The `on_response` callback is ONLY called for Claude response delivery (from `_read_stdout`). The `on_end` callback sends session-end notifications — these should NOT increment the failure counter. Confirmation messages (from `agent_command_handler` line 301) use `update.message.reply_text()` which is outside the retry/counter system entirely. So the counter naturally only counts response-delivery sends if placed in `on_response`.

6. **Race condition consideration**: The `on_response` callback is called from `_read_stdout` which runs as an asyncio task. Since Python asyncio is single-threaded and cooperative, there's no true race condition — but be aware that `end_session` is async and involves waiting for the process. After triggering the circuit breaker, subsequent `on_response` calls might still arrive before the session fully ends. Guard against this by checking `failure_state["consecutive_failures"] >= 5` and short-circuiting (don't try to end the session twice).

7. **Post-circuit-breaker flow**: After `end_session` completes, `SessionManager._remove_session()` removes the chat_id from `_sessions`. The next user message goes to `plain_text_handler()` which checks `session_manager.has_session(chat_id)` → False → sends "No active session" reply. This is the existing flow — no changes needed.

### Design Context

Implements the 'Consecutive Failure Circuit Breaker' and 'Post-Failure Message Routing' sections of the Telegram Send Error Handling design. See artifacts/designer/design.md, section 'Telegram Send Error Handling'. The circuit breaker prevents sessions from running indefinitely while silently dropping all output, which was the core user-reported bug.
