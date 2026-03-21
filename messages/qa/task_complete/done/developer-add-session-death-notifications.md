# add-session-death-notifications

## Metadata
- **From**: developer
- **To**: qa

## Content

### Summary of Changes

Updated session death notification messages to match the spec and added comprehensive tests.

### Files Changed

- **telegram_bot/bot.py** - Updated on_end callback messages: timeout now says 'timed out after 10 minutes of inactivity. Work has been saved.', crash now includes stderr inline (not in code block). Circuit breaker notification now uses max_attempts=1.
- **telegram_bot/tests/test_bot.py** - Added TestSessionDeathNotifications class (7 tests) and TestCircuitBreakerNotification class (1 test). Updated 2 existing tests to match new message formats.

### Requirements Addressed

1. Timeout message: Updated to 'Session with `<agent_name>` timed out after 10 minutes of inactivity. Work has been saved.' - DONE
2. Crash message: Updated to include stderr inline: 'Session with `<agent_name>` ended unexpectedly. {stderr_tail}' - DONE
3. Circuit breaker: Message already matched spec. Changed to max_attempts=1 since channel is already unreliable - DONE
4. Session cleanup after termination: Already implemented via _finish() ordering (cleanup before on_end) - verified
5. No silent session death: All termination paths send notification - verified via tests

### QA Steps

1. Simulate an idle timeout (wait 10 minutes or temporarily lower the timeout). Verify the user receives the timeout notification message in Telegram.
2. Kill the agent subprocess externally (e.g., kill -9 the claude process). Verify the user receives the unexpected crash notification with stderr content.
3. Simulate 5 consecutive Telegram send failures. Verify the circuit breaker triggers and attempts to send the circuit breaker notification.
4. After each termination scenario, send a new message to the bot and verify it responds with the 'No active session' prompt.
5. Review all session termination code paths and confirm each one sends a user-facing message before cleanup.

### Test Coverage

8 new tests added:
- TestSessionDeathNotifications: test_timeout_message_format, test_crash_message_with_stderr, test_crash_message_without_stderr, test_shutdown_message_format, test_unknown_reason_message, test_on_end_send_failure_logged, test_on_end_exception_does_not_propagate
- TestCircuitBreakerNotification: test_circuit_breaker_uses_single_attempt

2 existing tests updated to match new message formats.

Run: cd artifacts/developer && python -m pytest telegram_bot/tests/test_bot.py -v

### Notes

- The crash message format changed from a separate markdown code block for stderr to inline text. This is simpler and avoids markdown parsing issues in Telegram plain text mode.
- Circuit breaker notification changed from default 3 retries to max_attempts=1, since the channel is already proven unreliable at that point.
- The shutdown (user /end) message was not changed as the spec did not require it.
