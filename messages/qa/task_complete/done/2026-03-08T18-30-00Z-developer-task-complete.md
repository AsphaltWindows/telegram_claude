# Create `run_bot.sh` launcher script

## Metadata
- **From**: developer
- **To**: qa
- **Type**: task-complete
- **Created**: 2026-03-08T18:30:00Z

## Summary of Changes

Created `run_bot.sh` at the project root — a simple launcher script that lets the user paste in their Telegram bot token and start the bot with a single command.

## Files Changed

- **`run_bot.sh`** (created) — Bash launcher script with placeholder token, directory resolution, token validation, and `python -m telegram_bot` invocation

## Requirements Addressed

1. ✅ Created `run_bot.sh` at project root
2. ✅ Clearly marked placeholder variable at top: `BOT_TOKEN="YOUR_TOKEN_HERE"`
3. ✅ Exports `TELEGRAM_BOT_TOKEN` from `BOT_TOKEN`
4. ✅ `cd`s to the script's own directory using `$(dirname "${BASH_SOURCE[0]}")` — works regardless of invocation location
5. ✅ Checks for placeholder value and exits with error message to stderr if unchanged
6. ✅ Runs `exec python -m telegram_bot` after validation
7. ✅ File is executable (`chmod +x`)
8. ✅ Uses `#!/usr/bin/env bash` shebang
- Also follows project conventions: `set -euo pipefail`, uses `exec` for clean process replacement

## QA Steps

1. Verify `run_bot.sh` exists at the project root and is executable (`ls -la run_bot.sh` shows `x` permission bits)
2. Run `./run_bot.sh` without modifying the placeholder token — verify it prints an error message about the token needing to be set and exits with a non-zero status code
3. Read the script and verify it contains `BOT_TOKEN="YOUR_TOKEN_HERE"` near the top
4. Read the script and verify it exports `TELEGRAM_BOT_TOKEN` from `BOT_TOKEN`
5. Read the script and verify it `cd`s to the directory containing the script itself (not hardcoded, but derived from the script's location)
6. Read the script and verify it invokes `python -m telegram_bot`
7. Set `BOT_TOKEN` to a real value and run — verify it attempts to start the bot (it will fail if dependencies aren't installed, but it should get past the token check and attempt `python -m telegram_bot`)

## Test Coverage

This is a standalone shell script with no associated test framework. Verification was done manually:
- Ran the script from a different directory (`/tmp`) to confirm the `cd` logic works and the placeholder token check triggers correctly (exit code 1, error message to stderr).

## Notes

- Used `exec python -m telegram_bot` to replace the shell process with Python, keeping the process tree clean.
- Error message is sent to stderr (`>&2`) following best practices.
- The script follows all conventions from the existing `scripts/run_scheduler.sh` (shebang, `set -euo pipefail`, directory resolution pattern).
