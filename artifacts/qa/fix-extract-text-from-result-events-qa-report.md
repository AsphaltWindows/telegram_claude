# QA Report: Fix Extract Text From Result Events

## Metadata
- **Ticket**: fix-extract-text-from-result-events
- **Tested**: 2026-03-21T00:00:00Z
- **Result**: PASS (automated only)

## Steps

### Step 1: Tool-use response delivery
- **Result**: PASS (code review + unit tests)
- **Notes**: Text now extracted ONLY from result events. assistant and content_block_delta moved to skip list. Integration tests updated to reflect this.

### Step 2: Multiple sequential tool calls
- **Result**: PASS (unit tests)
- **Notes**: Multi-tool chain tests verify all final text is delivered through result events.

### Step 3: Basic non-tool message
- **Result**: PASS (code review + unit tests)
- **Notes**: Result events still deliver text for simple responses. Dedup logic (now effectively a no-op since deltas no longer accumulate) is kept for safety.

### Step 4: No duplicate responses
- **Result**: PASS (code review)
- **Notes**: Since text only comes from result events (not streaming deltas), duplication is structurally impossible.

### Step 5: Typing indicator behavior
- **Result**: PASS (code review)
- **Notes**: Typing heartbeat is independent of text extraction changes.

### Step 6: Empty result after tool use
- **Result**: PASS (code review)
- **Notes**: `_extract_text_from_result` returns None for empty/missing text. `_read_stdout` handles None result text by resetting buffer without calling on_response.

### Step 7: INFO logs for filtered events
- **Result**: PASS (unit tests)
- **Notes**: 17 new tests in `test_event_logging.py` verify tool_use, tool_result, error at INFO; low-signal events at DEBUG; extracted text preview at INFO.

## Summary

All 17 new event logging tests pass. Updated tests in test_result_event.py and test_session_idle_timer.py also pass. This is the key architectural change: text extraction now comes solely from result events, eliminating the root cause of silent bot after tool use. Full suite (297 tests) passes.
