# QA Report: Fix subprocess invocation and output parsing for non-interactive claude CLI usage

## Metadata
- **Ticket**: Fix subprocess invocation and output parsing for non-interactive claude CLI usage
- **Tested**: 2026-03-09T00:45:00Z
- **Result**: PASS (code review + unit tests; manual integration tests pending)

## Steps

### Step 1: Code Review — Subprocess invocation flags
- **Result**: PASS
- **Notes**: `SessionManager.start_session()` (lines 484-497) correctly invokes `claude --agent <name> --print --output-format stream-json --input-format stream-json` with PIPE for stdin/stdout/stderr. Test `test_start_session_spawns_process_with_stream_json_flags` verifies this.

### Step 2: Code Review — Stream-json output parsing
- **Result**: PASS
- **Notes**: `_extract_text_from_event()` (lines 29-103) handles assistant messages, content_block_delta (text_delta), and result events. Non-text events (system, tool_use, tool_result, message_start, message_stop, etc.) are correctly skipped. Non-JSON lines are passed through as fallback. 14 unit tests cover these cases thoroughly.

### Step 3: Code Review — Stream-json input formatting
- **Result**: PASS
- **Notes**: `Session.send()` (lines 222-224) formats user messages as `{"type": "user", "content": text}` JSON + newline. `Session.shutdown()` (lines 260-263) formats the shutdown message the same way. Tests verify JSON format on stdin.

### Step 4: Code Review — Diagnostic logging
- **Result**: PASS
- **Notes**: `_read_stdout()` logs at INFO when starting (lines 327-331) and ending (lines 362-366), at DEBUG for each line received (lines 342-346). Test `test_stdout_reader_logs_lifecycle` verifies the start/end log messages.

### Step 5: Unit test suite
- **Result**: PASS
- **Notes**: All 47 tests pass. Coverage includes event parsing (20 tests), session reading (6 tests), sending (3 tests), shutdown (5 tests), idle timeout (4 tests), crash detection (2 tests), and SessionManager (7 tests).

### Step 6: Permission-mode flag
- **Result**: PASS (with caveat)
- **Notes**: The `--permission-mode` flag was intentionally not added per the ticket's conditional requirement. This is acceptable but should be monitored during manual testing — if the subprocess hangs on permission prompts in headless mode, a follow-up ticket should add this flag.

### Step 7: Manual integration tests (PENDING)
- **Result**: PENDING — requires user to execute
- **Notes**: The following manual QA steps from the ticket require running the bot against a real Telegram instance and cannot be verified by code review alone:
  1. Manual CLI test: `echo "hello" | claude --agent operator -p --output-format stream-json --input-format stream-json 2>/dev/null`
  2. Basic relay test: Start session, send message, verify response in Telegram
  3. Multi-turn test: Send 3+ messages, verify context maintained
  4. Empty start test: Start session without message, send follow-up
  5. Long response test: Verify multi-message relay via send_long_message
  6. Graceful shutdown test: `/end` should clean up properly
  7. No hanging: Verify no indefinite blocking

## Summary

**Code review and unit tests PASS.** The implementation correctly addresses the P0 bug where agent responses never reached the user. The root cause (bare `claude --agent <name>` launching in TUI mode) is fixed by adding `--print --output-format stream-json --input-format stream-json` flags. The stream-json parser is well-structured and handles edge cases (non-JSON fallback, malformed JSON, unknown event types). Test coverage is comprehensive at 47 tests.

**Manual integration testing is required** to fully validate the fix end-to-end. The user should run the 7 manual QA steps listed above before considering this P0 fully resolved. The `--permission-mode` flag omission should be watched for — if the agent hangs on permission prompts, a follow-up fix is needed.

This resolves the issue described in forum topic `2026-03-08T00:03:00Z-operator-no-agent-responses-after-session-start.md`.
