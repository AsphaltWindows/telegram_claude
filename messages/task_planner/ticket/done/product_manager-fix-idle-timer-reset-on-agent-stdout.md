# fix-idle-timer-reset-on-agent-stdout

## Metadata
- **From**: product_manager
- **To**: task_planner

## Content

### Requirements

1. In `telegram_bot/session.py`, method `_read_stdout()`, add `self.last_activity = time.monotonic()` after line 383 (after the `if not raw: continue` guard), so that `last_activity` is updated whenever the agent produces any stdout output.
2. Immediately after the `last_activity` update added in requirement 1, add `self._reset_idle_timer()` to reset the idle timer, matching the pattern already used in `Session.send()` (line 253-254).
3. The two new lines must execute for every non-empty stdout line from the agent process, covering all event types: `tool_use`, `tool_result`, `content_block_delta`, text output, and any other stdout events.
4. No other behavioral changes — graceful shutdown, explicit user-triggered shutdown, and idle reaping of truly inactive agents must continue to work as before.

### QA Steps

1. **Idle timer resets on agent stdout**: Start a session, send a message that triggers a long-running agent task (e.g., multiple tool calls, file reads). Verify the session remains alive throughout the task and the agent responds successfully. Confirm `last_activity` is being updated by observing that the idle timer does not fire while the agent is producing output.
2. **All stdout event types keep session alive**: Verify that `tool_use`, `tool_result`, `content_block_delta`, and plain text events all reset the idle timer. The session should not be killed during any type of agent output.
3. **Truly idle agents still get reaped**: Start a session, then arrange for the agent to produce no stdout output for longer than the idle timeout. Verify the idle timer fires and the agent is shut down gracefully.
4. **Graceful shutdown still works**: Trigger an explicit shutdown (e.g., user-initiated). Verify the agent exits cleanly within the shutdown timeout and is not force-killed unnecessarily.
5. **No regression on user-input activity tracking**: Verify that `send()` still updates `last_activity` and resets the idle timer on user input, unchanged by this fix.

### Design Context

This is a critical bug fix. The idle timer in `session.py` only resets on user input (`send()`, line 253-254), never on agent output. This causes the idle timer to kill active agents during long-running tasks (tool use, file operations, extended reasoning), resulting in permanent session unresponsiveness. The fix adds the same two-line `last_activity` + `_reset_idle_timer()` pattern to `_read_stdout()`. Full root cause analysis documented in `forum/closed/2026-03-19-operator-idle-timer-kills-active-agents.md`. All agents confirmed the analysis and fix scope in that discussion. Priority: high — this causes complete session death during normal agent operation.
