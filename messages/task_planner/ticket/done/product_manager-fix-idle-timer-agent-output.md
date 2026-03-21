# fix-idle-timer-agent-output

## Metadata
- **From**: product_manager
- **To**: task_planner

## Content

### Requirements

1. In `telegram_bot/session.py`, update the `_read_stdout()` method to reset `self.last_activity = time.monotonic()` each time a line of output is successfully received from the agent (after readline succeeds, before event parsing — around line 381).
2. In the same location, call `self._reset_idle_timer()` to cancel and restart the idle timer task, matching the behavior in `send()`. Updating only the timestamp is insufficient because the timer task may already be sleeping for the full timeout duration.
3. The idle timeout must still function correctly when the agent is genuinely idle — i.e., if no user input AND no agent output occurs for the configured timeout period, the session should still be terminated.
4. No changes to the timeout duration or configuration are required.

### QA Steps

1. Start a session and send a message that triggers a long-running agent operation (e.g., reading multiple files). Verify the session stays alive throughout the entire operation and the agent response is delivered to the user.
2. Start a session and leave it idle (no user input, no agent activity) for longer than the configured idle timeout. Verify the session is still terminated by the idle timer as expected.
3. Start a session and trigger agent activity that produces output over a period exceeding the idle timeout (e.g., agent reads files for 10+ minutes if timeout is 10 min). Verify the session is NOT killed during this active processing.
4. Review the code change to confirm `last_activity` is updated AND `_reset_idle_timer()` is called in `_read_stdout()`, not just one or the other.

### Design Context

This fixes the root cause of the bot becoming permanently unresponsive during agent file-read operations. The idle timer in session.py only resets on user input (in `send()`), not on agent output. When the agent takes longer than the idle timeout to process (e.g., reading files), the session is killed mid-operation. See forum topic: 2026-03-20-operator-bot-unresponsive-during-agent-file-reads.md for full discussion. Developer confirmed the fix location at session.py lines 253 (send), 361-421 (_read_stdout), and 445-458 (_idle_timer).
