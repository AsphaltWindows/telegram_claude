# QA Report: Fix Idle Timer Reset on Agent Output

## Metadata
- **Ticket**: fix-idle-timer-agent-output
- **Tested**: 2026-03-20T00:00:00Z
- **Result**: PASS (code review + unit tests; manual steps deferred)

## Steps

### Step 1: Long-running agent operation keeps session alive
- **Result**: DEFERRED (requires interactive manual testing)
- **Notes**: Cannot be verified in non-interactive mode. Requires starting a real session and triggering a long-running agent operation.

### Step 2: Idle session is still terminated by idle timer
- **Result**: DEFERRED (requires interactive manual testing)
- **Notes**: Cannot be verified in non-interactive mode. Requires leaving a real session idle past the timeout.

### Step 3: Agent activity spanning idle timeout keeps session alive
- **Result**: DEFERRED (requires interactive manual testing)
- **Notes**: Cannot be verified in non-interactive mode. Requires agent activity exceeding the idle timeout duration.

### Step 4: Code review — last_activity AND _reset_idle_timer() both called in _read_stdout()
- **Result**: PASS
- **Notes**: Verified in session.py lines 385-388. Both `self.last_activity = time.monotonic()` and `self._reset_idle_timer()` are called after the empty-line guard (`if not raw: continue`) and before event parsing/on_response callback. This matches the existing pattern in `send()` (lines 253-254). The placement ensures the timer is reset even if the callback raises.

## Unit Tests

All 6 tests pass:
- test_read_stdout_resets_last_activity — PASS
- test_read_stdout_calls_reset_idle_timer — PASS
- test_read_stdout_resets_on_non_text_events — PASS
- test_read_stdout_resets_before_on_response_callback — PASS
- test_read_stdout_resets_on_each_line — PASS
- test_empty_lines_do_not_reset_timer — PASS

## Summary

Code review (step 4) passes cleanly. The fix is minimal (2 lines), correctly placed, and follows the established pattern from send(). Unit test coverage is thorough, covering normal operation, non-text events, ordering guarantees, per-line reset, and empty-line exclusion.

Steps 1-3 require interactive manual testing with a live bot session. These are deferred for the next interactive QA session with the user.
