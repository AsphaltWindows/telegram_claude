# QA Report: Fix duplicate message delivery by skipping `result` events

## Metadata
- **Ticket**: Fix duplicate message delivery by skipping `result` events in stream-JSON parsing
- **Tested**: 2026-03-09T03:15:00Z
- **Result**: PASS

## Steps

### Step 1: Code review — `result` events return `None`
- **Result**: PASS
- **Notes**: `"result"` is in the skip-list tuple (line 87 of `session.py`). No separate branch exists for result events. `_extract_text_from_event()` returns `None` for all result events.

### Step 2: Code review — `assistant` event unchanged
- **Result**: PASS
- **Notes**: The assistant branch (lines 74-76) extracts text from content blocks exactly as before. No modifications to this path.

### Step 3: Code review — only one `on_response` call per turn
- **Result**: PASS
- **Notes**: With result events now skipped (returning `None`), only the `assistant` event triggers the `on_response` callback in `_read_stdout()`. The `if text:` guard on line 391 ensures `None` returns are not relayed.

### Step 4: Unit tests — all 56 pass
- **Result**: PASS
- **Notes**: `python -m pytest tests/test_session.py -v` — 56 passed in 6.13s. Key tests:
  - `test_result_with_text_skipped` — result events with text return `None`
  - `test_result_without_text_skipped` — result events without text return `None`
  - `test_result_with_dict_payload_skipped` — result events with dict payloads return `None`
  - `test_assistant_message_event` — assistant events still return text (no regression)
  - `test_stdout_json_events_invoke_on_response` — end-to-end stdout reading still works

### Step 5: Docstring updated
- **Result**: PASS
- **Notes**: The docstring for `_extract_text_from_event()` documents that result events are skipped because they are turn-level summaries that duplicate content already delivered via the assistant event.

### Step 6: Manual integration tests (deferred)
- **Result**: N/A (requires live bot)
- **Notes**: The following manual QA steps from the ticket require a running Telegram bot and Claude subprocess:
  1. Start a session and send a message — verify exactly one response per turn
  2. Enable DEBUG logging — verify result events log as skipped, assistant events return text
  3. Multi-turn conversations — verify no regressions across turns
  4. Verify full response text is delivered (no truncation)

  These should be tested when the bot is next deployed.

## Summary

The implementation is clean and correct. The developer chose the "cleanest fix" approach: removing the separate result branch entirely and adding `"result"` to the skip-list tuple. This eliminates dead code and provides DEBUG-level logging for result events. All 56 unit tests pass, including three new tests specifically covering result event skipping. The assistant event path is untouched, confirming no regression risk.

Manual integration testing with a live bot is recommended before considering this fully validated, but the automated verification gives high confidence in the fix.
