# QA Report: Fix Bot Silent After Agent Tool Use

## Metadata
- **Ticket**: fix-bot-silent-after-agent-tool-use
- **Tested**: 2026-03-21T00:00:00Z
- **Result**: PASS (automated only)

## Steps

### Step 1: Tool-use response delivery
- **Result**: PASS (code review + unit tests)
- **Notes**: `_extract_text_from_event()` now extracts from result events. `_extract_text_from_result()` handles all known payload shapes (plain string, content blocks, nested message). 8 unit tests cover all shapes. 7 integration tests verify tool-use delivery flow. Manual live-bot testing recommended.

### Step 2: Simple response still works
- **Result**: PASS (code review + unit tests)
- **Notes**: `_deduplicate_result_text()` correctly skips result text that matches already-delivered streaming deltas. 8 dedup tests cover exact match, prefix match, empty input, and fallback scenarios.

### Step 3: Multi-tool-use response
- **Result**: PASS (code review + unit tests)
- **Notes**: Multi-tool chain integration test verifies sequential tool uses. `_turn_delivered_text` buffer resets on each result event, enabling multi-turn correctness.

### Step 4: Typing indicator stops
- **Result**: PASS (code review)
- **Notes**: Typing heartbeat stops when `_ended` is set. Result events reset silence tracking. No zombie typing possible after session ends.

### Step 5: Check logs
- **Result**: PASS (code review)
- **Notes**: Result events logged at DEBUG with up to 500 chars of raw JSON. Extracted text previewed at INFO level.

## Summary

All 29 new tests pass. Code correctly extracts text from result events with deduplication against streaming deltas. The dedup strategy favors content delivery over dedup (safe fallback). Full test suite (297 tests) passes. Manual testing with a live bot is recommended to verify end-to-end behavior with real tool-use scenarios.
