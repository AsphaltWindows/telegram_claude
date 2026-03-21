# fix-extract-text-from-result-events

## Metadata
- **From**: developer
- **To**: qa

## Content

### Summary of Changes

Fixed the critical bug where the bot goes silent after agent tool use. Modified _extract_text_from_event() to extract text ONLY from result events, which contain the complete authoritative turn output. Moved assistant and content_block_delta events to the skip list. Added INFO-level logging for high-signal filtered events (tool_use, tool_result, error) and for extracted text previews.

### Files Changed

- **artifacts/developer/telegram_bot/session.py** — Rewrote _extract_text_from_event() to extract text only from result events. assistant and content_block_delta are now skipped. Added INFO-level logging for tool_use (with tool name), tool_result, error, and extracted text preview (first 80 chars).
- **artifacts/developer/telegram_bot/tests/test_result_event.py** — Updated integration tests to reflect new behavior: text comes only from result events, not from streaming deltas. Updated test_assistant_event_still_works -> test_assistant_event_now_skipped, test_content_block_delta_still_works -> test_content_block_delta_now_skipped. Updated tool-use and multi-tool-use chain tests.
- **artifacts/developer/telegram_bot/tests/test_event_logging.py** — New test file (17 tests) verifying INFO vs DEBUG log levels for all event types.
- **artifacts/developer/telegram_bot/tests/test_session_idle_timer.py** — Updated test_read_stdout_resets_before_on_response_callback to use a result event instead of assistant event (since assistant no longer triggers on_response).

### Requirements Addressed

1. Extract text only from result events — done.
2. Stop extracting from assistant and content_block_delta — done, they return None.
3. Continue skipping all other event types — done.
4. Reuse _extract_text_from_content() for result parsing — done (via existing _extract_text_from_result helper).
5. Empirical verification — could not run claude CLI in this environment; the implementation handles multiple result event shapes defensively via _extract_text_from_result().
6. Result event as end-of-turn signal — already handled by existing _read_stdout dedup logic which resets _turn_delivered_text on result events.
7. INFO-level logging for high-signal events and extracted text — done.

### QA Steps

1. Send a message that triggers tool use (e.g., 'read session.py'). Verify the bot delivers the final response text after tools complete. The bot must NOT go silent.
2. Send a prompt triggering multiple sequential tool calls. Verify all final text is delivered.
3. Send a basic message that does NOT trigger tool use. Verify the response is delivered normally.
4. Verify response text is delivered exactly once (no duplicates).
5. Verify typing indicator is active during tools and stops after final response.
6. Test agent's final output being empty after tool use — should not hang or crash.
7. Check INFO logs for tool_use/tool_result filtering and extracted text preview.

### Test Coverage

17 new tests in test_event_logging.py covering:
- tool_use, tool_result, error logged at INFO
- assistant, content_block_delta, ping, system, etc. logged at DEBUG
- result with text logged at INFO with preview
- result without text logged at DEBUG
- tool name extraction and truncation

Updated tests in test_result_event.py and test_session_idle_timer.py.

Run: python -m pytest artifacts/developer/telegram_bot/tests/ -v

### Notes

- The deduplication logic (_deduplicate_result_text, _turn_delivered_text) is now effectively a no-op since deltas no longer accumulate text. It is kept for safety but could be simplified in a future cleanup.
- The _extract_text_from_result helper handles multiple result event payload shapes defensively (plain string, content blocks, nested message).
