# send-progress-status-messages

## Metadata
- **From**: task_planner
- **To**: developer

## Content

### Requirements

1. Modify the `_typing_heartbeat` loop in `session.py` (currently lines 480-506) to check `silence_start` against two thresholds on each iteration:
   - **~15 seconds of silence**: Send the status message '⏳ Still working...' to the user via the existing `_on_response` callback (or a similar retry-capable send path). Set `_sent_15s_status = True`.
   - **~60 seconds of silence**: Send the status message '⏳ This is taking a while — still processing your request.' to the user. Set `_sent_60s_status = True`.
2. Each status message must be sent **once** per silence period — check the `_sent_15s_status` / `_sent_60s_status` flags before sending. These flags are reset when agent output arrives (implemented in the prerequisite ticket 'track-silence-start-timestamp').
3. Beyond 60 seconds of silence, no additional status messages are sent. The typing indicator continues as before until the agent responds or idle timeout fires.
4. Status messages must be sent through the same retry-capable send path as normal agent responses (the `_on_response` callback with retry and circuit breaker logic in `bot.py`).
5. Status messages must be prefixed with the hourglass emoji (⏳) to visually distinguish them from agent responses.
6. Do NOT delete or edit status messages after the agent eventually responds — keep the implementation simple.
7. Errors sending status messages should be logged and swallowed (same pattern as typing indicator errors) — a failed status message must never crash the session.

### QA Steps

1. Start a session and send a prompt that triggers a long agent operation (e.g., a complex code generation task). Verify that after ~15 seconds of silence, the message '⏳ Still working...' appears in the chat.
2. Continue waiting and verify that after ~60 seconds of silence, the message '⏳ This is taking a while — still processing your request.' appears.
3. Verify that no additional status messages appear beyond the 60-second message, even if the agent remains silent for several more minutes.
4. After the agent responds, send another prompt that triggers a long operation. Verify that the 15s and 60s messages fire again (timers reset properly).
5. Verify that if the agent produces output at 10 seconds (before the 15s threshold), no status message is sent.
6. Verify that if the agent produces output between 15s and 60s, the 60s message is NOT sent (flags reset on output).
7. Verify that status messages appear with the ⏳ prefix and are visually distinct from agent responses.
8. Verify that the typing indicator continues to fire every 5 seconds regardless of status messages.
9. Verify that if `_on_response` fails when sending a status message, the error is logged but the session continues normally.

### Technical Context

#### Relevant Files

- **`telegram_bot/session.py`** (primary) — The `Session` class, specifically `_typing_heartbeat` (lines 483-509).
  - `_typing_heartbeat` (lines 483-509): The main loop to modify. Currently sleeps for `_TYPING_HEARTBEAT_INTERVAL` (5s), checks elapsed time since `last_activity`, and sends typing indicator if silent. Add silence threshold checks here.
  - `__init__` (lines 172-209): Where `silence_start`, `_sent_15s_status`, `_sent_60s_status` live (added by prerequisite ticket).
  - `_read_stdout` (lines 375-442): Resets `silence_start` and the status flags on agent output. No changes needed here.
  - `_on_response` callback (stored at line 190): The async callback to invoke for sending status messages. Same path used for normal agent responses.
- **`artifacts/developer/telegram_bot/session.py`** — Developer's working copy where changes should be made.
- **`telegram_bot/bot.py`** (read-only context):
  - `on_response` closure (lines 345-380): The callback that calls `send_long_message` with retry and circuit breaker logic. Status messages go through this same path.
  - `retry_send_message` (lines 165-240): Retry logic with exponential backoff.
  - `send_long_message` (lines 243-269): Splits long messages and retries each chunk.
- **`artifacts/developer/telegram_bot/tests/test_typing_heartbeat.py`** — Existing heartbeat tests. Add new test cases for progress status messages here.
- **`artifacts/developer/telegram_bot/tests/test_silence_start.py`** — Tests for silence_start; useful reference for mocking patterns.

#### Patterns and Conventions

