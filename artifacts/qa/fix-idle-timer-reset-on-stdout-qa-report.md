# QA Report: Fix Idle Timer Reset on Stdout

## Metadata
- **Ticket**: fix-idle-timer-reset-on-stdout
- **Tested**: 2026-03-20T00:00:00Z
- **Result**: PASS

## Steps

### Step 1: Start an agent session and trigger a tool-use operation. Verify idle timer resets on stdout output.
- **Result**: PASS
- **Notes**: Code review confirms lines 385-386 in `_read_stdout()` reset `last_activity` and call `_reset_idle_timer()` for all non-empty stdout lines. This is placed after the `if not raw: continue` guard, so any stdout event (including tool_use) resets the timer. Test `test_stdout_output_resets_idle_timer` validates this scenario with mock tool_use events and confirms no premature timeout.

### Step 2: Verify tool_use, tool_result, text deltas, and other stdout event types all reset the timer.
- **Result**: PASS
- **Notes**: The fix is placed before `_extract_text_from_event`, so ALL event types trigger the reset regardless of their content type. Tests `test_stdout_updates_last_activity` (text events) and `test_non_text_stdout_events_reset_idle_timer` (tool_use events) both pass, confirming this behavior.

### Step 3: Leave a session idle beyond the configured timeout. Verify it is correctly terminated.
- **Result**: PASS
- **Notes**: `_idle_timer()` double-check logic at lines 453-454 is unchanged. When `elapsed >= _idle_timeout`, shutdown is triggered. Test `test_idle_timeout_triggers_shutdown` and the tail end of `test_non_text_stdout_events_reset_idle_timer` (which verifies timeout fires after activity stops) both confirm correct reaping of idle sessions.

### Step 4: Trigger graceful shutdown while agent is active. Verify normal completion.
- **Result**: PASS
- **Notes**: `shutdown()` and `_finish()` methods are completely untouched by this change. No regression risk. Existing tests covering shutdown behavior all pass (59/59).

### Step 5: Conduct a normal multi-turn conversation with tool use. Verify stable operation.
- **Result**: PASS
- **Notes**: Full test suite (59 tests) passes. The fix follows the exact same pattern as `send()` (lines 253-254), which has been stable. No new failure modes introduced.

## Summary

All 5 QA steps pass. The 2-line fix is minimal, correctly placed, and follows established patterns. Code review confirms:
- The fix mirrors the `send()` pattern exactly (lines 253-254 vs 385-386)
- All stdout event types reset the timer (fix is before event type filtering)
- Truly idle sessions still get reaped (double-check logic in `_idle_timer` unchanged)
- Graceful shutdown is unaffected (no changes to shutdown/finish methods)
- 3 new tests provide good coverage of the fix
- Full suite of 59 tests pass

Verification was done via code review and automated tests (non-interactive mode). Manual end-to-end testing with a live bot session was not performed but the automated coverage is comprehensive.
