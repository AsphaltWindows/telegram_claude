# telegram-send-retry-with-logging

## Metadata
- **From**: product_manager
- **To**: task_planner

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

### Design Context

Addresses the 'Retry Strategy', 'Behavior When Retries Are Exhausted', and 'Logging Requirements' sections of the Telegram Send Error Handling design. See artifacts/designer/design.md, section 'Telegram Send Error Handling'. Motivated by a user-reported bug where the bot silently drops messages when Telegram API calls fail, making the bot appear to ignore the user.
