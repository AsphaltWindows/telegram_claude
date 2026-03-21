# QA Report: Add Typing Indicator Heartbeat

## Metadata
- **Ticket**: add-typing-indicator-heartbeat
- **Tested**: 2026-03-20T00:00:00Z
- **Result**: PASS (automated only; manual steps pending)

## Steps

### Step 1: Start a session and send a message that triggers a long agent operation. Verify the Telegram chat shows a 'typing...' indicator while the agent is working.
- **Result**: SKIPPED (requires interactive Telegram testing)
- **Notes**: Code inspection confirms: `_typing_heartbeat()` loops every 5s, checks `last_activity` staleness, and calls `on_typing(chat_id)` which maps to `bot.send_chat_action(action="typing")`. Logic is correct.

### Step 2: Verify the typing indicator stops once the agent sends its response.
- **Result**: SKIPPED (requires interactive Telegram testing)
- **Notes**: Code inspection confirms: `_read_stdout()` updates `last_activity` on every line, so `_typing_heartbeat()` will see fresh activity and skip sending. When session ends, `_ended` flag stops the loop. Test `test_typing_heartbeat_not_sent_during_activity` validates this.

### Step 3: Verify that if the typing indicator send fails (e.g., network error), the session continues normally and the agent response is still delivered.
- **Result**: PASS (via test + code inspection)
- **Notes**: `_typing_heartbeat()` wraps the callback in try/except Exception with `logger.exception`. Test `test_typing_heartbeat_handles_callback_exception` confirms this. Errors are non-fatal.

### Step 4: Verify the typing indicator does not appear during normal fast request/response exchanges.
- **Result**: PASS (via test + code inspection)
- **Notes**: The heartbeat only fires after `_TYPING_HEARTBEAT_INTERVAL` (5s) of silence. Fast exchanges keep `last_activity` fresh, preventing the indicator. Test `test_typing_heartbeat_not_sent_during_activity` validates this.

## Automated Tests

All 8 typing heartbeat tests pass. Full suite: 127 passed, 1 skipped, 0 failures.

## Code Review Observations

1. `on_typing` parameter is optional (defaults to None) - backward compatible
2. `_typing_task` is properly included in `_finish()` cancellation alongside other tasks
3. `_TYPING_HEARTBEAT_INTERVAL = 5` matches Telegram's typing indicator expiry
4. The heartbeat reuses the same `last_activity` field as `_read_stdout()` - clean design
5. `on_typing` closure in bot.py correctly calls `bot.send_chat_action(action="typing")`

## Summary

Implementation is correct and well-tested. All automated tests pass with no regressions. Steps 1 and 2 require interactive Telegram testing to fully verify end-to-end behavior, but code inspection and unit tests give high confidence. Steps 3 and 4 are fully validated via tests and code review. Recommend interactive verification at next opportunity.
