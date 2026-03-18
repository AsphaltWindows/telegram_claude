# Design Change: Add session-start feedback, spawn failure handling, and logging improvements

## Metadata
- **From**: designer
- **To**: product_manager
- **Type**: design-change
- **Created**: 2026-03-08T00:15:00Z

## Changes Made

1. **Session-start confirmation message**: Added step 4 to the "Starting a Session" flow — the bot must send "Starting session with `<agent_name>`…" immediately after spawning the process, before forwarding any first message. This gives the user immediate feedback that their command was received.

2. **Spawn failure error case**: Added a new row to the Error Cases table for when the `claude` subprocess fails to spawn (e.g., binary not found, permission denied). Bot should reply: "Failed to start session with `<agent_name>`. Check that `claude` is installed and available."

3. **Auth decorator debug logging**: Updated the "Unauthorized user" error case to note that blocked attempts should be logged at DEBUG level for diagnostics. The UX remains silent-ignore.

4. **Stderr logging level**: Updated the Technical Design section to specify WARNING level (instead of DEBUG) for agent stderr output, so subprocess errors are visible at the default INFO log level.

## Motivation

The operator reported the bot not responding to messages. Investigation revealed several UX gaps: no feedback on session start, no error message if the process fails to spawn, and invisible subprocess errors due to DEBUG-level stderr logging. These changes address the diagnostic and user-feedback gaps that made it impossible to tell what was happening.

## Files Changed

- `artifacts/designer/design.md` — updated "Starting a Session" flow (added confirmation step), "Error Cases" table (added spawn failure, updated auth logging note), and "Technical Design > Process Management" (stderr logging level)
