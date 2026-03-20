# fix-idle-timer-reset-on-agent-stdout

## Metadata
- **From**: task_planner
- **To**: developer

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

### Technical Context

#### Relevant Files

- **`telegram_bot/session.py`** (primary, modify): Contains the `Session` class. This is the only file to modify.
  - **`_read_stdout()`** (line 367-409): The stdout reader coroutine. Insert the two new lines after line 383 (after the `if not raw: continue` guard, before the debug log on line 385).
  - **`send()`** (line 230-254): Reference implementation of the pattern — lines 253-254 show the exact two-line pattern to replicate: `self.last_activity = time.monotonic()` followed by `self._reset_idle_timer()`.
  - **`_reset_idle_timer()`** (line 462-466): Cancels the existing idle task and creates a new one. Already works correctly — just needs to be called from the new location.
  - **`_idle_timer()`** (line 445-460): The timer coroutine that sleeps for `_idle_timeout` seconds, then checks `last_activity`. Uses a re-check loop pattern: even if the sleep completes, it verifies elapsed time against `last_activity` before triggering shutdown. This means the fix is safe — updating `last_activity` is sufficient even if a timer sleep is already in progress.

#### Patterns and Conventions

- The codebase already uses the two-line pattern `self.last_activity = time.monotonic()` + `self._reset_idle_timer()` in `send()` (lines 253-254). Replicate this exact pattern.
- `time` is already imported at line 16 — no new imports needed.
- `time.monotonic()` is used consistently (not `time.time()`) for activity tracking.

#### Dependencies and Integration Points

- **`self.last_activity`**: A float attribute set to `time.monotonic()`. Read by `_idle_timer()` (line 450) to compute elapsed inactivity time.
- **`self._reset_idle_timer()`**: Cancels the current `_idle_task` and creates a new `asyncio.Task` running `_idle_timer()`. This is safe to call from any async context within the Session.
- **`_idle_timer()` re-check pattern** (line 450-451): After sleeping, the timer recalculates `elapsed = time.monotonic() - self.last_activity`. This means updating `last_activity` in `_read_stdout()` will be picked up even by an already-sleeping timer, providing double safety.
- **No cross-module impact**: The change is entirely internal to the `Session` class. No other files reference or depend on the modified method's behavior.

#### Implementation Notes

1. **Exact insertion point**: After line 383 (`continue` inside the `if not raw:` guard), before line 385 (the `logger.debug` call). Insert:
   ```python
   self.last_activity = time.monotonic()
   self._reset_idle_timer()
   ```
2. **Indentation**: Match the surrounding code — 16 spaces (4 levels of indentation: class > method > try > while).
3. **No blank line needed** between the two new lines, but add a blank line after them before the `logger.debug` call, matching the existing code style.
4. **Thread safety**: Not a concern — the session runs in a single asyncio event loop. The stdout reader and idle timer are both coroutines on the same loop.
5. **Performance**: `time.monotonic()` and `_reset_idle_timer()` are lightweight. Calling them per stdout line is negligible overhead.
6. **Testing approach**: The QA steps focus on behavioral verification. There are no unit tests to update — this is a runtime behavior fix.

### Design Context

This is a critical bug fix. The idle timer in `session.py` only resets on user input (`send()`, line 253-254), never on agent output. This causes the idle timer to kill active agents during long-running tasks (tool use, file operations, extended reasoning), resulting in permanent session unresponsiveness. The fix adds the same two-line `last_activity` + `_reset_idle_timer()` pattern to `_read_stdout()`. Full root cause analysis documented in `forum/closed/2026-03-19-operator-idle-timer-kills-active-agents.md`. All agents confirmed the analysis and fix scope in that discussion. Priority: high — this causes complete session death during normal agent operation.
