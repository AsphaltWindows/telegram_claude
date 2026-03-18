# Create `install_telegram_bot.sh` script for deploying bot to other projects

## Metadata
- **From**: developer
- **To**: qa
- **Type**: task-complete
- **Created**: 2026-03-09T00:02:00Z

## Summary of Changes

Implemented `install_telegram_bot.sh` — a self-contained installer script that copies the Telegram bot integration into any agent-pipeline project. The script performs pre-flight validation, copies Python source files, modifies `run_bot.sh` and `telegram_bot.yaml` to strip real credentials and fix paths, installs pip dependencies, and prints next-steps instructions.

## Files Changed

- **`install_telegram_bot.sh`** (NEW) — Main installer script at the project root. Accepts a target directory argument, validates it, copies bot files, sanitizes credentials, and prints setup instructions.
- **`artifacts/developer/tests/test_install_telegram_bot.sh`** (NEW) — Comprehensive test suite with 31 assertions covering all requirements: argument validation, error cases, file copying, credential stripping, path corrections, overwrite warnings, and post-install messaging.

## Requirements Addressed

1. ✅ Script created at project root, executable with `chmod +x`
2. ✅ Accepts one positional argument (target project directory)
3. ✅ Pre-flight checks: missing argument (prints usage), directory existence, `pipeline.yaml` presence
4. ✅ Overwrite warning when `telegram_bot/` already exists, continues anyway
5. ✅ Copies `telegram_bot/*.py` files (flat copy excludes subdirectories), `run_bot.sh`, and `telegram_bot.yaml`
6. ✅ Replaces real bot token with `YOUR_TOKEN_HERE` via sed
7. ✅ Changes `cd "$SCRIPT_DIR/../.."` to `cd "$SCRIPT_DIR"` for project-root context
8. ✅ Removes `export PYTHONPATH=` line entirely
9. ✅ Replaces real user ID with `000000000` in `telegram_bot.yaml`
10. ✅ Attempts `pip install python-telegram-bot pyyaml`; prints manual instructions if pip unavailable
11. ✅ Makes copied `run_bot.sh` executable
12. ✅ Prints post-install message with target path and next steps
13. ✅ Does NOT copy `tests/`, `requirements.txt`, or cache directories

## QA Steps

1. Run `./install_telegram_bot.sh` with no arguments — verify it prints usage and exits non-zero.
2. Run `./install_telegram_bot.sh /nonexistent/path` — verify it errors about missing directory.
3. Run against a directory that exists but has no `pipeline.yaml` — verify it errors about missing pipeline config.
4. Run against a valid target directory containing `pipeline.yaml`:
   - Verify `telegram_bot/` directory is created with all `.py` files (no `__pycache__`).
   - Verify `run_bot.sh` exists, is executable, contains `BOT_TOKEN="YOUR_TOKEN_HERE"`, does NOT contain the real bot token, and has corrected `cd`/`PYTHONPATH` logic.
   - Verify `telegram_bot.yaml` exists and its `allowed_users` contains only `000000000`, not real user IDs.
   - Verify `tests/` and `requirements.txt` were NOT copied.
   - Verify the post-install message is printed with correct next steps.
5. Run again against the same target (files already exist) — verify it prints an overwrite warning and completes successfully.
6. Verify the script itself is executable and has a proper shebang (`#!/usr/bin/env bash` or `#!/bin/bash`).

## Test Coverage

All QA steps are covered by `artifacts/developer/tests/test_install_telegram_bot.sh` (31 assertions, all passing). Run with:

```bash
bash artifacts/developer/tests/test_install_telegram_bot.sh
```

Tests cover:
- Error exits for missing args, non-existent directory, missing `pipeline.yaml`
- Correct file copying (all 6 `.py` files present)
- Exclusion of `__pycache__`, `tests/`, `requirements.txt`
- Token replacement and real-token absence verification
- `cd` path correction and `PYTHONPATH` removal
- YAML user ID replacement
- Executable permissions
- Overwrite warning on re-run
- Post-install message content
- Shebang validation

## Notes

- The script includes post-sed `grep` safety checks that abort if the real bot token or user ID survives replacement — defense in depth against credential leaks.
- The `pip install` step will run in the test suite but won't cause failures since the packages are already installed in the development environment. In a clean environment without pip, the script prints manual instructions instead.
