# Create `run_bot.sh` launcher script

## Metadata
- **From**: product_manager
- **To**: task_planner
- **Type**: ticket
- **Created**: 2026-03-08T00:01:00Z

## Requirements

1. Create a file `run_bot.sh` at the project root
2. The script must have a clearly marked placeholder variable at the top: `BOT_TOKEN="YOUR_TOKEN_HERE"`
3. The script must export `TELEGRAM_BOT_TOKEN` from the `BOT_TOKEN` variable
4. The script must `cd` to the project root directory, derived from the script's own location (e.g., using `$(dirname "$0")` or `BASH_SOURCE`), so that `claude` agent commands resolve correctly regardless of where the script is invoked from
5. The script must check whether `BOT_TOKEN` is still set to the placeholder value `YOUR_TOKEN_HERE` and refuse to start if so, printing a clear error message telling the user to edit the script and set their token
6. The script must run `python -m telegram_bot` after validation passes
7. The file must be executable (`chmod +x run_bot.sh`)
8. The script should use `#!/usr/bin/env bash` as the shebang line

## QA Steps

1. Verify `run_bot.sh` exists at the project root and is executable (`ls -la run_bot.sh` shows `x` permission bits)
2. Run `./run_bot.sh` without modifying the placeholder token — verify it prints an error message about the token needing to be set and exits with a non-zero status code
3. Read the script and verify it contains `BOT_TOKEN="YOUR_TOKEN_HERE"` near the top
4. Read the script and verify it exports `TELEGRAM_BOT_TOKEN` from `BOT_TOKEN`
5. Read the script and verify it `cd`s to the directory containing the script itself (not hardcoded, but derived from the script's location)
6. Read the script and verify it invokes `python -m telegram_bot`
7. Set `BOT_TOKEN` to a real value and run — verify it attempts to start the bot (it will fail if dependencies aren't installed, but it should get past the token check and attempt `python -m telegram_bot`)

## Design Context

The user wants a simple entry point where they can paste in their Telegram bot token and run the bot without needing to manually export environment variables or remember the Python module invocation. See `artifacts/designer/design.md`, section "Launcher Script: `run_bot.sh`".
