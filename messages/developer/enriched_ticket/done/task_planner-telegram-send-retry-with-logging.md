# telegram-send-retry-with-logging

## Metadata
- **From**: task_planner
- **To**: developer

## Content

### Requirements

1. Create a reusable async retry wrapper (e.g., `retry_send_message(bot, chat_id, text)`) that wraps `bot.send_message()` calls with retry logic. All Telegram send calls in the response delivery path (`send_long_message` and any direct `bot.send_message()` calls for user notifications) must use this wrapper.

2. The retry wrapper must attempt a maximum of 3 attempts (1 initial + 2 retries).

3. Backoff between retries must be exponential: 1s after first failure, 2s after second failure, 4s after third failure (using `asyncio.sleep`).

4. When a `RetryAfter` exception is raised, use the server-provided `retry_after` value as the sleep duration instead of the standard exponential backoff.

5. Classify errors as retryable or non-retryable:
   - **Retryable**: `TimedOut`, `NetworkError`, `RetryAfter` (from python-telegram-bot exceptions)
   - **Non-retryable**: `BadRequest`, `Forbidden` — fail immediately with no retry

6. On every failed send attempt (whether retried or not), log at ERROR level with: exception type and message, chat_id, message length in characters, retry attempt number formatted as 'attempt N/3'.

7. When all retries are exhausted and the message is permanently dropped, additionally log the first 200 characters of the message content (truncated).

8. After all retries are exhausted, do NOT attempt to send a 'delivery failed' notification to the user.

9. After all retries are exhausted for a single message, do NOT crash or raise an unhandled exception that would terminate the session. The session must remain alive so transient issues can self-resolve.

10. The retry wrapper must return a boolean (or similar signal) indicating success or failure, so callers (including the future circuit breaker) can track outcomes.

### QA Steps

1. **Unit test — successful send**: Mock `bot.send_message` to succeed on first call. Verify the message is sent exactly once with no sleep/delay.

2. **Unit test — retry then succeed**: Mock `bot.send_message` to raise `TimedOut` on first call, then succeed on second call. Verify exactly 2 calls were made and `asyncio.sleep(1)` was called between them.

3. **Unit test — all retries exhausted**: Mock `bot.send_message` to raise `NetworkError` on all 3 attempts. Verify 3 total calls, exponential sleeps of 1s and 2s, and that no exception propagates to the caller.

4. **Unit test — non-retryable error**: Mock `bot.send_message` to raise `BadRequest`. Verify exactly 1 call (no retries) and that the function returns a failure signal.

5. **Unit test — RetryAfter handling**: Mock `bot.send_message` to raise `RetryAfter(retry_after=10)` on first call, then succeed. Verify sleep was called with 10 (server value), not 1 (standard backoff).

6. **Unit test — logging on exhausted retries**: Mock all 3 attempts to fail. Capture log output and verify it contains: exception type, chat_id, message length, 'attempt 3/3', and the first 200 characters of the message.

7. **Unit test — logging does not include content on non-final failures**: Mock first attempt to fail, second to succeed. Verify log for attempt 1 does NOT include message content.

8. **Integration test**: Verify that `send_long_message` uses the retry wrapper for each chunk it sends.

### Technical Context

#### Relevant Files

- **`telegram_bot/bot.py`** (MODIFY) — Main file to modify. Contains `send_long_message()` (line 163) which calls `bot.send_message()` directly at line 180. The new `retry_send_message()` function should be added here, and `send_long_message()` updated to use it. Also contains `on_response` callback (line 252) and `on_end` callback (line 255) which both call `send_long_message` — these will inherit retry behavior automatically once `send_long_message` is updated.
- **`telegram_bot/bot.py` — `agent_command_handler()`** (line 212) — Uses `update.message.reply_text()` for error/confirmation messages. These are NOT in the response delivery path (they are one-off notifications), so they do NOT need the retry wrapper per the requirements.
- **`artifacts/developer/telegram_bot/tests/test_bot.py`** (MODIFY) — Existing test file for `bot.py`. Add new test classes here for the retry wrapper. Follow the existing patterns: `pytest.mark.asyncio`, `MagicMock`/`AsyncMock` from `mock`, test class grouping by feature.
- **`telegram_bot/session.py`** (READ ONLY) — Contains `Session` class and `SessionManager`. The `_read_stdout` method (line 361) calls `self._on_response(self.chat_id, text)` which is bound to the `on_response` callback in `bot.py` that calls `send_long_message`. No changes needed here — retry is injected at the `bot.py` layer.

