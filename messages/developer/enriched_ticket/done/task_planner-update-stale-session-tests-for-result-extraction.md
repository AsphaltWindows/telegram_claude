# update-stale-session-tests-for-result-extraction

## Metadata
- **From**: task_planner
- **To**: developer

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

### Technical Context

#### Relevant Files

**Files to modify:**

- `artifacts/developer/tests/test_session.py` — The test file containing the 7 stale tests. This is the ONLY file to modify. Key locations:
  - Lines 155-258: `TestExtractTextFromEvent` class — 5 tests need assertion changes
  - Lines 312-349: `TestSessionReading` class — 2 integration tests need event type changes
  - Lines 46-59: Helper functions `_make_stream_json_line()` and `_make_assistant_event()` — useful for reference but should not need changes

**Files to read for reference (DO NOT modify):**

- `artifacts/developer/telegram_bot/session.py` — The developer's version with the new extraction logic. Key functions:
  - Lines 47-123: `_extract_text_from_event()` — Now extracts text ONLY from `result` events; `assistant` and `content_block_delta` are in the skip list (lines 107-119)
  - Lines 154-202: `_extract_text_from_result()` — New function that extracts text from result events in multiple payload shapes (plain string, content blocks, nested message)
  - Lines 205-239: `_deduplicate_result_text()` — Deduplication logic for result text vs already-delivered streaming deltas
  - Lines 510-597: `_read_stdout()` — Updated to detect result events, apply deduplication via `_turn_delivered_text` buffer

- `artifacts/developer/telegram_bot/tests/test_result_event.py` — The 29 tests covering the new logic. Good reference for result event shapes and expected behavior. Imports `_extract_text_from_result` and `_deduplicate_result_text` from `telegram_bot.session`.

- `telegram_bot/session.py` — The live production code. **IMPORTANT NOTE**: The live code currently still has the OLD extraction logic (assistant/content_block_delta return text, result is skipped). The developer's new version lives in `artifacts/developer/telegram_bot/session.py`. The production code changes from the previous ticket (fix-bot-silent-after-agent-tool-use) may need to be applied to the live file before or alongside this test update. If the tests are run against the live code as-is, the OLD tests would pass and the UPDATED tests would fail. The tests must match the developer's new version of session.py.

#### Patterns and Conventions

- Tests use `pytest` with `@pytest.mark.asyncio` for async tests
- Test file imports private functions directly: `from telegram_bot.session import _extract_text_from_event, _extract_text_from_content`
- Helper functions follow `_make_*` naming convention (e.g., `_make_stream_json_line`, `_make_assistant_event`, `_make_mock_process`, `_make_session`)
- The test file includes a Python 3.7-compatible `AsyncMock` fallback (lines 20-40)
- `_make_session()` creates a Session with sensible defaults; the Session constructor accepts `on_typing=None` as optional param
- JSON events are encoded as `bytes + b"\n"` for stdout line simulation

#### Dependencies and Integration Points

- `telegram_bot.session` module — the production code being tested
- `_extract_text_from_event()` — the core function whose behavior changed (result-only extraction)
- `_extract_text_from_result()` — new function added; may need to be imported in test_session.py if any new tests reference it directly
- `_deduplicate_result_text()` — new deduplication function; relevant to `_read_stdout` integration tests
- `Session._turn_delivered_text` — new instance attribute (str) for tracking delivered text within a turn
- `Session._filtered_event_count` — new instance attribute (int) for tracking consecutive filtered events

#### Implementation Notes

1. **Start with the 5 unit tests in `TestExtractTextFromEvent`** — these are pure function tests, easiest to fix:
   - `test_assistant_message_event` (line 158): Change `assert ... == "Hello, world!"` to `assert ... is None`
   - `test_assistant_multi_block_content` (line 164): Change `assert ... == "Hello world!"` to `assert ... is None`
   - `test_content_block_delta_text` (line 178): Change `assert ... == "partial"` to `assert ... is None`
   - `test_assistant_with_string_content` (line 252): Change to expect `None`
   - `test_result_with_text_skipped` (line 196): This is the trickiest one — the old test asserts `is None` but now should assert the result text IS extracted. The current event shape is `{"type": "result", "result": "Task completed."}` which `_extract_text_from_result` handles (plain string shape). Change to `assert ... == "Task completed."`
   - Also update docstrings to reflect the new behavior (e.g., "Assistant message events should return None" instead of "should return the text content")

2. **Then fix the 2 integration tests in `TestSessionReading`** — these are more involved:
   - `test_stdout_json_events_invoke_on_response` (line 312): Currently sends two `assistant` events and expects `on_response` called twice. Under the new logic, `assistant` events return `None`, so `on_response` would NOT be called. Change the test to send `result` events instead. Use shapes like `{"type": "result", "result": "Hello"}` and `{"type": "result", "result": "World"}`. Note: with the developer's `_read_stdout`, result events go through deduplication via `_deduplicate_result_text`; since `_turn_delivered_text` starts empty, the full text should be delivered.
   - `test_stdout_skips_non_text_events` (line 332): Currently sends system, assistant, tool_use events and expects only the assistant event triggers `on_response`. Change to send system, result-with-text, tool_use events and expect only the result event triggers `on_response`.

3. **Critical dependency**: The live `telegram_bot/session.py` still has the OLD logic. The developer's new version is in `artifacts/developer/telegram_bot/session.py`. For the updated tests to pass, the production code changes must also be applied. If the developer hasn't already copied their session.py changes to the live file, they should do that first (or as part of this work, even though the ticket says not to modify it — the previous ticket's production changes may simply be unapplied). Check test imports — `test_result_event.py` imports `_extract_text_from_result` and `_deduplicate_result_text` which don't exist in the live code yet.

4. **Helper function for result events**: Consider adding a `_make_result_event(text)` helper similar to the existing `_make_assistant_event(text)` helper, to keep the test code clean. Use the plain string shape: `{"type": "result", "result": text}`.

### Design Context

After the fix-bot-silent-after-agent-tool-use ticket was implemented, `_extract_text_from_event()` was changed to extract text only from `result` events (instead of `assistant` and `content_block_delta` events). See `artifacts/designer/design.md`, section on result-only extraction. The new `tests/test_result_event.py` was written to cover the new behavior, but 7 old tests in `tests/test_session.py` still assert the previous behavior. This ticket updates those stale tests to be consistent. Forum topic: `2026-03-20T12-00-00Z-qa-stale-session-tests.md`.
