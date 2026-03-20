# QA Report: Fix Idle Timer Reset on Agent Stdout

## Metadata
- **Ticket**: fix-idle-timer-reset-on-agent-stdout
- **Tested**: 2026-03-20T00:00:00Z
- **Result**: PASS (code review only — behavioral testing requires interactive session)

## Steps

### Step 1: Idle timer resets on agent stdout (Code Review)
- **Result**: PASS
- **Notes**: Lines 385-386 in `_read_stdout()` add `self.last_activity = time.monotonic()` and `self._reset_idle_timer()` after the `if not raw: continue` guard (line 382-383). This ensures every non-empty stdout line resets the idle timer. The pattern exactly matches `send()` at lines 253-254. Behavioral verification (long-running agent task surviving idle timeout) requires interactive testing.

### Step 2: All stdout event types keep session alive (Code Review)
- **Result**: PASS
- **Notes**: The two new lines execute for every non-empty stdout line regardless of event type — there is no type filtering before them. tool_use, tool_result, content_block_delta, and plain text events all flow through the same code path and will reset the timer.

### Step 3: Truly idle agents still get reaped (Code Review)
- **Result**: PASS
- **Notes**: `_idle_timer()` (lines 448-459) uses a while-True loop that sleeps for `_idle_timeout` seconds, then re-checks `time.monotonic() - self.last_activity >= _idle_timeout`. If no stdout has been produced and no user input sent, `last_activity` won't be updated, and the timer will fire correctly. The `_reset_idle_timer()` call only happens on non-empty stdout lines, so truly silent agents are unaffected.

### Step 4: Graceful shutdown still works (Code Review)
- **Result**: PASS
- **Notes**: The `shutdown()` method (line 256+) is completely untouched by this change. The fix only adds lines inside `_read_stdout()`. No behavioral change to explicit shutdown paths.

### Step 5: No regression on user-input activity tracking (Code Review)
- **Result**: PASS
- **Notes**: `send()` at lines 253-254 still contains its original `self.last_activity = time.monotonic()` and `self._reset_idle_timer()` calls, unchanged by this fix. The new lines in `_read_stdout()` are additive.

## Summary

Code review confirms the implementation is correct, minimal, and consistent with existing patterns. The fix adds exactly two lines in `_read_stdout()` that mirror the existing two-line pattern in `send()`. No other code was modified. Thread safety is not a concern since all coroutines run on the same asyncio event loop.

Behavioral testing (actually running the bot and verifying sessions survive long agent tasks) requires an interactive QA session. The code-level analysis shows no issues.
