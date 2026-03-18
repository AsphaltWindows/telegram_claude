# Fix CancelledError in session _finish() when called from idle timer

## Metadata
- **From**: task_planner
- **To**: developer
- **Type**: enriched-ticket
- **Created**: 2026-03-09T00:15:00Z

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

## Technical Context

### Relevant Files
- **`artifacts/developer/telegram_bot/session.py`** — The sole file to modify. Contains the `Session` class with the buggy `_finish()` method (line 180) and the reference `shutdown()` method (line 114) that already has the correct guard pattern.

### Patterns and Conventions
- **Current task guard pattern**: The codebase already uses `asyncio.current_task()` to avoid self-cancellation. See `shutdown()` at line 135:
  ```python
  current_task = asyncio.current_task() if hasattr(asyncio, 'current_task') else asyncio.Task.current_task()
  ```
  The `hasattr` check is a compatibility guard for Python 3.6 (where `current_task` was on `Task`). Follow this exact same pattern in `_finish()` for consistency.
- **Idempotency via `_ended` flag**: `_finish()` is guarded by `self._ended` (line 182-183) to ensure it runs exactly once. This is already in place — no changes needed here.
- **Logging**: The module uses `logger = logging.getLogger(__name__)` at module level (line 15). Existing log calls use `logger.info`, `logger.warning`, `logger.debug`, and `logger.exception`.
- **Docstrings**: Methods use Google/NumPy-style docstrings. The `_finish()` docstring is minimal ("Invoke end callback and clean up, exactly once.") — no update needed.

### Dependencies and Integration Points
- **Call chain for the bug**: `_idle_timer()` (line 247) → `shutdown(reason="timeout")` (line 259) → `_finish("timeout")` (line 158). When `_finish()` is called from this path, `asyncio.current_task()` returns the `_idle_task`. The unconditional `task.cancel()` at line 189 schedules a `CancelledError` on the currently running task, which fires during `await self._on_end(...)` at line 197.
- **`_on_end` callback**: Defined in `bot.py` (line 218 per the forum topic). This is the async Telegram API call that sends the "session ended" message to the user. The `CancelledError` kills this call mid-flight.
- **Other callers of `_finish()`**: `_read_stdout()` calls `_finish("crash")` at line 229 when the agent exits unexpectedly. In this path, `current_task()` returns `_stdout_task`, so the fix also correctly prevents self-cancellation of the stdout reader — though this is less critical since `_read_stdout` calls `_finish` at the end of its execution.
- **`shutdown()` also calls `_finish()`**: At line 158. In this path, the current task is whatever called `shutdown()` (e.g., a handler task from the Telegram framework), not one of the background tasks, so the guard has no effect — all three background tasks are correctly cancelled. This is the expected behavior.

### Implementation Notes
1. **Exact change location**: Lines 186-189 of `session.py`. Insert one line before line 187 and modify the condition on line 188.
2. **Before (lines 186-189)**:
   ```python
   # Cancel remaining background tasks.
   for task in (self._stdout_task, self._stderr_task, self._idle_task):
       if task and not task.done():
           task.cancel()
   ```
3. **After**:
   ```python
   # Cancel remaining background tasks.
   current = asyncio.current_task() if hasattr(asyncio, 'current_task') else asyncio.Task.current_task()
   for task in (self._stdout_task, self._stderr_task, self._idle_task):
       if task and not task.done() and task is not current:
           task.cancel()
   ```
4. **No imports needed**: `asyncio` is already imported at line 9.
5. **Risk assessment**: Very low. The change only adds a skip condition — all other tasks are still cancelled. The only behavioral change is that the currently executing task no longer receives a spurious `CancelledError`.

## Design Context

The `shutdown()` method already contains a `current_task` guard (lines 135-141) that prevents self-cancellation when the idle timer triggers shutdown. However, `_finish()` — called by `shutdown()` — cancels all background tasks unconditionally, re-introducing the self-cancellation the guard was meant to prevent. The pending `CancelledError` then fires during the `await self._on_end(...)` call, killing the Telegram API request mid-flight. The fix is a one-line addition mirroring the existing pattern. See forum topic `forum/open/2026-03-08T00:01:00Z-operator-session-end-cancelled-error.md` for full root cause analysis.
