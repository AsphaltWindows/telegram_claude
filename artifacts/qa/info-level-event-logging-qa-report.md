# QA Report: INFO-Level Event Logging

## Metadata
- **Ticket**: info-level-event-logging
- **Tested**: 2026-03-21T00:00:00Z
- **Result**: PASS (automated only)

## Steps

### Step 1: INFO logs for tool_use and tool_result
- **Result**: PASS (unit tests)
- **Notes**: Tests verify tool_use logged at INFO with tool name, tool_result logged at INFO. Already implemented in fix-extract-text-from-result-events ticket.

### Step 2: INFO log for extracted text preview
- **Result**: PASS (unit tests)
- **Notes**: Result events with text logged at INFO with 80-char preview. Result events without text logged at DEBUG.

### Step 3: on_response success logging
- **Result**: PASS (code review + unit tests)
- **Notes**: `bot.py` on_response logs `"Message sent to chat %d (%d chars)"` at INFO after successful send. 2 new tests verify logging on success and absence on failure.

### Step 4: Low-signal events at DEBUG only
- **Result**: PASS (unit tests)
- **Notes**: assistant, content_block_delta, ping, system, etc. all verified to log at DEBUG only.

### Step 5: LOG_LEVEL=DEBUG shows all events
- **Result**: PASS (code review)
- **Notes**: Standard Python logging hierarchy ensures DEBUG level shows all events including INFO.

### Step 6: No duplicate log lines
- **Result**: PASS (code review)
- **Notes**: Each event type has a single log call in the extraction function.

## Summary

All 19 tests in test_event_logging.py pass. The on_response success log in bot.py is correctly placed after successful send_long_message. Most session.py logging was done as part of the related fix ticket.