#### Patterns and Conventions

- **Async throughout**: The codebase uses `async/await` consistently. The retry wrapper must be `async def`.
- **Logging**: Uses `logging.getLogger(__name__)` with a module-level `logger` variable (already exists in `bot.py`).
- **Imports**: python-telegram-bot exceptions are in `telegram.error` — import `TimedOut`, `NetworkError`, `RetryAfter`, `BadRequest`, `Forbidden` from there.
- **Test patterns**: Tests use `pytest.mark.asyncio`, `MagicMock`/`AsyncMock` from `mock` (not `unittest.mock`), test classes grouped by feature with `Test` prefix, helper functions prefixed with `_make_`.
- **Docstrings**: NumPy-style docstrings with Parameters/Returns/Raises sections.
- **Type hints**: Used throughout with `from __future__ import annotations`.
- **No parse_mode**: Messages are sent as plain text — `bot.send_message(chat_id=chat_id, text=chunk)` with no parse_mode argument. Maintain this.

#### Dependencies and Integration Points

- **python-telegram-bot exceptions** (`telegram.error`): `TimedOut`, `NetworkError`, `RetryAfter`, `BadRequest`, `Forbidden`. The `RetryAfter` exception has a `retry_after` attribute (integer seconds).
- **`asyncio.sleep`**: Used for backoff delays. Must be patchable in tests (patch `asyncio.sleep` or the module-level reference).
- **`send_long_message()`** at line 163-180: Currently calls `bot.send_message()` directly in a loop over chunks. Must be updated to call `retry_send_message()` instead.
- **`on_response` callback** (line 252-253): Calls `send_long_message(bot, cid, text)` — will get retry behavior automatically.
- **`on_end` callback** (line 255-268): Calls `send_long_message(bot, cid, msg)` inside a try/except — will get retry behavior automatically. The existing try/except at line 268-269 already catches exceptions from this path, which is consistent with requirement 9.
- **Future circuit breaker** (next ticket): Will consume the boolean return value from `retry_send_message()`. Design the return value with this in mind — `True` for success, `False` for failure.

#### Implementation Notes

1. **Create `retry_send_message()`** as an async function in `bot.py`, placed after `split_message()` and before `send_long_message()`. Signature: `async def retry_send_message(bot, chat_id: int, text: str, max_attempts: int = 3) -> bool`.
2. **Backoff calculation**: `delay = 2 ** (attempt - 1)` where attempt is 0-indexed (gives 1, 2, 4). But only sleep between retries, so after attempt 0 failure sleep 1s, after attempt 1 failure sleep 2s. That means only 2 sleeps for 3 attempts.
3. **RetryAfter special case**: Catch `RetryAfter` separately, read its `retry_after` attribute for the sleep duration, then continue to next attempt.
4. **Return value**: Return `True` on successful send, `False` if all retries exhausted or non-retryable error.
5. **Update `send_long_message()`**: Change `await bot.send_message(chat_id=chat_id, text=chunk)` to `await retry_send_message(bot, chat_id, chunk)`. Consider whether `send_long_message` should also return success/failure — it should, to support the circuit breaker in the next ticket. Return `True` only if ALL chunks succeeded.
6. **Do NOT wrap `update.message.reply_text()` calls** — those are direct user replies (confirmations, errors), not response delivery path sends.
7. **Exception handling order**: Catch non-retryable (`BadRequest`, `Forbidden`) first to fail fast, then retryable (`TimedOut`, `NetworkError`, `RetryAfter`) with retry logic.

### Design Context

Addresses the 'Retry Strategy', 'Behavior When Retries Are Exhausted', and 'Logging Requirements' sections of the Telegram Send Error Handling design. See artifacts/designer/design.md, section 'Telegram Send Error Handling'. Motivated by a user-reported bug where the bot silently drops messages when Telegram API calls fail, making the bot appear to ignore the user.
