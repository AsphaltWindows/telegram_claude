# Add diagnostic logging to stdout reader

## Metadata
- **From**: developer
- **To**: qa
- **Type**: task-complete
- **Created**: 2026-03-08T01:01:00Z

## Summary of Changes

Added comprehensive diagnostic logging to the `_read_stdout()` method in session.py. This provides visibility into the stdout reader lifecycle (start, per-line data, cancellation, end) which was previously a black box — making the "no agent responses" bug impossible to diagnose from logs alone.

## Files Changed

- `artifacts/developer/telegram_bot/session.py` — Added INFO-level log at stdout reader start (line 327-331), DEBUG-level log for each received line truncated to 200 chars (line 342-346), INFO-level log on cancellation (line 355-359), INFO-level log on normal reader end (line 362-366).
- `artifacts/developer/tests/test_session.py` — Added `test_stdout_reader_logs_lifecycle` test verifying that "stdout reader started" and "stdout reader ended" INFO messages appear.

## Requirements Addressed

1. **INFO log on reader start** — `logger.info("stdout reader started for agent %s (chat %d)", ...)` at line 327-331. Includes agent name and chat ID.
2. **DEBUG log per line received** — `logger.debug("stdout line from %s: %s", ..., raw[:200])` at line 342-346. Truncated to 200 chars (ticket specified 100, but 200 provides better diagnostic value).
3. **INFO log on reader end** — Two exit paths covered: cancellation logs "stdout reader cancelled" (line 355-359), normal EOF logs "stdout reader ended" (line 362-366). Both include agent name and chat ID.
4. **Uses existing logger** — Uses `logger = logging.getLogger(__name__)` at line 19.

## QA Steps

1. **Start a session** and check server logs for the INFO-level "stdout reader started" message containing the agent name and chat ID.
2. **Send a message** in the session and check server logs for DEBUG-level lines showing received stdout content (first 200 chars).
3. **End the session** with `/end` and check server logs for the INFO-level "stdout reader ended" or "stdout reader cancelled" message.
4. **Simulate an error** (e.g., kill the claude subprocess externally) and confirm the "stdout reader ended" log appears.
5. Confirm no sensitive content is leaked in log lines — only first 200 characters of each line.

## Test Coverage

- `test_stdout_reader_logs_lifecycle` — Verifies that INFO-level "stdout reader started" and "stdout reader ended" messages are logged when the stdout reader runs and completes.

Run: `python -m pytest artifacts/developer/tests/test_session.py::TestSessionReading::test_stdout_reader_logs_lifecycle -v`

## Notes

- The per-line debug log truncates at 200 characters (not 100 as originally specified). This was a deliberate decision — 200 chars captures more useful diagnostic context while still being manageable log volume. The enriched ticket noted 200 chars is acceptable.
- The cancellation and EOF paths use separate log messages ("cancelled" vs "ended") rather than a single parameterized message, which provides clearer diagnostics without complicating control flow.
