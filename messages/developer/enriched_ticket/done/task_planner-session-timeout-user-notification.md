# session-timeout-user-notification

## Metadata
- **From**: task_planner
- **To**: developer

## Content

### Requirements

1. When a session is terminated due to idle timeout, the bot must send a message to the user via Telegram informing them that the session has ended (e.g., 'Session ended due to inactivity. Send a new message to start a new session.').
2. After a session is cleaned up (via `_finish("timeout")` and `SessionManager._remove_session()`), verify that new incoming messages from the user correctly trigger a new session rather than hitting a `ValueError("No active session")` with no user-visible feedback.
3. If the timeout notification message to Telegram fails to send (network error, API error), this failure must be logged at WARNING or ERROR level. The session cleanup must still proceed regardless.
4. The `on_end` callback path (session.py lines 393-395) should be reviewed to ensure exceptions in the callback do not prevent proper session cleanup or leave the bot in a state where it cannot accept new messages for that chat.

### QA Steps

1. Start a session and let it idle until the timeout fires. Verify the user receives a clear notification message in Telegram that the session was ended due to inactivity.
2. After receiving the timeout notification, send a new message. Verify a new session is started successfully and the bot responds normally.
3. Simulate a failure in sending the timeout notification (e.g., disconnect network briefly). Verify the session cleanup still completes and the bot can accept new messages for that chat afterward.
4. Check logs after a timeout event to confirm appropriate log entries exist for the timeout, the notification attempt, and the session cleanup.
5. Verify no race condition exists: rapidly send a message right as the timeout fires. Confirm the bot either delivers the timeout message and starts a new session, or the new message prevents the timeout — but does not leave the bot in a broken state.

### Technical Context

#### Relevant Files

- **`telegram_bot/bot.py`** (PRIMARY — modify): Contains the `on_end` callback (lines 381-395) defined inside `agent_command_handler()`. This is where the timeout notification is sent to the user.
  - Lines 381-395: `on_end()` closure — already handles timeout with message `f"Session with {aname} timed out due to inactivity."`. This means **the timeout notification is already partially implemented**.
  - Line 393: `await send_long_message(bot, cid, msg)` — sends the notification. Wrapped in try/except on lines 394-395.
  - Lines 471-474: `plain_text_handler()` — after session removal, `has_session()` returns False and the user gets `"No active session. Start one with /<agent_name>."`. This is the recovery path.
- **`telegram_bot/session.py`** (review/possible modify): Contains the session lifecycle.
  - Lines 324-359: `_finish()` method — the cleanup sequence. CRITICAL: `_cleanup(self.chat_id)` (line 350) removes the session from `SessionManager._sessions` BEFORE `_on_end` callback (line 354). This ordering means by the time the user receives the timeout notification, the session is already removed and a new `/agent` command would work.
  - Lines 348-350: `self._cleanup(self.chat_id)` — calls `SessionManager._remove_session()` which does `self._sessions.pop(chat_id, None)`.
  - Lines 353-359: `_on_end` callback invocation — already wrapped in try/except with `logger.exception`. If the callback raises, it is logged and the session cleanup has already completed (line 350 ran first).
- **`artifacts/developer/telegram_bot/bot.py`** (modify): Developer workspace copy.
- **`artifacts/developer/telegram_bot/tests/test_bot.py`** (reference/modify): Existing tests use `pytest`, `mock.AsyncMock`, `mock.MagicMock`.

#### Patterns and Conventions

- Callbacks (`on_response`, `on_end`) are closures defined inside `agent_command_handler()` (bot.py lines 345-395). They capture `bot` and `session_manager` from the enclosing scope.
- Error handling pattern: wrap Telegram sends in try/except, log the exception, never let send failures propagate to break session lifecycle.
- `send_long_message()` (bot.py lines 243-269) already returns `bool` — True if all chunks sent, False if any failed. Use this return value for logging.
- `retry_send_message()` (bot.py lines 165-240) handles RetryAfter, TimedOut, NetworkError with retries, and BadRequest/Forbidden as non-retryable.
- Logging: `logger = logging.getLogger(__name__)`, use `logger.warning()` or `logger.error()` for send failures.

#### Dependencies and Integration Points

- **`Session._finish()` ordering (session.py lines 324-359)**: The cleanup (`_remove_session`) runs at line 350, BEFORE `_on_end` at line 354. This is correct — it means even if `on_end` fails to send the notification, the session is already removed and the bot can accept new sessions. No change needed to this ordering.
- **`plain_text_handler()` (bot.py lines 464-479)**: After session removal, this handler correctly checks `has_session()` and replies with "No active session. Start one with /<agent_name>." This is the existing recovery flow — it works, but the user message could be improved to be more helpful.
- **`agent_command_handler()` (bot.py lines 301-434)**: After session removal, a new `/<agent>` command will succeed because `has_session()` returns False. The path works correctly.
- **`send_long_message()` and `retry_send_message()`**: Already handle all Telegram error types with retries. The notification send in `on_end` already uses `send_long_message`.

#### Implementation Notes

1. **GOOD NEWS: The timeout notification already exists.** The `on_end` callback (bot.py lines 381-395) already sends `"Session with {aname} timed out due to inactivity."` when reason is "timeout". The primary task is to VERIFY this works correctly end-to-end and improve robustness.

2. **Key improvements to make:**
   - **Improve the timeout message** (line 386): Change from `f"Session with {aname} timed out due to inactivity."` to something like `f"Session with {aname} ended due to inactivity. Send /{aname} to start a new session."` — the current message does not tell the user how to recover.
   - **Log the send result** (around line 393): Currently the return value of `send_long_message()` is discarded. Log at WARNING level if it returns False: `success = await send_long_message(bot, cid, msg)` followed by `if not success: logger.warning(...)`.
   - **Verify the exception handler** (lines 394-395): The existing `except Exception` with `logger.exception` is correct — it prevents send failures from breaking cleanup. But confirm that `_finish()` has already completed cleanup before this point (it has — `_cleanup` at line 350 runs before `_on_end` at line 354).

3. **Race condition analysis**: The `_shutting_down` flag (session.py line 274) prevents `send()` from accepting new input during shutdown. If a user sends a message right as timeout fires, `send()` will raise `RuntimeError("Session is no longer active.")`. The `plain_text_handler` does not currently catch this — it would result in an unhandled exception. Consider wrapping the `send_message` call in `plain_text_handler()` (bot.py line 479) with a try/except for RuntimeError to handle this race gracefully.

4. **Test approach**: Test that `on_end` callback sends the correct message for reason "timeout". Mock `send_long_message` and verify it is called with the expected timeout message. Also test that when `send_long_message` raises, the exception is caught and logged.

5. **Order of implementation**: This can be developed independently of the idle-timer fix ticket, but should be tested together. The idle-timer fix prevents premature timeouts; this ticket ensures proper user notification when legitimate timeouts occur.

### Design Context

This addresses the secondary issue from the bot unresponsiveness bug: when a session dies due to timeout, the bot goes completely silent with no user feedback. The user has no way to know what happened or that they need to send a new message. Silent failure is the worst UX outcome for a chat interface. The designer noted this is a UX bug independent of the timer fix. See forum topic: 2026-03-20-operator-bot-unresponsive-during-agent-file-reads.md. Developer analysis confirmed that after session removal, the code path for new messages may not gracefully handle the missing session. This ticket depends on the idle timer fix ticket (fix-idle-timer-agent-output) being implemented first or concurrently, but can be developed independently.
