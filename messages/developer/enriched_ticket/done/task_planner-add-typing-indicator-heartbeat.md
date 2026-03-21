# add-typing-indicator-heartbeat

## Metadata
- **From**: task_planner
- **To**: developer

## Content

### Requirements

1. During long-running agent operations, when no agent output has been received for a configurable period (suggest 5-10 seconds), the bot should send a Telegram typing indicator (`chat_action: typing`) to the user's chat.
2. The typing indicator should repeat periodically while the agent is still working (Telegram typing indicators expire after ~5 seconds).
3. The typing indicator must stop when agent output is received or the session ends.
4. Failure to send a typing indicator must not crash the session or interfere with normal message relay — treat send errors as non-critical (log and continue).
5. This is a lower-priority enhancement. It depends on the idle timer fix (ticket: fix-idle-timer-reset-on-agent-output) being completed first, as that ticket establishes the agent-output activity tracking this feature builds on.

### QA Steps

1. Start a session and send a message that triggers a long agent operation. Verify the Telegram chat shows a "typing..." indicator while the agent is working.
2. Verify the typing indicator stops once the agent sends its response.
3. Verify that if the typing indicator send fails (e.g., network error), the session continues normally and the agent response is still delivered.
4. Verify the typing indicator does not appear during normal fast request/response exchanges.

### Technical Context

#### Relevant Files

- **`telegram_bot/session.py`** — Primary file. Add a new background task for the typing indicator heartbeat. The `Session` class already manages background tasks (`_stdout_task`, `_stderr_task`, `_idle_task`) — the typing indicator will follow the same pattern.
- **`telegram_bot/session.py`** (lines 385-388) — `_read_stdout()` already updates `self.last_activity` on each agent output line. The typing indicator can use the same `last_activity` timestamp to detect silence.
- **`telegram_bot/session.py`** (lines 221-225) — `start()` method. Add the new heartbeat task here alongside the existing tasks.
- **`telegram_bot/session.py`** (lines 324-359) — `_finish()` method. The new task must be added to the cancellation loop at lines 344-346.
- **`telegram_bot/bot.py`** — The bot layer needs to provide a typing indicator callback to the Session. The Telegram API call is `await bot.send_chat_action(chat_id=chat_id, action="typing")`.
- **`artifacts/developer/telegram_bot/tests/test_session_idle_timer.py`** — Follow these test patterns for the new feature tests.

#### Patterns and Conventions

- Background tasks follow a consistent pattern in Session: created in `start()`, stored as `self._<name>_task`, cancelled in `_finish()`.
- Async methods use `try/except asyncio.CancelledError: return` for clean cancellation.
- Callbacks are passed into Session via constructor parameters (e.g., `on_response`, `on_end`). The new typing callback should follow this pattern.
- Error handling for non-critical operations: `try/except Exception: logger.exception(...)` — log and continue.

#### Dependencies and Integration Points

- **Depends on**: fix-idle-timer-reset-on-agent-output (must be completed first). That ticket ensures `last_activity` is updated on agent output, which this feature relies on.
- **Telegram API**: `bot.send_chat_action(chat_id=chat_id, action="typing")` — this sends a typing indicator that expires after ~5 seconds. Must be re-sent periodically.
- **`telegram.error` exceptions**: `RetryAfter`, `TimedOut`, `NetworkError`, `Forbidden`, `BadRequest` — all should be caught and logged, not propagated.
- **Session constructor**: Will need a new optional `on_typing` callback parameter (or similar). The `SessionManager.start_session()` method passes callbacks from bot.py into Session — this needs updating too.

#### Implementation Notes

- **Suggested approach**: Add a `_typing_heartbeat()` async method to Session that loops with `asyncio.sleep(5)`, checks if `time.monotonic() - self.last_activity > 5` (configurable), and if so calls the typing callback. Reset the check when output arrives.
- **Alternative simpler approach**: Instead of a new callback, pass the `bot` instance and `chat_id` directly and call `bot.send_chat_action()` from within Session. However, this couples Session to the Telegram API. The callback approach is cleaner and more testable.
- **Add a new parameter** to Session.__init__: `on_typing: Optional[Callable] = None`. If None, no typing indicator is sent (backward compatible).
- **Heartbeat interval**: Use a constant like `_TYPING_HEARTBEAT_INTERVAL = 5` (seconds). The Telegram typing indicator lasts ~5 seconds, so re-sending every 5 seconds keeps it visible.
- **Silence threshold**: Could be the same as `_TYPING_HEARTBEAT_INTERVAL` or configurable. Only start sending typing indicators after no output for this duration.
- **Task lifecycle**: 
  1. Created in `start()`: `self._typing_task = asyncio.create_task(self._typing_heartbeat())`
  2. Cancelled in `_finish()`: add to the task cancellation loop
  3. Self-stops when session ends (checks `self._ended`)
- **Testing**: Mock the `on_typing` callback. Verify it is called after silence period. Verify it is NOT called when output is flowing. Verify exceptions in the callback do not crash the session.
- **Configuration**: Consider making the heartbeat interval configurable via Session.__init__ or a module-level constant. For now, a constant is sufficient.

### Design Context

This is an enhancement to improve UX during long-running agent operations. While the idle timer fix prevents premature session death, users may still be confused by long silences. A typing indicator provides visual feedback that the bot is still active. See `artifacts/designer/design.md`, section "Heartbeat / Typing Indicator (Enhancement)". This is explicitly marked as lower priority than the timer fix and death notifications.
