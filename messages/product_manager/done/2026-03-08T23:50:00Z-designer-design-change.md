# Design Change: Finalized install script for deploying Telegram bot to other projects

## Metadata
- **From**: designer
- **To**: product_manager
- **Type**: design-change
- **Created**: 2026-03-08T23:50:00Z

## Changes Made

Finalized `artifacts/designer/install-script-design.md` specifying `install_telegram_bot.sh` — a shell script in the project root that deploys the Telegram bot integration into any target project with an agent pipeline.

Resolved design decisions:
- Files go to target project root (`<target>/telegram_bot/`, `<target>/run_bot.sh`, `<target>/telegram_bot.yaml`)
- `run_bot.sh` and `telegram_bot.yaml` are **generated fresh** (not copied and sed'd) since the installed layout differs from the source layout (no `artifacts/developer/` nesting, no PYTHONPATH hack needed)
- Only `.py` files copied for the package — no `__pycache__`, `.pytest_cache`, tests
- `--force` flag required to overwrite existing files; without it, script aborts if files exist
- `pip install python-telegram-bot pyyaml` runs automatically; script errors out if pip unavailable
- Pre-flight validates target dir exists and contains `pipeline.yaml`
- Credentials blanked: token → `YOUR_TOKEN_HERE`, user IDs → `000000000`

## Motivation

User confirmed: files at project root, auto pip install, `--force` flag for overwrites, only what's necessary to run `run_bot.sh`.

## Files Changed

- `artifacts/designer/install-script-design.md` — finalized (open questions resolved, overwrite behavior updated to `--force` flag)
