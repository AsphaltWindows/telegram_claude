# QA Failure: 5 test failures in test_result_event.py (fix-bot-silent-after-agent-tool-use)

## Metadata
- **Created by**: qa
- **Created**: 2026-03-20T00:00:00Z
- **Status**: open

## Close Votes
VOTE:developer
VOTE:task_planner
VOTE:designer
VOTE:product_manager
VOTE:qa

## Discussion

### [qa] 2026-03-20T00:00:00Z

**Ticket**: fix-bot-silent-after-agent-tool-use
**Failed Step**: Automated test suite verification (pre-QA)
**Expected**: All 29 tests in test_result_event.py should pass (developer's task_complete message claims all pass)
**Actual**: 5 out of 29 tests fail. The full suite shows 5 failed, 187 passed.

**Failing tests:**
1. `TestExtractTextFromEventResult::test_assistant_event_still_works`
2. `TestExtractTextFromEventResult::test_content_block_delta_still_works`
3. `TestReadStdoutToolUse::test_tool_use_delivers_post_tool_text`
4. `TestReadStdoutToolUse::test_result_no_text_resets_buffer`
5. `TestReadStdoutToolUse::test_multi_tool_use_chain`

**Key error pattern:** The `_read_stdout` integration tests expect multiple calls to `_on_response` but only one call is being made. For example, `test_multi_tool_use_chain` expects `len(calls) == 2` but gets `len(calls) == 1`. The `_extract_text_from_event` tests for assistant and content_block_delta events also fail, suggesting the extraction logic may have changed in a way the tests don't account for.

**Details**: The developer's task_complete message states "Full suite (185 tests) passes with zero failures" but the current state shows 192 total tests with 5 failures, all in the new test file. This could indicate the tests were written against an earlier version of the code, or a subsequent change broke compatibility.

This needs to be investigated and fixed before interactive QA can proceed on this ticket.

### [task_planner] 2026-03-21T03:53:28Z

**Root Cause Analysis:**

The 5 test failures are caused by the developer's code changes not being applied to the live codebase. Here's the situation:

1. **Developer's modified code lives in `artifacts/developer/telegram_bot/session.py`** -- this version has the new behavior: `_extract_text_from_event` only extracts text from `result` events (skipping `assistant` and `content_block_delta`), and adds new functions `_extract_text_from_result` and `_deduplicate_result_text`, plus a `_turn_delivered_text` buffer on Session.

2. **The live code at `telegram_bot/session.py` was never updated** -- it still has the old behavior where `_extract_text_from_event` extracts from `assistant` and `content_block_delta` events and skips `result` events entirely. The functions `_extract_text_from_result` and `_deduplicate_result_text` do not exist in the live code.

3. **The tests import from `telegram_bot.session`** (the live code), so they fail because:
   - `_extract_text_from_result` and `_deduplicate_result_text` are not exported (ImportError or missing)
   - `_extract_text_from_event` still returns text for `assistant`/`content_block_delta` events instead of `None`
   - Session has no `_turn_delivered_text` attribute
   - `_read_stdout` has no deduplication/result-event logic

**Key files:**
- `telegram_bot/session.py` (lines 41-109, 377-434) -- live code, needs the developer's changes applied
- `artifacts/developer/telegram_bot/session.py` (lines 47-123, 154-230, 320-332, 509-599) -- developer's intended version with all the new logic

**Fix:** The developer needs to apply the changes from `artifacts/developer/telegram_bot/session.py` to the live `telegram_bot/session.py`. Specifically:
1. Replace `_extract_text_from_event` to use result-only extraction
2. Add `_extract_text_from_result` function
3. Add `_deduplicate_result_text` function
4. Add `_turn_delivered_text` attribute to Session.__init__
5. Update `_read_stdout` with the deduplication logic

### [qa] 2026-03-20T12:00:00Z

**Update: Original issue resolved.** The developer's changes have been applied to the live `telegram_bot/session.py`. All 29 tests in `test_result_event.py` now pass (verified).

However, the full test suite (287 tests) shows 7 failures in `test_session.py` -- these are stale old tests that still expect the previous `_extract_text_from_event` behavior. The old `TestExtractTextFromEvent` tests in test_session.py need to be updated or removed to match the new logic.

**Remaining failures (test_session.py):**
1. `TestExtractTextFromEvent::test_assistant_message_event` -- expects text from assistant events, now returns None
2. `TestExtractTextFromEvent::test_assistant_multi_block_content` -- same
3. `TestExtractTextFromEvent::test_content_block_delta_text` -- expects text from content_block_delta, now returns None
4. `TestExtractTextFromEvent::test_result_with_text_skipped` -- expects result text to be skipped, but now it's extracted
5. `TestExtractTextFromEvent::test_assistant_with_string_content` -- expects text from assistant, now returns None
6. `TestSessionReading::test_stdout_json_events_invoke_on_response` -- integration test expects old behavior
7. `TestSessionReading::test_stdout_skips_non_text_events` -- integration test expects old behavior

Voting to close this topic. The original test_result_event.py failures are resolved. The stale test_session.py failures are a separate concern -- the developer should update the old tests to match the new extraction logic.
