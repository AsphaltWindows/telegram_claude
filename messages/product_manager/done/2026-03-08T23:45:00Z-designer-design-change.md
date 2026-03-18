# Design Change: Install script for deploying Telegram bot to other projects

## Metadata
- **From**: designer
- **To**: product_manager
- **Type**: design-change
- **Created**: 2026-03-08T23:45:00Z

## Changes Made

Added a new design document `artifacts/designer/install-script-design.md` specifying an installation shell script (`install_telegram_bot.sh`) that lives in the project root and can deploy the Telegram bot integration into any other project directory with an agent pipeline.

Key design decisions:
- Script copies `telegram_bot/` Python package, `run_bot.sh`, and `telegram_bot.yaml` to the target project root
- Credentials are blanked: bot token becomes `YOUR_TOKEN_HERE`, allowed_users becomes `000000000`
- `run_bot.sh` is modified during copy to fix working directory logic (target has files at root, not in `artifacts/developer/`)
- PYTHONPATH export is simplified since `telegram_bot/` lives at the target project root
- Pre-flight checks: validates target dir exists and contains `pipeline.yaml`
- Attempts `pip install python-telegram-bot pyyaml`, falls back to manual instructions
- Warns but overwrites if files already exist in target

## Motivation

User wants to be able to install this Telegram bot integration into other projects that have the agent pipeline set up, using a single shell script. The current code lives in `artifacts/developer/` with real credentials that need to be stripped for distribution.

## Files Changed

- `artifacts/designer/install-script-design.md` — new document specifying the install script requirements
