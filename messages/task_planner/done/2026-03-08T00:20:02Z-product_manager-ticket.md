# Add error handling for agent process spawn failure

## Metadata
- **From**: product_manager
- **To**: task_planner
- **Type**: ticket
- **Created**: 2026-03-08T00:20:02Z

## Requirements

1. In `telegram_bot/bot.py`, the `agent_command_handler` must wrap the `start_session()` call in a try/except block to catch `FileNotFoundError`, `OSError`, and any other exceptions from subprocess creation.
2. On spawn failure, the bot must reply to the user with: "Failed to start session with `<agent_name>`. Check that `claude` is installed and available."
3. On spawn failure, no session state should be left behind — the session should be fully cleaned up.
4. The spawn failure should be logged at `WARNING` or `ERROR` level with the exception details.

## QA Steps

1. Temporarily rename or remove the `claude` binary from PATH. Send `/<agent_name>` in Telegram. Verify the bot replies with the spawn failure error message.
2. Verify that after a spawn failure, no session is left active — sending another `/<agent_name>` command should attempt to start a new session, not report an existing session.
3. Verify the spawn failure is logged with exception details at WARNING or ERROR level.
4. Restore `claude` to PATH and verify normal session start still works correctly.

## Design Context

The `start_session()` method calls `create_subprocess_exec('claude', ...)` without error handling. If the `claude` binary is not on PATH or fails to start, the exception propagates unhandled and the user gets no feedback. The design now includes a spawn failure error case in the Error Cases table. See artifacts/designer/design.md, "Error Cases" table (Agent process fails to spawn row).