- **Error handling in heartbeat**: Follow the existing pattern at lines 501-507 — wrap the callback call in try/except, log with `logger.exception()`, and continue the loop. Apply the same pattern to status message sends.
- **Test pattern**: Use `_make_session()` helper, `patch("telegram_bot.session.asyncio.sleep", ...)` to control loop iterations, and `session._ended = True` to terminate the loop. See `test_typing_heartbeat.py` for examples.
- **Mocking**: `from mock import AsyncMock, MagicMock, patch` — not `unittest.mock`.
- **Constants**: Define threshold constants at module level (e.g., `_PROGRESS_15S_THRESHOLD = 15`, `_PROGRESS_60S_THRESHOLD = 60`) following the pattern of `_TYPING_HEARTBEAT_INTERVAL`.

#### Dependencies and Integration Points

- **Prerequisite**: `track-silence-start-timestamp` must be implemented first. It provides `silence_start` (initialized to `time.monotonic()` at session start), `_sent_15s_status`, and `_sent_60s_status` flags on the Session instance, plus the reset logic in `_read_stdout`.
- **`_on_response` callback**: This is set in `Session.__init__` (line 190) and wired to the `on_response` closure in `bot.py` (line 345). Calling `await self._on_response(self.chat_id, "⏳ Still working...")` will route the status message through the same retry + circuit breaker path as normal agent responses. This is the correct send path.
- **Circuit breaker (bot.py lines 342-380)**: Status messages flowing through `_on_response` will count toward the circuit breaker's consecutive failure tracker. This is acceptable — if Telegram sends are failing, status messages should also fail gracefully.
- **Typing indicator**: The typing indicator send (`self._on_typing`) is independent and must continue firing every 5s regardless of status messages.

#### Implementation Notes

1. **Add threshold constants** at module level near `_TYPING_HEARTBEAT_INTERVAL` (line 32):
   ```python
   _PROGRESS_15S_THRESHOLD = 15
   _PROGRESS_60S_THRESHOLD = 60
   ```
2. **Modify `_typing_heartbeat`**: After the existing typing indicator send (line 502), add silence threshold checks:
   ```python
   # Check progress status message thresholds
   if self.silence_start is not None:
       silence_elapsed = time.monotonic() - self.silence_start
       if silence_elapsed >= _PROGRESS_15S_THRESHOLD and not self._sent_15s_status:
           self._sent_15s_status = True
           try:
               await self._on_response(self.chat_id, "\u23f3 Still working...")
           except Exception:
               logger.exception("Failed to send 15s status message for chat %d.", self.chat_id)
       if silence_elapsed >= _PROGRESS_60S_THRESHOLD and not self._sent_60s_status:
           self._sent_60s_status = True
           try:
               await self._on_response(self.chat_id, "\u23f3 This is taking a while \u2014 still processing your request.")
           except Exception:
               logger.exception("Failed to send 60s status message for chat %d.", self.chat_id)
   ```
3. **Timing precision**: The heartbeat fires every 5s, so the 15s message will fire at ~15-20s and 60s at ~60-65s. This is acceptable per the "approximately" language in the requirements.
4. **Test cases to add**: (a) 15s message fires after threshold, (b) 60s message fires after threshold, (c) no messages before 15s, (d) no additional messages after 60s, (e) flags reset on output and messages fire again, (f) send failure is logged and swallowed, (g) typing indicator continues alongside status messages.
5. **Edge case**: `silence_start` could be `None` if `_read_stdout` hasn't processed any output yet (before the prerequisite ticket changes initialization). After the prerequisite is done, `silence_start` is always a float, but defensive `is not None` check is still good practice.

### Design Context

This ticket implements the user-visible progress status messages described in the 'Progress Status Messages' subsection of the design (see artifacts/designer/design.md, lines 224-241). The motivation is that the typing indicator alone makes the bot appear frozen during long agent operations — users need explicit textual feedback. This ticket depends on 'track-silence-start-timestamp' which provides the silence_start tracking and per-silence-period flags.
