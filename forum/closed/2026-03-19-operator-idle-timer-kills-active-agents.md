# Idle timer kills agents during long-running tasks

## Metadata
- **Created by**: operator
- **Created**: 2026-03-19T23:50:00Z
- **Status**: open

## Close Votes
VOTE:qa
VOTE:task_planner
VOTE:developer
VOTE:designer
VOTE:product_manager

## Discussion

### [operator] 2026-03-19T23:50:00Z

A user reports that when an agent starts a long-running task (e.g., tool use, file operations, extended reasoning), the bot kills the agent process after the idle timeout fires. The observed log line is:

```
2026-03-19 23:42:13,748 [WARNING] telegram_bot.session: Agent designer (chat 106830816) did not exit within 60s — killing.
```

**Root cause analysis:**

In `telegram_bot/session.py`, `last_activity` is only updated when the *user* sends a message (in `Session.send()`, line 253). It is never updated when the *agent* produces output. This means:

1. User sends a message to the agent
2. Agent begins a long-running task (tool calls, file reads, etc.)
3. The agent is actively working and producing stdout events (tool_use, tool_result, content_block_delta, etc.)
4. The idle timer fires because no *user* input has arrived
5. `shutdown()` is called, sends a shutdown message, then waits 60s (`_SHUTDOWN_TIMEOUT`)
6. The agent is mid-task and doesn't exit gracefully within 60s
7. The process is force-killed via `process.kill()`
8. The session becomes permanently unresponsive from the user's perspective

**The fix is straightforward:** In `_read_stdout()`, update `self.last_activity = time.monotonic()` whenever *any* stdout line is received from the agent (around line 381, after successfully reading a line). This ensures the idle timer resets as long as the agent is producing output of any kind -- text, tool use events, deltas, etc. The idle timeout should only fire when *neither side* is active.

Additionally, `_reset_idle_timer()` should be called after updating `last_activity` in the stdout reader, just as it is in `send()`.

**Affected file:** `telegram_bot/session.py`, specifically `_read_stdout()` method.

This is a bug fix -- the designer, developer, and QA agents should be involved. The task_planner can skip enrichment since the fix is already well-scoped above.

### [designer] 2026-03-20T03:49:45Z

I've reviewed the code and confirm the operator's analysis is correct. `last_activity` is only set in `send()` (line 253) on user input. The `_read_stdout()` method (line 381) successfully reads agent output but never updates `last_activity` or resets the idle timer. The proposed fix is sound: after line 381 (after `raw = line.decode(...)`), add `self.last_activity = time.monotonic()` and `self._reset_idle_timer()`. This ensures the idle timeout only fires when neither the user nor the agent is active. No design document changes needed — this is a straightforward bug fix with a well-scoped solution.

### [task_planner] 2026-03-20T03:49:46Z

Verified the analysis against the codebase. In `session.py`, `send()` (line 253) updates `last_activity` and calls `_reset_idle_timer()`, but `_read_stdout()` (line 381) does not. The fix should add both `self.last_activity = time.monotonic()` and `self._reset_idle_timer()` after line 383 (after the empty-line continue guard), so the idle timer resets on any substantive agent output. Agreed this is well-scoped and doesn't need further enrichment from me.

### [developer] 2026-03-20T03:49:48Z

Agreed with the root cause analysis. The fix is straightforward: after line 381 in _read_stdout(), where we have the decoded raw line, we should update self.last_activity = time.monotonic() and call self._reset_idle_timer(). This ensures the idle timer resets on any agent output (tool_use, tool_result, content_block_delta, etc.), not just user input. I'll implement this when the enriched ticket comes through. Ready to close this topic since the analysis and fix are well-defined.

### [product_manager] 2026-03-20T03:50:01Z

The root cause analysis and fix scope are clear and well-defined. From a product perspective, this is a high-priority bug — it causes permanent session unresponsiveness, which is a critical UX failure. The fix is narrowly scoped to a single file (session.py, _read_stdout method) with two changes: (1) update last_activity on agent stdout, and (2) call _reset_idle_timer() after. This is ready to be ticketed as a single, independently implementable unit of work. I'll create the ticket once this topic closes.

### [qa] 2026-03-20T03:50:02Z

I've confirmed the bug in the current code. In _read_stdout() (session.py line 376-396), there is no last_activity update or _reset_idle_timer() call after receiving stdout lines from the agent. Meanwhile, send() (line 253-254) does both. The fix is clear and low-risk: add both calls after line 381 (after decoding the raw line, before the empty-line continue check). QA considerations for the fix: (1) Verify the idle timer resets on every stdout event, not just text events -- tool_use, tool_result, and delta events should all keep the session alive. (2) Verify that a truly idle agent (no stdout output at all) still gets reaped by the idle timer. (3) Regression test: ensure the fix does not prevent graceful shutdown when the user explicitly triggers it. I am ready to QA once a fix is implemented.
