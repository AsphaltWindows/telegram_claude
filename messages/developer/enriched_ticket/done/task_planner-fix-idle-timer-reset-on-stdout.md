# fix-idle-timer-reset-on-stdout

## Metadata
- **From**: task_planner
- **To**: developer

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

### Technical Context

#### Relevant Files

- **`telegram_bot/session.py`** (MODIFY) — The only file to modify. Contains the `Session` class with the `_read_stdout()` method (line 376), `_idle_timer()` (line 448), `_reset_idle_timer()` (line 465), and `last_activity` tracking (initialized at line 178).

#### Patterns and Conventions

- The idle timer reset pattern is already established in the codebase: `send()` method (line 253-254) does exactly `self.last_activity = time.monotonic()` followed by `self._reset_idle_timer()` after writing user input. The fix mirrors this exact same 2-line pattern in `_read_stdout()`.
- `_reset_idle_timer()` (line 465-469) cancels the existing `_idle_task` and creates a new `asyncio.create_task(self._idle_timer())`. This is safe to call repeatedly.
- `_idle_timer()` (line 448-463) sleeps for `_idle_timeout` seconds, then double-checks `elapsed >= _idle_timeout` before shutting down. This double-check means even if timer reset races with the sleep, the shutdown only fires on genuinely idle sessions.

#### Dependencies and Integration Points

- `time.monotonic()` — already imported and used elsewhere in the file.
- `self._reset_idle_timer()` — already defined and used in `send()`. No new dependencies needed.
- The `_idle_timer` → `shutdown()` flow (line 460) is the downstream consumer of `last_activity`. No changes needed there.

#### Implementation Notes

- **IMPORTANT: The fix already exists as an uncommitted change in the working tree.** Running `git diff -- telegram_bot/session.py` shows the exact 2-line addition at lines 385-386 is already applied. The developer should verify this change is correct, ensure no other modifications are present, and commit it.
- The insertion point is line 384 (after the `if not raw: continue` guard at line 382-383), before the `logger.debug()` call at line 388. This ensures the timer resets for ALL non-empty stdout lines, not just those containing extractable text.
- The fix must go BEFORE `_extract_text_from_event(raw)` (line 394) — tool_use and tool_result events may not yield user-visible text, but they still represent agent activity that should reset the idle timer.
- No changes to `_idle_timer()`, `_reset_idle_timer()`, or `shutdown()` are needed.

### Design Context

This fix addresses a critical bug where the idle timer kills active agent sessions during tool use. The root cause: `_read_stdout()` processes agent output but never resets the idle timer, so long-running tool operations (file reads, etc.) cause the session to appear idle and get reaped. The fix was fully analyzed and agreed upon in `forum/closed/2026-03-19-operator-idle-timer-kills-active-agents.md`. This is high priority — the bug causes complete session death during normal agent operation.
