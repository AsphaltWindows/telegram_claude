# QA Report: Create `install_telegram_bot.sh` script for deploying bot to other projects

## Metadata
- **Ticket**: Create `install_telegram_bot.sh` script for deploying bot to other projects
- **Tested**: 2026-03-09T00:05:00Z
- **Result**: PASS

## Steps

### Step 1: No arguments — prints usage and exits non-zero
- **Result**: PASS
- **Notes**: Verified via test suite (assertions 1-2). Script prints usage message and exits non-zero.

### Step 2: Non-existent directory — errors about missing directory
- **Result**: PASS
- **Notes**: Verified via test suite (assertions 3-4). Prints directory error to stderr and exits non-zero.

### Step 3: Directory without `pipeline.yaml` — errors about missing pipeline config
- **Result**: PASS
- **Notes**: Verified via test suite (assertions 5-6). Prints pipeline.yaml error and exits non-zero.

### Step 4: Valid target directory with `pipeline.yaml`
- **Result**: PASS
- **Notes**: All sub-checks passed (assertions 7-28):
  - 6 `.py` files copied correctly (no `__pycache__`, no `tests/`, no `requirements.txt`)
  - `run_bot.sh` exists, is executable, contains `YOUR_TOKEN_HERE` placeholder, real token stripped
  - `cd` path corrected from `"$SCRIPT_DIR/../.."` to `"$SCRIPT_DIR"`
  - `export PYTHONPATH=` line removed
  - `telegram_bot.yaml` contains `000000000`, real user ID stripped
  - Post-install message printed with next steps

### Step 5: Re-run on existing target — overwrite warning printed
- **Result**: PASS
- **Notes**: Verified via test suite (assertion 29). Warning printed, install completes successfully.

### Step 6: Script is executable with proper shebang
- **Result**: PASS
- **Notes**: Verified via test suite (assertions 30-31). Script has `#!/usr/bin/env bash` shebang and executable permission.

## Summary

All 6 QA steps pass, validated by the automated test suite (31/31 assertions passing). The script is well-structured with defense-in-depth grep checks that abort if real credentials survive sed replacement. No issues found.
