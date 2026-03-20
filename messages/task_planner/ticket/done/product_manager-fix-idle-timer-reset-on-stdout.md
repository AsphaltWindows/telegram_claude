# fix-idle-timer-reset-on-stdout

## Metadata
- **From**: product_manager
- **To**: task_planner

## Content

### Requirements

1. In `telegram_bot/session.py`, method `_read_stdout()`, after line 383 (the `if not raw: continue` guard), add the following two lines:
   ```python
   self.last_activity = time.monotonic()
   self._reset_idle_timer()
   ```
2. The idle timer MUST reset whenever the agent process produces any non-empty stdout output (including tool_use events, tool_result events, text deltas, and any other event types).
3. The idle timer MUST still correctly reap truly idle agents — agents that produce no stdout output for the configured idle timeout period must still be terminated.
4. Graceful shutdown behavior MUST remain unaffected — the existing shutdown flow must not be altered by this change.
5. No other methods or files should need modification; this is a 2-line addition only.

### QA Steps

1. **Idle timer resets on stdout events**: Start an agent session and trigger a tool-use operation (e.g., file read). Verify that the idle timer resets each time the agent emits stdout output. The session should NOT be killed while the agent is actively producing output.
2. **All stdout event types reset the timer**: Verify that tool_use, tool_result, text deltas, and other stdout event types all cause the idle timer to reset. No event type should be missed.
3. **Truly idle agents still get reaped**: Start an agent session, then leave it idle (no user input, no agent output) for longer than the configured idle timeout. Verify that the session is correctly terminated after the timeout period.
4. **Graceful shutdown unaffected**: Trigger a graceful shutdown while an agent is active. Verify that the shutdown completes normally without hanging or errors.
5. **No regression in normal conversation flow**: Conduct a normal multi-turn conversation with tool use. Verify that responses are delivered correctly and sessions remain stable throughout.

### Design Context

This fix addresses a critical bug where the idle timer kills active agent sessions during tool use. The root cause: `_read_stdout()` processes agent output but never resets the idle timer, so long-running tool operations (file reads, etc.) cause the session to appear idle and get reaped. The fix was fully analyzed and agreed upon in `forum/closed/2026-03-19-operator-idle-timer-kills-active-agents.md`. This is high priority — the bug causes complete session death during normal agent operation.
