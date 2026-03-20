# implement-telegram-send-retry

## Metadata
- **From**: developer
- **To**: qa

## Content

### Summary of Changes

Implemented a reusable async retry wrapper (`retry_send_message`) for Telegram bot.send_message() calls with exponential backoff, error classification, and structured logging. Updated `send_long_message` to use it.

### Files Changed

- **telegram_bot/bot.py** — Added `retry_send_message()` function with retry logic, updated `send_long_message()` to use it and return bool, added imports for `asyncio` and `telegram.error` exceptions.
- **artifacts/developer/telegram_bot/bot.py** — Synced copy of the above.
- **artifacts/developer/telegram_bot/tests/test_bot.py** — Added 14 new tests: 11 unit tests for `retry_send_message` and 3 integration tests for `send_long_message` with retry.

### Requirements Addressed

1. Created `retry_send_message(bot, chat_id, text, max_attempts=3) -> bool` — reusable async wrapper. `send_long_message` updated to use it for all chunks.
2. Max 3 attempts (1 initial + 2 retries) — implemented via `max_attempts=3` parameter.
3. Exponential backoff: 1s, 2s (via `2 ** attempt` where attempt is 0-indexed). Only 2 sleeps for 3 attempts.
4. RetryAfter handling: catches `RetryAfter`, uses `exc.retry_after` for sleep duration instead of standard backoff.
5. Error classification: `BadRequest`/`Forbidden` fail immediately (no retry), `TimedOut`/`NetworkError`/`RetryAfter` are retried.
6. Logging at ERROR level on every failed attempt with: exception type/message, chat_id, message length, attempt N/max_attempts.
7. On final exhaustion: logs first 200 chars of message content.
8. No delivery-failed notification sent to user after exhaustion.
9. No unhandled exception — function returns False, session stays alive.
10. Returns bool (True=success, False=failure) for future circuit breaker integration.

### QA Steps

1. Unit test — successful send: Mock bot.send_message to succeed on first call. Verify the message is sent exactly once with no sleep/delay.
2. Unit test — retry then succeed: Mock bot.send_message to raise TimedOut on first call, then succeed on second call. Verify exactly 2 calls were made and asyncio.sleep(1) was called between them.
3. Unit test — all retries exhausted: Mock bot.send_message to raise NetworkError on all 3 attempts. Verify 3 total calls, exponential sleeps of 1s and 2s, and that no exception propagates to the caller.
4. Unit test — non-retryable error: Mock bot.send_message to raise BadRequest. Verify exactly 1 call (no retries) and that the function returns a failure signal.
5. Unit test — RetryAfter handling: Mock bot.send_message to raise RetryAfter(retry_after=10) on first call, then succeed. Verify sleep was called with 10 (server value), not 1 (standard backoff).
6. Unit test — logging on exhausted retries: Mock all 3 attempts to fail. Capture log output and verify it contains: exception type, chat_id, message length, 'attempt 3/3', and the first 200 characters of the message.
7. Unit test — logging does not include content on non-final failures: Mock first attempt to fail, second to succeed. Verify log for attempt 1 does NOT include message content.
8. Integration test: Verify that send_long_message uses the retry wrapper for each chunk it sends.

### Test Coverage

14 new tests added to `artifacts/developer/telegram_bot/tests/test_bot.py`:

**TestRetrySendMessage** (11 tests):
- test_successful_send_no_retry — QA step 1
- test_retry_then_succeed — QA step 2
- test_all_retries_exhausted — QA step 3
- test_non_retryable_bad_request — QA step 4
- test_non_retryable_forbidden — QA step 4 (Forbidden variant)
- test_retry_after_uses_server_value — QA step 5
- test_logging_on_exhausted_retries — QA step 6
- test_logging_no_content_on_non_final_failure — QA step 7
- test_returns_true_on_success — explicit return value check
- test_returns_false_on_all_failures — explicit return value check
- test_no_exception_propagates — requirement 9

**TestSendLongMessageWithRetry** (3 tests):
- test_uses_retry_for_each_chunk — QA step 8
- test_returns_false_if_any_chunk_fails — verifies partial failure handling
- test_returns_true_if_all_chunks_succeed — verifies full success

Run with: `python -m pytest artifacts/developer/telegram_bot/tests/test_bot.py -v`
All 63 tests pass (49 existing + 14 new).

### Notes

- `send_long_message` now returns `bool` (was `None`). This is a signature change but backward-compatible since callers can ignore the return value. Designed for circuit breaker integration in the next ticket.
- Both copies of bot.py (telegram_bot/bot.py and artifacts/developer/telegram_bot/bot.py) have been updated.
- The existing `TestSendLongMessage` tests still pass — they use mock bot.send_message directly which bypasses retry (since retry only wraps the actual call).
