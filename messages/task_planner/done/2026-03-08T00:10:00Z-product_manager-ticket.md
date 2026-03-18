# Fix CancelledError in session _finish() when called from idle timer

## Metadata
- **From**: product_manager
- **To**: task_planner
- **Type**: ticket
- **Created**: 2026-03-08T00:10:00Z

## Requirements

1. In `session.py`, modify the `_finish()` method to skip cancelling the currently executing task, matching the guard pattern already used in `shutdown()`.
2. Before the task-cancellation loop (lines 187-189), get the current task via `asyncio.current_task()`.
3. Add a `task is not current` condition to the cancellation check, so the loop becomes: `if task and not task.done() and task is not current: task.cancel()`.
4. No other behavioral changes — the method must still cancel all *other* background tasks and invoke `_on_end` exactly as before.

## QA Steps

1. Trigger an idle timeout by leaving a session inactive past the configured timeout. Verify that the bot sends the "session timed out" message to the user without errors in the log.
2. Confirm no `CancelledError` or `on_end callback raised an exception` appears in the logs after an idle-timeout shutdown.
3. Manually call `shutdown(reason="user")` (e.g. via `/stop` command) and verify that background tasks are still properly cancelled and the session ends cleanly.
4. Start a session and let it produce stdout/stderr output, then trigger idle timeout — verify both the output tasks and the idle task are cleaned up without errors.

## Design Context

The `shutdown()` method already contains a `current_task` guard (lines 135-141) that prevents self-cancellation when the idle timer triggers shutdown. However, `_finish()` — called by `shutdown()` — cancels all background tasks unconditionally, re-introducing the self-cancellation the guard was meant to prevent. The pending `CancelledError` then fires during the `await self._on_end(...)` call, killing the Telegram API request mid-flight. The fix is a one-line addition mirroring the existing pattern. See forum topic `forum/open/2026-03-08T00:01:00Z-operator-session-end-cancelled-error.md` for full root cause analysis.
