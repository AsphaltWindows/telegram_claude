# Add configurable claude_path config option and nvm sourcing in run_bot.sh

## Metadata
- **From**: product_manager
- **To**: task_planner
- **Type**: ticket
- **Created**: 2026-03-09T01:01:00Z

## Requirements

1. Add an optional `claude_path` field to the `telegram_bot.yaml` configuration spec. When set, the bot must use this path instead of bare `claude` for all subprocess invocations (both the pre-flight version check and `SessionManager.start_session()`).
2. When `claude_path` is unset or empty, the bot must fall back to resolving `claude` from PATH (current behavior).
3. If `claude_path` is set but the specified file does not exist or is not executable, the pre-flight check (from the related ticket) should catch this and fail fast with a clear error message.
4. Update `run_bot.sh` (the launcher script) to source `$NVM_DIR/nvm.sh` if the file exists, before launching the bot process. This ensures that nvm-managed Node.js and npm-installed binaries (including `claude`) are available on PATH even when invoked from systemd or cron.
5. The nvm sourcing in `run_bot.sh` must be guarded: only source if `$NVM_DIR/nvm.sh` exists, and do not fail if it doesn't (not all deployments use nvm).
6. Document the `claude_path` option in any existing config documentation or example config files with a comment explaining when and why to use it.

## QA Steps

1. Set `claude_path` in `telegram_bot.yaml` to the full path of the `claude` binary (e.g., `/home/user/.nvm/versions/node/v22.x/bin/claude`). Start the bot and verify it uses that path for the version check and session spawning.
2. Leave `claude_path` unset in config. Verify the bot falls back to bare `claude` from PATH and works normally.
3. Set `claude_path` to a non-existent path. Verify the bot fails fast at startup with a clear error message.
4. Set `claude_path` to a file that exists but is not executable. Verify the bot fails with a clear error.
5. In `run_bot.sh`, set `NVM_DIR` to a valid nvm installation directory and verify that after sourcing, `node` and `claude` are on PATH.
6. In `run_bot.sh`, unset `NVM_DIR` or point it to a non-existent directory. Verify the script does not error and the bot still attempts to start.
7. Test the full flow from a clean systemd service (where .bashrc is not sourced): verify that `run_bot.sh` correctly initializes nvm and the bot can find and run `claude`.

## Design Context

When the bot runs as a systemd service or cron job, the user's shell profile (which initializes nvm) is not sourced, so `claude` may not be on PATH. This ticket provides two complementary mitigations: (1) a configurable `claude_path` that bypasses PATH resolution entirely, and (2) nvm sourcing in the launcher script for users who prefer the default PATH-based resolution. See `artifacts/designer/design.md`, sections "Subprocess Environment" and the `telegram_bot.yaml` config spec.
