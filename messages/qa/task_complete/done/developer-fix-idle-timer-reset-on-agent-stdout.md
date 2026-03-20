# fix-idle-timer-reset-on-agent-stdout

## Metadata
- **From**: developer
- **To**: qa

## Content

## Summary of Changes

Implemented the idle timer reset fix in `_read_stdout()` to prevent active agent sessions from being killed during long-running tasks (tool use, file reads, extended reasoning).

## Files Changed

- **`telegram_bot/session.py`** — Added two lines in `_read_stdout()` after line 383 (after the `if not raw: continue` guard): `self.last_activity = time.monotonic()` and `self._reset_idle_timer()`. This ensures the idle timer resets on every non-empty stdout line from the agent process.

## Requirements Addressed

1. **last_activity update on stdout**: Added `self.last_activity = time.monotonic()` at line 385 — updates activity timestamp for every non-empty stdout line. DONE.
2. **Idle timer reset on stdout**: Added `self._reset_idle_timer()` at line 386 — resets the idle timer, matching the pattern in `send()` (lines 253-254). DONE.
3. **All stdout event types covered**: The two lines execute for every non-empty stdout line, covering `tool_use`, `tool_result`, `content_block_delta`, text, and all other event types. DONE.
4. **No other behavioral changes**: Only added two lines in one location. Graceful shutdown, explicit shutdown, and idle reaping of truly inactive agents are unaffected. DONE.

## QA Steps

1. **Idle timer resets on agent stdout**: Start a session, send a message that triggers a long-running agent task (e.g., multiple tool calls, file reads). Verify the session remains alive throughout the task and the agent responds successfully. Confirm last_activity is being updated by observing that the idle timer does not fire while the agent is producing output.
2. **All stdout event types keep session alive**: Verify that tool_use, tool_result, content_block_delta, and plain text events all reset the idle timer. The session should not be killed during any type of agent output.
3. **Truly idle agents still get reaped**: Start a session, then arrange for the agent to produce no stdout output for longer than the idle timeout. Verify the idle timer fires and the agent is shut down gracefully.
4. **Graceful shutdown still works**: Trigger an explicit shutdown (e.g., user-initiated). Verify the agent exits cleanly within the shutdown timeout and is not force-killed unnecessarily.
5. **No regression on user-input activity tracking**: Verify that send() still updates last_activity and resets the idle timer on user input, unchanged by this fix.

## Test Coverage

This is a runtime behavior fix — no unit test files exist in the codebase for this module. QA verification is behavioral per the QA steps above.

## Notes

- The fix exactly replicates the two-line pattern from `send()` (lines 253-254), maintaining codebase consistency.
- The `_idle_timer()` re-check pattern (line 450-451) provides double safety: even if a timer sleep is already in progress, updating `last_activity` will be picked up when the sleep completes.
- No new imports needed — `time` is already imported at line 16.
- No thread safety concerns — all coroutines run on the same asyncio event loop.
