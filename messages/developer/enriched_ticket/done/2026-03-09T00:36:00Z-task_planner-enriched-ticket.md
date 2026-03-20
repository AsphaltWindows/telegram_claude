# Add diagnostic logging to stdout reader

## Metadata
- **From**: task_planner
- **To**: developer
- **Type**: enriched-ticket
- **Created**: 2026-03-09T00:36:00Z

## Requirements

1. In `_read_stdout()` (session.py, lines ~203-231), add an INFO-level log line when the reader starts, including the agent name and chat ID. Example: `"stdout reader started for agent %s (chat %d)"`.

2. In the read loop within `_read_stdout()`, add a DEBUG-level log line for each line/event received, logging the first 100 characters of the raw content. Example: `"stdout line from %s: %s"`.

3. After the read loop exits in `_read_stdout()`, add an INFO-level log line indicating the reader has ended, including the reason (EOF, cancellation, error). Example: `"stdout reader ended for agent %s (chat %d): %s"`.

4. Use the existing `logger` instance in session.py. Do not create a new logger.

## QA Steps

1. **Start a session** and check server logs for the INFO-level "stdout reader started" message containing the agent name and chat ID.

2. **Send a message** in the session and check server logs for DEBUG-level lines showing received stdout content (first 100 chars).

3. **End the session** with `/end` and check server logs for the INFO-level "stdout reader ended" message with the reason (should indicate EOF or normal termination).

4. **Simulate an error** (e.g., kill the claude subprocess externally) and confirm the "stdout reader ended" log includes the error reason.

5. Confirm no sensitive content is leaked in log lines — only first 100 characters of each line, which should be safe.

## Technical Context

### Relevant Files

| File | Path | Why |
|------|------|-----|
| **session.py** | `artifacts/developer/telegram_bot/session.py` | **Only file to modify.** The `_read_stdout()` method (lines 203-231) is where all three log lines must be added. |
| **test_session.py** | `artifacts/developer/tests/test_session.py` | Should add tests verifying the new log lines appear. The existing `test_stderr_logged_at_warning_level` test (lines 170-190) demonstrates the pattern for testing log output — it patches `telegram_bot.session.logger` and asserts on `mock_logger.warning` / `mock_logger.debug` calls. |

### Patterns and Conventions

- **Logger**: `logger = logging.getLogger(__name__)` at line 15 of session.py. Already used throughout the module.
- **Existing logging pattern**: `_read_stderr()` (lines 233-247) uses `logger.warning("Agent %s stderr: %s", self.agent_name, text)` — follow this style for format strings.
- **Log levels in the module**: `logger.info()` for lifecycle events (session start at line 360, idle timeout at line 256), `logger.warning()` for unexpected conditions (stderr at line 243, unexpected exit at line 225, force-kill at line 171), `logger.debug()` for verbose/pipe-broken at line 151.
- **Testing log output**: Patch `telegram_bot.session.logger` (see test at line 179), then assert on `mock_logger.info.assert_any_call(...)` etc.

### Dependencies and Integration Points

- No external dependencies. This is a logging-only change.
- If the P0 subprocess invocation fix (the other ticket) changes `_read_stdout()` to parse JSON, the debug log line should log the raw line content *before* JSON parsing, so it captures the actual data received from the subprocess regardless of parse success.

### Implementation Notes

1. **Placement of "started" log**: Add immediately after the `assert self.process.stdout is not None` on line 205, before the `while True` loop:
   ```python
   logger.info("stdout reader started for agent %s (chat %d)", self.agent_name, self.chat_id)
   ```

2. **Placement of "line received" log**: Add inside the loop after receiving and decoding a line, before the `if text:` check. Log the raw decoded text truncated to 100 chars:
   ```python
   logger.debug("stdout line from %s: %.100s", self.agent_name, text)
   ```
   Note: Use `%.100s` format specifier or `text[:100]` to truncate.

3. **Placement of "ended" log**: There are multiple exit paths from `_read_stdout()`:
   - **EOF** (line 211: `if not line: break`): After the loop ends normally, log with reason "EOF".
   - **CancelledError** (line 218): In the `except asyncio.CancelledError` block, log with reason "cancelled" before the `return`.

   Suggested structure:
   ```python
   async def _read_stdout(self) -> None:
       assert self.process.stdout is not None
       logger.info("stdout reader started for agent %s (chat %d)", self.agent_name, self.chat_id)
       end_reason = "EOF"
       try:
           while True:
               line = await self.process.stdout.readline()
               if not line:
                   break
               text = line.decode(errors="replace").rstrip("\n")
               logger.debug("stdout line from %s: %.100s", self.agent_name, text)
               if text:
                   try:
                       await self._on_response(self.chat_id, text)
                   except Exception:
                       logger.exception("on_response callback raised.")
       except asyncio.CancelledError:
           end_reason = "cancelled"
           return
       finally:
           logger.info("stdout reader ended for agent %s (chat %d): %s", self.agent_name, self.chat_id, end_reason)

       # ... rest of method (process wait, crash detection)
   ```

   **Important**: Using `try/finally` ensures the "ended" log fires on both EOF and cancellation. However, note that the code after the loop (lines 222-231 — process wait and crash detection) must still execute on the EOF path. So the `finally` block must only contain the log, and the crash-detection code should remain after the `finally` block or inside the `try`. Consider placing the log strategically rather than using `finally` if it complicates the control flow — two explicit log calls (one after the loop break, one in the except block) may be cleaner.

4. **Test additions**: Add a test class like `TestStdoutReaderLogging`:
   - Test that starting a session logs "stdout reader started" at INFO level
   - Test that receiving lines logs "stdout line from" at DEBUG level with truncated content
   - Test that EOF logs "stdout reader ended" at INFO level with "EOF" reason

5. **Ordering with the P0 ticket**: This ticket is independently implementable. If done before the P0 fix, the debug log will show raw lines (which currently never arrive, confirming the bug). If done after, it will show JSON events. Either order works, but doing this first provides immediate diagnostic value.

## Design Context

The original design omitted diagnostic logging for the stdout reader, which made the "no agent responses" bug (P0) difficult to diagnose. The design has been updated to require these log lines. See `artifacts/designer/design.md`, section "Diagnostic Logging". This ticket is independently implementable and can be done before or after the subprocess invocation fix.
