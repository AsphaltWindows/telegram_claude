# update-stale-session-tests-for-result-extraction

## Metadata
- **From**: product_manager
- **To**: task_planner

## Content

### Requirements

1. Update the 5 failing `TestExtractTextFromEvent` tests in `tests/test_session.py` to match the new result-only extraction logic implemented in `telegram_bot/session.py`. Specifically:
   - `test_assistant_message_event`: Change assertion to expect `None` (assistant events no longer produce extracted text).
   - `test_assistant_multi_block_content`: Change assertion to expect `None`.
   - `test_content_block_delta_text`: Change assertion to expect `None` (content_block_delta events no longer produce extracted text).
   - `test_assistant_with_string_content`: Change assertion to expect `None`.
   - `test_result_with_text_skipped`: Change assertion to expect the result text to be **extracted** (not skipped). The result event's content blocks with `type: text` should be joined and returned.

2. Update the 2 failing `TestSessionReading` integration tests in `tests/test_session.py`:
   - `test_stdout_json_events_invoke_on_response`: Update to reflect that `_on_response` is now called when result events arrive (not assistant/content_block_delta events).
   - `test_stdout_skips_non_text_events`: Update expected skip/extract behavior to match the new logic — result events with text content should be extracted, assistant/content_block_delta events should be skipped.

3. Do NOT modify `tests/test_result_event.py` — those 29 tests already pass and cover the new logic correctly.

4. Do NOT modify the production code in `telegram_bot/session.py` — only test files should change.

5. After changes, the full test suite must pass with zero failures.

### QA Steps

1. Run `python -m pytest tests/test_session.py -v` and verify all tests pass, including the 7 previously failing tests listed above.

2. Run `python -m pytest tests/test_result_event.py -v` and verify all 29 tests still pass (regression check).

3. Run `python -m pytest` (full suite) and verify zero failures.

4. Review the updated test assertions to confirm they accurately reflect the new extraction logic: result events produce text, assistant/content_block_delta events return None.

### Design Context

After the fix-bot-silent-after-agent-tool-use ticket was implemented, `_extract_text_from_event()` was changed to extract text only from `result` events (instead of `assistant` and `content_block_delta` events). See `artifacts/designer/design.md`, section on result-only extraction. The new `tests/test_result_event.py` was written to cover the new behavior, but 7 old tests in `tests/test_session.py` still assert the previous behavior. This ticket updates those stale tests to be consistent. Forum topic: `2026-03-20T12-00-00Z-qa-stale-session-tests.md`.
