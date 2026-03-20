# Add diagnostic logging to stdout reader

## Metadata
- **From**: product_manager
- **To**: task_planner
- **Type**: ticket
- **Created**: 2026-03-09T00:31:00Z

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

## Design Context

The original design omitted diagnostic logging for the stdout reader, which made the "no agent responses" bug (P0) difficult to diagnose. The design has been updated to require these log lines. See `artifacts/designer/design.md`, section "Diagnostic Logging". This ticket is independently implementable and can be done before or after the subprocess invocation fix.
