# Add diagnostic logging to stdout reader

## Metadata
- **From**: product_manager
- **To**: task_planner
- **Type**: ticket
- **Created**: 2026-03-08T22:01:00Z

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

## Design Context

Diagnostic logging was identified as a critical missing piece during the investigation of the P0 "no agent responses" bug. Without logging in the stdout reader, there is no way to distinguish between "no data is arriving from the subprocess" and "data arrives but is lost before reaching Telegram." This logging will aid debugging of any future output relay issues.

See `artifacts/designer/design.md`, section "Diagnostic Logging".
