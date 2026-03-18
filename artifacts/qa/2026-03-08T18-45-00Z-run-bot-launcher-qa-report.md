# QA Report: Create `run_bot.sh` launcher script

## Metadata
- **Ticket**: Create `run_bot.sh` launcher script
- **Tested**: 2026-03-08T18:45:00Z
- **Result**: PASS

## Steps

### Step 1: File exists and is executable
- **Result**: PASS
- **Notes**: `ls -la` shows `-rwxrwxr-x`, file is at project root.

### Step 2: Placeholder token triggers error
- **Result**: PASS
- **Notes**: Running with default placeholder prints `Error: BOT_TOKEN is not set...` to stderr and exits with code 1. Tested from `/tmp` to also verify directory resolution.

### Step 3: Contains `BOT_TOKEN="YOUR_TOKEN_HERE"` near top
- **Result**: PASS
- **Notes**: Line 8 of the script.

### Step 4: Exports `TELEGRAM_BOT_TOKEN` from `BOT_TOKEN`
- **Result**: PASS
- **Notes**: Line 20: `export TELEGRAM_BOT_TOKEN="$BOT_TOKEN"`.

### Step 5: `cd`s to script's own directory dynamically
- **Result**: PASS
- **Notes**: Line 11: `cd "$(dirname "${BASH_SOURCE[0]}")"` — not hardcoded.

### Step 6: Invokes `python -m telegram_bot`
- **Result**: PASS
- **Notes**: Line 23: `exec python -m telegram_bot`.

### Step 7: Runs past token check with real token
- **Result**: PASS (partial)
- **Notes**: Script logic verified by inspection — after token validation, the only remaining command is `exec python -m telegram_bot`. Live run skipped as it requires a real bot token and installed dependencies.

## Summary

All QA steps pass. The script is clean, follows project conventions (`set -euo pipefail`, `#!/usr/bin/env bash`, directory resolution pattern matching `scripts/run_scheduler.sh`), and handles the placeholder token case correctly with a clear error message to stderr. Uses `exec` for clean process replacement. No issues found.
