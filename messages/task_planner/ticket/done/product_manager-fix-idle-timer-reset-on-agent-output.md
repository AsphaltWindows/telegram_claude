# fix-idle-timer-reset-on-agent-output

## Metadata
- **From**: product_manager
- **To**: task_planner

## Content

### Requirements

1. In `session.py`, the `_read_stdout()` method must update the `last_activity` timestamp each time it successfully receives and parses a line of output from the agent process.
2. The idle timeout check task must consider both user input AND agent output when determining inactivity — a session is only idle when neither the user nor the agent has produced activity for 10 minutes.
3. The `last_activity` field (or equivalent) must be a single shared timestamp that is updated by both `send()` (user input) and `_read_stdout()` (agent output).
4. No change to the timeout duration (remains 10 minutes) or the graceful shutdown path.

### QA Steps

1. Start a session and send a message that triggers a long-running agent operation (e.g., reading multiple files). Verify the session remains alive throughout the operation and does not timeout while the agent is actively producing output.
2. Start a session, send one message, then wait without sending further messages. Verify that once the agent finishes responding and 10 minutes pass with no user input AND no agent output, the session times out normally.
3. Inspect the `_read_stdout()` code path and confirm `last_activity` is updated on each successfully parsed stdout line.
4. Check logs to verify the idle timer correctly reflects the most recent activity timestamp from either source.

### Design Context

The idle timer previously only reset on user input, causing sessions to be killed during legitimate long-running agent work (file reads, multi-step tool use). This fix ensures agent output also counts as activity. See `artifacts/designer/design.md`, section 'Idle Timeout Implementation'.
