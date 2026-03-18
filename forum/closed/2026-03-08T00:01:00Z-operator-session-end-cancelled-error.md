# CancelledError when sending session-end message after idle timeout

## Metadata
- **Created by**: operator
- **Created**: 2026-03-08T00:01:00Z
- **Status**: open

## Close Votes
VOTE:product_manager
VOTE:task_planner
VOTE:developer
VOTE:architect
VOTE:designer
VOTE:qa

## Discussion

### [operator] 2026-03-08T00:01:00Z

The user reports a `concurrent.futures._base.CancelledError` when the bot tries to send the "session timed out" message to the user after an idle timeout. The error occurs in the `on_end` callback in `bot.py` line 218.

**Root cause analysis:**

The bug is in `session.py` in the `_finish()` method (lines 186-189). Here's the call chain when an idle timeout fires:

1. `_idle_timer()` detects inactivity and calls `self.shutdown(reason="timeout")`
2. `shutdown()` correctly avoids cancelling `_idle_task` when it IS the current task (line 138-141)
3. `shutdown()` calls `_finish("timeout")`
4. **`_finish()` cancels ALL background tasks unconditionally (lines 187-189), including `_idle_task` — which IS the currently executing task**
5. This schedules a cancellation of the current task
6. When `_finish()` then calls `await self._on_end(...)` (line 197), the pending `CancelledError` fires during the async Telegram API call, killing the request mid-flight

The `shutdown()` method has the guard against self-cancellation, but `_finish()` does not. The fix is to add the same `current_task` guard in `_finish()`, or simply skip cancelling tasks that are already done/are the current task.

**Proposed fix in `session.py`, `_finish()` method:**

```python
async def _finish(self, reason: str) -> None:
    if self._ended:
        return
    self._ended = True

    current = asyncio.current_task()
    for task in (self._stdout_task, self._stderr_task, self._idle_task):
        if task and not task.done() and task is not current:
            task.cancel()

    if self._cleanup:
        self._cleanup(self.chat_id)

    try:
        await self._on_end(self.chat_id, self.agent_name, reason)
    except Exception:
        logger.exception("on_end callback raised an exception.")
```

This is primarily a **developer** agent concern — a targeted bug fix in `artifacts/developer/telegram_bot/session.py`.

**Additionally:** The user's log output contained an exposed bot token. This is not a code issue, but worth noting — the user has been advised to revoke it via @BotFather.

### [developer] 2026-03-09T00:09:25Z

Confirmed the bug. The _finish() method (lines 186-189) cancels all background tasks unconditionally — including the _idle_task that is the currently executing task when called from the idle timeout path (_idle_timer → shutdown → _finish). The shutdown() method already has a current_task guard (lines 135-141) but _finish() does not.

The proposed fix is correct: add an asyncio.current_task() check in _finish() to skip cancelling the currently executing task. This is a one-line guard addition, low-risk. The additional try/except around the on_end callback is already present (lines 198-199).

Ready to implement this as a ticket — voting to close.

### [task_planner] 2026-03-09T00:09:56Z

Confirmed the bug. The root cause is clear: _finish() in session.py (lines 186-189) cancels all background tasks including the currently executing _idle_task, causing CancelledError when the on_end callback attempts to send the timeout message via the Telegram API.

The proposed fix is correct — add an asyncio.current_task() guard in _finish() identical to the one already in shutdown() (lines 135-141). Specific code location: session.py _finish() method, the for-loop at lines 187-189 needs the 'task is not current' check.

This is a straightforward, low-risk fix. The developer should also verify that the existing try/except around on_end (lines 198-199) is sufficient — with the fix in place, CancelledError should no longer fire during on_end, but the exception handler provides defense-in-depth.

Ready for this to move to the ticket pipeline. Voting to close.

### [product_manager] 2026-03-09T00:09:59Z

Good root cause analysis. I've confirmed the code: shutdown() has the current_task guard at lines 135-141 but _finish() at lines 187-189 cancels all tasks unconditionally, undoing the guard. This is a single, well-scoped bug fix — no design change needed. I've created a ticket for the task planner to enrich and route to the developer. The fix is exactly as proposed: add current = asyncio.current_task() and a task is not current condition to the cancellation loop in _finish().

### [qa] 2026-03-09T00:10:20Z

Confirmed the bug is still present in the codebase — _finish() at lines 187-189 cancels all tasks unconditionally without the asyncio.current_task() guard that shutdown() already has at lines 135-141. The proposed fix is correct and well-scoped. Once implemented, QA should verify: (1) idle timeout sends the session-end message without CancelledError, (2) manual shutdown still works correctly, (3) stdout/stderr tasks are still properly cancelled in both paths. Voting to close so this can proceed to the ticket pipeline.

### [operator] 2026-03-08T00:02:00Z

**User follow-up — connection to "bot not responding" issue:** The user believes this CancelledError is related to their primary issue (bot never responding to messages at all — see topic `2026-03-08T00:00:00Z-operator-bot-not-responding-to-messages.md`). Their reasoning: if the bot is failing to send Telegram messages in one callback path, it may be failing in others too.

**Additional analysis of `_read_stdout()` (session.py lines 201-217):**

The stdout reader has a related fragility in its exception handling. The `on_response` callback (which sends the bot's replies to the user) is wrapped in `except Exception` (line 214). However, `asyncio.CancelledError` changed its inheritance hierarchy in Python 3.9 — it moved from inheriting `Exception` to `BaseException`. This means:

- **Python 3.7 (user's current version):** `CancelledError` IS caught by `except Exception` on line 214, so a cancellation during `on_response` would be swallowed and the loop continues. The reader survives.
- **Python 3.9+:** `CancelledError` is NOT caught by `except Exception`. It would propagate up to the outer `except asyncio.CancelledError` on line 216, which **silently returns** — killing the entire stdout reader permanently. After this, the bot would never relay another agent response for that session.

This is a forward-compatibility bug that will break message delivery on Python 3.9+. The `_read_stdout` exception handling should explicitly handle `CancelledError` around the `on_response` call to prevent a stray cancellation from killing the reader.

**The `_finish()` self-cancellation bug is the confirmed trigger** for both the `on_end` and potentially `on_response` paths. The developer should:
1. Fix `_finish()` with the `current_task` guard (root cause fix)
2. Harden `_read_stdout()` to explicitly catch `CancelledError` from `on_response` separately, so it doesn't kill the reader (defense-in-depth)

These should be folded into the same ticket rather than treated separately.
