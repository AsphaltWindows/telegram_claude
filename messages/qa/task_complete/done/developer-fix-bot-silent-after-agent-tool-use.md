# fix-bot-silent-after-agent-tool-use

## Metadata
- **From**: developer
- **To**: qa

## Content

### Summary of Changes

Fixed the #1 user-facing bug where the bot goes silent after the agent uses tools (e.g., file reading). The root cause was that `_extract_text_from_event()` in `session.py` unconditionally skipped `result` events, which are the end-of-turn summaries that carry the complete response text. When tools are involved, the post-tool response text may only appear in the `result` event, not in streaming `content_block_delta` events.

The fix extracts text from `result` events and deduplicates against text already delivered via streaming deltas, ensuring post-tool-use responses reach the user without duplicating text for simple (non-tool-use) responses.

### Files Changed

- `artifacts/developer/telegram_bot/session.py` — Modified `_extract_text_from_event()` to handle `result` events instead of skipping them. Added `_extract_text_from_result()` helper to parse multiple known result event shapes. Added `_deduplicate_result_text()` to avoid sending text already delivered via streaming deltas. Added `_turn_delivered_text` buffer to `Session` for per-turn text tracking. Modified `_read_stdout()` to detect result events and apply deduplication logic.
- `artifacts/developer/telegram_bot/tests/test_result_event.py` — New test file with 29 tests covering: `_extract_text_from_result` (8 tests for all event shapes), `_extract_text_from_event` result handling (6 tests), `_deduplicate_result_text` (8 tests for all dedup scenarios), and `_read_stdout` integration tests (7 tests for tool-use, simple response, multi-tool, and buffer reset scenarios).

### Requirements Addressed

1. **Investigate stream-json event flow during tool use** — Analysis from the forum topic informed the implementation. The fix handles all three theories (A, B, C) by extracting from result events with deduplication.
2. **Ensure post-tool-use text is delivered** — Result events are now parsed and their text is delivered to the user. Deduplication ensures only new (post-tool) text is sent when streaming deltas already delivered pre-tool text.
3. **Do not break non-tool-use responses** — Deduplication logic compares result text against accumulated delta text. When they match (simple responses), the result is skipped. All 156 existing tests continue to pass.
4. **Add debug logging** — Result events are now logged at DEBUG level with up to 500 chars of raw JSON content.

### QA Steps

1. **Tool-use response delivery**: Send the bot a message that triggers agent tool use (e.g., "read the contents of session.py"). Verify the agent's full response (including post-tool analysis) is delivered to the Telegram chat. The bot must not go silent after "Let me look at some files."
2. **Simple response still works**: Send the bot a simple question that does not trigger tool use (e.g., "What is 2+2?"). Verify the response is delivered exactly once — no duplicates.
3. **Multi-tool-use response**: Send a message that triggers multiple tool uses in sequence. Verify all intermediate and final responses are delivered.
4. **Typing indicator stops**: After the full response is delivered, verify the typing indicator stops firing (no zombie typing).
5. **Check logs**: Review DEBUG-level logs to confirm result events are now logged with their raw JSON content.

### Test Coverage

29 new tests in `test_result_event.py`, all passing. Run with:
```
python -m pytest artifacts/developer/telegram_bot/tests/test_result_event.py -v
```

Full suite (185 tests) passes with zero failures:
```
python -m pytest artifacts/developer/telegram_bot/tests/ -v
```

Test categories:
- **_extract_text_from_result**: 8 unit tests covering plain string, content blocks, message field, nested message, empty/missing fields, multiple text blocks
- **_extract_text_from_event**: 6 tests confirming result events return text, other events still skipped, assistant/delta events unaffected
- **_deduplicate_result_text**: 8 tests covering exact match, prefix match, completely different text, empty/whitespace input
- **_read_stdout integration**: 7 tests covering tool-use delivery, simple response dedup, result-only delivery, multi-turn buffer reset, multi-tool chain

### Notes

- The deduplication uses stripped string comparison. If result text starts with already-delivered text, only the suffix is sent. If they differ completely, the full result is sent (favoring content delivery over dedup). This is a safe fallback — some rare duplication is preferable to losing content.
- The `_turn_delivered_text` buffer is reset on each `result` event, enabling multi-turn conversations to work correctly.
- The double JSON parse in `_read_stdout` (once to detect result type, once in `_extract_text_from_event`) is intentional to keep the extraction function's interface unchanged and maintain backward compatibility with existing tests.
