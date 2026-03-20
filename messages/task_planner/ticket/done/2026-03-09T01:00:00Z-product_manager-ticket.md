# Add pre-flight claude CLI check at bot startup and surface stderr on agent crash

## Metadata
- **From**: product_manager
- **To**: task_planner
- **Type**: ticket
- **Created**: 2026-03-09T01:00:00Z

## Requirements

1. During bot startup (in `main()` or `build_application()`), run `claude --version` as a subprocess and verify it exits successfully (exit code 0).
2. If the `claude_path` config option is set (see ticket for configurable claude_path), use that path instead of bare `claude` for the version check. If `claude_path` is not yet implemented, use bare `claude`.
3. On success, log the detected claude CLI version at INFO level.
4. On failure (command not found, non-zero exit, timeout after 10 seconds), log a clear error message indicating the likely cause (e.g., "claude CLI not found on PATH — is nvm initialized?") and exit the bot process with a non-zero exit code. Do not proceed to start the Telegram polling loop.
5. In `SessionManager`, when the agent subprocess exits unexpectedly (non-zero exit code), capture the last 10 lines of stderr from the process.
6. Include the captured stderr content in the "Session ended unexpectedly" message sent to the user in Telegram, truncated to a reasonable length (e.g., 500 characters) to avoid hitting Telegram message limits.
7. If stderr is empty, the crash message should still be sent but without the stderr section.

## QA Steps

1. Temporarily rename the `claude` binary (or set PATH to exclude it) and start the bot. Verify the bot fails fast with a clear error message mentioning that `claude` is not available, and does not start the Telegram polling loop.
2. Create a mock `claude` script that exits with code 1 and outputs an error to stderr. Start the bot pointing to it. Verify the bot fails fast with the error output logged.
3. With a working `claude` binary, start the bot and verify the log contains the claude version at INFO level and the bot proceeds normally.
4. Simulate an agent subprocess crash (e.g., kill the process, or use a mock that writes to stderr then exits non-zero). Verify the Telegram user receives a "Session ended unexpectedly" message that includes the stderr content.
5. Simulate an agent subprocess crash where stderr is empty. Verify the user still receives the "Session ended unexpectedly" message without a blank/broken stderr section.
6. Verify that very long stderr output is truncated to avoid exceeding Telegram message limits.

## Design Context

The operator identified that when the bot runs in non-login environments (systemd, cron), nvm may not be initialized, causing `claude` to be unavailable or broken at runtime. Currently, such failures are silent or produce generic error messages. This ticket adds defense-in-depth: fail fast at startup if the CLI is broken, and surface stderr diagnostics to users when agent processes crash unexpectedly. See `artifacts/designer/design.md`, sections "Pre-flight Environment Check" and the updated error cases table.
