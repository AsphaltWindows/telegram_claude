# Design Change: Add environment robustness features (pre-flight check, claude_path config, stderr surfacing, nvm sourcing)

## Metadata
- **From**: designer
- **To**: product_manager
- **Type**: design-change
- **Created**: 2026-03-08T00:30:00Z

## Changes Made

1. **New section: "Pre-flight Environment Check"** — The bot must run `claude --version` at startup and fail fast with a clear error if the CLI is unavailable or broken. Logs the detected version on success.

2. **New section: "Subprocess Environment"** — Documents the nvm/Node.js environment concern and the two mitigation strategies (nvm sourcing in launcher script + configurable `claude_path`).

3. **New config option: `claude_path`** in `telegram_bot.yaml` — Optional field allowing the user to specify the full path to the `claude` binary, bypassing PATH resolution. Critical for non-login contexts (systemd, cron) where nvm is not initialized.

4. **Updated error case: "Agent process crashes/dies unexpectedly"** — The crash notification message now includes the last few lines of stderr, so users see diagnostic errors (e.g., "node: command not found") directly in Telegram instead of having to check server logs.

5. **Updated `run_bot.sh` requirements** — The launcher script must source `$NVM_DIR/nvm.sh` if it exists, ensuring Node.js and npm-installed binaries are on PATH when invoked from non-login contexts.

## Motivation

The operator raised a concern (forum topic `2026-03-08T00:04:00Z-operator-nvm-node-environment-for-claude-subprocess.md`) that the bot may fail to run `claude` when the subprocess environment lacks nvm initialization. This is a real risk when the bot runs as a systemd service or cron job. The design changes add defense-in-depth: the launcher script sources nvm, the config allows specifying a direct path, the bot validates the CLI at startup, and crash messages include stderr for diagnostics.

## Files Changed

- `artifacts/designer/design.md` — Added "Pre-flight Environment Check" and "Subprocess Environment" sections; updated `telegram_bot.yaml` config spec with `claude_path` option; updated error cases table to include stderr in crash messages; updated `run_bot.sh` requirements to include nvm sourcing
