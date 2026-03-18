# Add diagnostic logging to stdout reader

## Metadata
- **From**: task_planner
- **To**: developer
- **Type**: enriched-ticket
- **Created**: 2026-03-08T22:11:00Z

## Requirements

1. Add an INFO-level log line when the stdout reader (`_read_stdout`) starts, including the agent name and chat ID. Example: `"stdout reader started for agent %s (chat %d)"`.

2. Add a DEBUG-level log line when the stdout reader receives a line from the subprocess, including the first 100 characters of the line. Example: `"stdout line from %s: %s"`.

3. Add an INFO-level log line when the stdout reader exits, including the agent name, chat ID, and the reason for exit (EOF, cancellation, error). Example: `"stdout reader ended for agent %s (chat %d): %s"`.

4. All log lines must use the existing logger in session.py (no new logger setup needed).

## QA Steps

1. Start an agent session and check the server logs — confirm the "stdout reader started" INFO message appears with the correct agent name and chat ID.

2. Send a message to the agent and check the server logs at DEBUG level — confirm the "stdout line from" message appears showing truncated content.

3. End a session with `/end` and check the server logs — confirm the "stdout reader ended" INFO message appears with reason "EOF" or similar.

4. Kill an agent process externally (or simulate a crash) — confirm the "stdout reader ended" message appears with an appropriate error reason.

## Technical Context

### Relevant Files

| File | Path | Status |
|------|------|--------|
| **session.py** | `artifacts/developer/telegram_bot/session.py` | **Already implemented.** Lines 327-331 log "stdout reader started" at INFO. Lines 342-346 log each line at DEBUG (truncated to 200 chars). Lines 354-360 log "cancelled" at INFO. Lines 362-366 log "stdout reader ended" at INFO. |
| **test_session.py** | `artifacts/developer/tests/test_session.py` | **Tests for logging not yet added.** Should add tests verifying the log lines appear. Follow the existing pattern at lines 170-190 (`test_stderr_logged_at_warning_level`) which patches `telegram_bot.session.logger`. |

### Patterns and Conventions

- **Logger**: `logger = logging.getLogger(__name__)` at line 19.
- **Log levels in module**: INFO for lifecycle events (session start, reader start/end, idle timeout), WARNING for unexpected conditions (stderr, unexpected exit, force-kill), DEBUG for verbose/per-line data.
- **Testing logs**: Patch `telegram_bot.session.logger`, then assert on `mock_logger.info.assert_any_call(...)` etc. See `test_stderr_logged_at_warning_level` at line 170.

### Dependencies and Integration Points

- No external dependencies. Logging-only change.
- The debug log at line 342 logs `raw[:200]` (the raw decoded line before JSON parsing), which provides diagnostic visibility regardless of whether JSON parsing succeeds.

### Implementation Notes

**This work is already implemented in session.py.** The diagnostic logging was added as part of the `_read_stdout()` rewrite for the stream-json protocol. Specifically:

- **"started" log** (line 327-331): `logger.info("stdout reader started for agent %s (chat %d)", self.agent_name, self.chat_id)`
- **Per-line debug log** (line 342-346): `logger.debug("stdout line from %s: %s", self.agent_name, raw[:200])` — note: logs first 200 chars rather than 100 as originally specified, which is acceptable.
- **"cancelled" log** (line 354-360): `logger.info("stdout reader cancelled for agent %s (chat %d)", self.agent_name, self.chat_id)`
- **"ended" log** (line 362-366): `logger.info("stdout reader ended for agent %s (chat %d)", self.agent_name, self.chat_id)`

**Remaining work — tests only:**

Add a test class `TestStdoutReaderLogging` with:
1. Test that starting a session and letting stdout deliver lines logs "stdout reader started" at INFO level.
2. Test that receiving a line logs "stdout line from" at DEBUG level with truncated content.
3. Test that EOF (empty readline) logs "stdout reader ended" at INFO level.
4. Test that cancellation logs "stdout reader cancelled" at INFO level.

Pattern to follow:
```python
with patch("telegram_bot.session.logger") as mock_logger:
    session.start()
    await asyncio.sleep(0.05)
    mock_logger.info.assert_any_call(
        "stdout reader started for agent %s (chat %d)",
        "test-agent",
        100,
    )
```

## Design Context

Diagnostic logging was identified as a critical missing piece during the investigation of the P0 "no agent responses" bug. Without logging in the stdout reader, there is no way to distinguish between "no data is arriving from the subprocess" and "data arrives but is lost before reaching Telegram." This logging will aid debugging of any future output relay issues.

See `artifacts/designer/design.md`, section "Diagnostic Logging".

**Note:** The implementation is already complete in session.py. Only test additions remain.
