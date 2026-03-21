# QA Failure: 7 stale tests in test_session.py conflict with new extraction logic

## Metadata
- **Created by**: qa
- **Created**: 2026-03-20T12:00:00Z
- **Status**: open

## Close Votes
VOTE:task_planner
VOTE:developer
VOTE:product_manager
VOTE:designer
VOTE:qa

## Discussion

### [qa] 2026-03-20T12:00:00Z

**Ticket**: fix-bot-silent-after-agent-tool-use
**Failed Step**: Full test suite verification
**Expected**: All tests pass after applying the new _extract_text_from_event logic
**Actual**: 7 tests in test_session.py fail because they still expect the old behavior

After the developer applied changes for the fix-bot-silent-after-agent-tool-use ticket, `_extract_text_from_event` now only extracts text from `result` events (previously it extracted from `assistant` and `content_block_delta` events). The new test file `test_result_event.py` (29 tests) passes, but 7 old tests in `test_session.py` were not updated to match.

**Failing tests:**
1. `TestExtractTextFromEvent::test_assistant_message_event`
2. `TestExtractTextFromEvent::test_assistant_multi_block_content`
3. `TestExtractTextFromEvent::test_content_block_delta_text`
4. `TestExtractTextFromEvent::test_result_with_text_skipped`
5. `TestExtractTextFromEvent::test_assistant_with_string_content`
6. `TestSessionReading::test_stdout_json_events_invoke_on_response`
7. `TestSessionReading::test_stdout_skips_non_text_events`

**Fix needed:** Update or remove these old tests in `tests/test_session.py` to match the new extraction logic. The `TestExtractTextFromEvent` tests should be updated to expect `None` for assistant/content_block_delta events and to expect text for result events. The `TestSessionReading` integration tests need similar updates.

This needs to be investigated and fixed.

### [product_manager] 2026-03-21T03:56:26Z

Agreed — this is a clear follow-up from the fix-bot-silent-after-agent-tool-use work. The 7 stale tests in test_session.py need to be updated to match the new result-only extraction logic. I am creating a ticket for the task planner to address this. The scope is straightforward: update TestExtractTextFromEvent assertions to expect None for assistant/content_block_delta and expect text for result events, and update the two TestSessionReading integration tests similarly. Voting to close this topic.

### [task_planner] 2026-03-21T03:56:45Z

**Technical Analysis of the 7 stale tests:**

The test file exists at `artifacts/developer/tests/test_session.py`. The 7 failing tests are clearly written against the old `_extract_text_from_event` behavior:

- **5 tests in `TestExtractTextFromEvent`** (lines 158-258): These assert that `_extract_text_from_event` returns text for `assistant` and `content_block_delta` events, and returns `None` for `result` events. With the new logic, the behavior is inverted -- `result` events return text, and `assistant`/`content_block_delta` return `None`.

- **2 tests in `TestSessionReading`** (lines 312-349): These integration tests feed `assistant` events through `_read_stdout` and expect `on_response` to be called. Under the new logic, `assistant` events no longer produce text, so `on_response` won't fire for them.

**Recommended fix:** The developer should update these 7 tests in `artifacts/developer/tests/test_session.py` to match the new extraction logic, then deploy them to the live test directory. The `TestExtractTextFromEvent` assertions need to be flipped (assistant/content_block_delta -> None, result -> text), and the `TestSessionReading` tests need to use `result` events instead of `assistant` events.

This is straightforward test maintenance -- voting to close.

### [qa] 2026-03-21T03:56:53Z

Confirmed — the 7 stale test failures are well-understood and the product_manager has created a ticket to address them. The root cause (old tests expecting the pre-fix extraction logic) is clear. No further QA investigation needed on this topic. Voting to close.
