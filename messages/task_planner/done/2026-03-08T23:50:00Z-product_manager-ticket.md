# Create `install_telegram_bot.sh` script for deploying bot to other projects

## Metadata
- **From**: product_manager
- **To**: task_planner
- **Type**: ticket
- **Created**: 2026-03-08T23:50:00Z

## Requirements

1. Create `install_telegram_bot.sh` in the project root (next to `pipeline.yaml`), executable (`chmod +x`).
2. The script accepts one positional argument: the path to the target project directory.
3. **Pre-flight checks** (abort with clear error message if any fail):
   - Argument is provided; print usage if missing.
   - Target directory exists and is a directory.
   - Target directory contains a `pipeline.yaml` file.
4. If `telegram_bot/` already exists in the target directory, print a warning but continue (overwrite).
5. **Copy files** from this repo to the target project root:
   - `artifacts/developer/telegram_bot/` → `<target>/telegram_bot/` (all `.py` files, recursive; exclude `__pycache__/` and `.pytest_cache/`).
   - `artifacts/developer/run_bot.sh` → `<target>/run_bot.sh` (with modifications per req 6–8).
   - `artifacts/developer/telegram_bot.yaml` → `<target>/telegram_bot.yaml` (with modifications per req 9).
6. In the copied `run_bot.sh`, replace the `BOT_TOKEN="<actual value>"` line with `BOT_TOKEN="YOUR_TOKEN_HERE"`.
7. In the copied `run_bot.sh`, change the working-directory (`cd`) logic so the script `cd`s to its own directory (the target project root) instead of navigating `../../` from `artifacts/developer/`.
8. In the copied `run_bot.sh`, remove or simplify the `PYTHONPATH` export since `telegram_bot/` will be at the project root.
9. In the copied `telegram_bot.yaml`, replace the `allowed_users` list entries with a single placeholder entry `- 000000000`.
10. **Dependency installation**: attempt `pip install python-telegram-bot pyyaml`. If `pip` is not available, print a warning with manual install instructions instead.
11. Make the copied `run_bot.sh` executable in the target.
12. **Post-install message**: print the target path and next-steps instructions (edit token, edit allowed_users, run the bot).
13. Do NOT copy `artifacts/developer/tests/`, `artifacts/developer/requirements.txt`, or any cache directories.

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

## Design Context

The user wants a single command to install the Telegram bot integration into any project that already has the agent pipeline set up. The script must strip real credentials so the distributed copy is safe to share. See `artifacts/designer/install-script-design.md` for the full specification.
