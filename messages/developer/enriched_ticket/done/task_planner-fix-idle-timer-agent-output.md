# fix-idle-timer-agent-output

## Metadata
- **From**: task_planner
- **To**: developer

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

### Technical Context

#### Relevant Files

- **`telegram_bot/session.py`** (PRIMARY — modify): Contains the `Session` class with the bug. Key locations:
  - Line 178: `self.last_activity: float = time.monotonic()` — initialized in `__init__`
  - Lines 227-254: `send()` method — the model to follow. Lines 253-254 show the pattern: `self.last_activity = time.monotonic()` followed by `self._reset_idle_timer()`
  - Lines 361-421: `_read_stdout()` method — WHERE THE FIX GOES. After line 383 (`if not raw: continue`), add the two lines to update `last_activity` and reset the idle timer. This should happen for every non-empty stdout line, not just lines that produce text for `on_response`.
  - Lines 445-460: `_idle_timer()` method — sleeps for `_idle_timeout`, then checks `elapsed = time.monotonic() - self.last_activity`. No changes needed here.
  - Lines 462-466: `_reset_idle_timer()` method — cancels and restarts `_idle_task`. No changes needed here.
- **`artifacts/developer/telegram_bot/session.py`** (modify): Developer workspace copy — apply the same change here.
- **`artifacts/developer/telegram_bot/tests/test_bot.py`** (reference): Existing test patterns — uses `pytest`, `mock.AsyncMock`, `mock.MagicMock`, `mock.patch`. Follow these patterns for any new tests.

#### Patterns and Conventions

- The codebase uses `time.monotonic()` (not `time.time()`) for all timing — follow this convention.
- The idle timer reset pattern is: (1) update `self.last_activity = time.monotonic()`, then (2) call `self._reset_idle_timer()`. Both steps are required. See `send()` lines 253-254 for the reference pattern.
- `_reset_idle_timer()` cancels the existing `_idle_task` and creates a new one via `asyncio.create_task(self._idle_timer())`. This ensures the timer starts fresh from the current moment.
- Logging follows stdlib `logging` with module-level `logger = logging.getLogger(__name__)`. Use `logger.debug()` for the activity reset if logging is desired.
- Tests use `mock` (not `unittest.mock`) — see imports in `test_bot.py`.

#### Dependencies and Integration Points

- **`_idle_timer()` (session.py lines 445-460)**: Reads `self.last_activity` to decide whether to fire. The fix ensures this timestamp stays current during agent output, preventing premature timeout.
- **`_reset_idle_timer()` (session.py lines 462-466)**: Already exists, well-tested by the `send()` path. Reuse it as-is.
- **`on_response` callback (bot.py lines 345-379)**: Called from `_read_stdout()` after text extraction. The activity reset should happen BEFORE the callback to ensure timing is updated even if the callback raises.
- **No config changes needed**: `_idle_timeout` value is unchanged.

#### Implementation Notes

1. **The fix is 2 lines of code** in `_read_stdout()`. After line 383 (`if not raw: continue`), insert:
   ```python
   self.last_activity = time.monotonic()
   self._reset_idle_timer()
   ```
2. **Reset on ALL non-empty lines, not just text events**: Even non-text events (tool_use, system, etc.) indicate the agent is alive and working. Resetting on all output prevents timeout during file-heavy operations where the agent produces many non-text events before the final text response.
3. **Place the reset BEFORE the `_on_response` callback call** (before line 392): If the callback raises an exception (which is caught on line 395-396), the activity timestamp should still have been updated.
4. **Test approach**: Create a test that verifies `last_activity` is updated and `_reset_idle_timer` is called when `_read_stdout` processes a line. Mock the process stdout to return a line, then check `last_activity` changed and `_reset_idle_timer` was invoked.
5. **No risk of infinite timer reset loops**: `_reset_idle_timer()` just cancels and restarts the sleep — there is no recursive callback, so this is safe to call from `_read_stdout()`.

### Design Context

This fixes the root cause of the bot becoming permanently unresponsive during agent file-read operations. The idle timer in session.py only resets on user input (in `send()`), not on agent output. When the agent takes longer than the idle timeout to process (e.g., reading files), the session is killed mid-operation. See forum topic: 2026-03-20-operator-bot-unresponsive-during-agent-file-reads.md for full discussion. Developer confirmed the fix location at session.py lines 253 (send), 361-421 (_read_stdout), and 445-458 (_idle_timer).
