# info-level-event-logging

## Metadata
- **From**: developer
- **To**: qa

## Content

### Summary of Changes

Implemented INFO-level event logging for high-signal events in _extract_text_from_event() and on_response success logging in bot.py. Most of the session.py work was done as part of the fix-extract-text-from-result-events ticket (same function). The remaining piece was the on_response success log.

### Files Changed

- **artifacts/developer/telegram_bot/bot.py** — Added INFO log in on_response after successful send: 'Message sent to chat {cid} ({len} chars)'.
- **artifacts/developer/telegram_bot/session.py** — (Already modified in fix ticket) tool_use, tool_result, error logged at INFO; assistant, content_block_delta and low-signal events at DEBUG; extracted text previewed at INFO.
- **artifacts/developer/telegram_bot/tests/test_event_logging.py** — Added 2 tests for on_response success logging (logs on success, does not log on failure). Total 19 tests.

### Requirements Addressed

1. tool_use events logged at INFO with tool name — done (in fix ticket).
2. tool_result events logged at INFO — done (in fix ticket).
3. error events logged at INFO with content — done (in fix ticket).
4. Extracted text logged at INFO with 80-char preview — done (in fix ticket).
5. Low-signal events remain at DEBUG — done (in fix ticket).
6. on_response logs success at INFO with chat_id and char count — done.
7. All logs use existing logger instance — done.

### QA Steps

1. Start bot at default LOG_LEVEL (INFO). Send a message triggering tool use. Verify INFO-level lines for tool_use and tool_result events.
2. Send a message triggering text response. Verify INFO-level line with truncated text preview.
3. Verify INFO-level line confirming message sent to user (chat ID and character count).
4. Verify low-signal events (ping, content_block_start, etc.) do NOT appear at INFO.
5. Set LOG_LEVEL=DEBUG and verify all event types appear.
6. Verify no duplicate log lines.

### Test Coverage

19 tests in test_event_logging.py covering all logging behavior.
Run: python -m pytest artifacts/developer/telegram_bot/tests/test_event_logging.py -v

### Notes

- Most session.py logging changes were implemented as part of the fix-extract-text-from-result-events ticket since both tickets modify _extract_text_from_event. This ticket adds the final piece: on_response success logging in bot.py.
