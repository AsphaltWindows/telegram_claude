# Install Script Design: `install_telegram_bot.sh`

## Overview

A shell script in the project root that installs the Telegram bot integration into another project directory where an agent pipeline has already been set up.

The script copies all necessary files, blanks out credentials (bot API token and whitelisted user IDs), and adjusts paths so the bot works from the target project root.

## Usage

```bash
./install_telegram_bot.sh /path/to/target/project
./install_telegram_bot.sh --force /path/to/target/project
```

## What Gets Installed

### Files copied to target project root

| Source (this repo) | Destination (target) | Notes |
|---|---|---|
| `artifacts/developer/telegram_bot/` | `<target>/telegram_bot/` | Python package (`.py` files only, recursive, no `__pycache__`/`.pytest_cache`) |
| (generated) | `<target>/run_bot.sh` | Launcher script, generated fresh with correct paths and blanked token |
| (generated) | `<target>/telegram_bot.yaml` | Config file with placeholder user ID |

### Files NOT copied

- `artifacts/developer/tests/` — test files stay in this repo
- `artifacts/developer/requirements.txt` — dependencies are pip-installed directly
- `__pycache__/`, `.pytest_cache/`, `.pyc` — build artifacts excluded

## Credential Blanking

### `run_bot.sh` (generated, not copied verbatim)

Rather than copying and sed-ing the source `run_bot.sh`, the install script generates a clean version because the installed layout differs from the source layout:

- `BOT_TOKEN="YOUR_TOKEN_HERE"` — placeholder
- `cd` to the script's own directory (which IS the project root) — no `../../` navigation
- No `PYTHONPATH` manipulation needed — `telegram_bot/` is at the project root
- nvm sourcing preserved (needed for non-login contexts)
- All other logic (token validation, pipeline.yaml resolution, pipeline.yaml existence check) preserved

### `telegram_bot.yaml` (generated)

- `allowed_users` list has placeholder: `- 000000000`
- All other fields use the same defaults as the source

## Dependency Installation

The script auto-installs Python dependencies:
1. Run `pip install python-telegram-bot pyyaml`
2. If `pip` is not available, print an error and exit (these are required to run `run_bot.sh`)

## Pre-flight Checks

Before installing, the script validates:
1. Target directory argument is provided
2. Target directory exists and is a directory
3. Target directory contains a `pipeline.yaml` (confirming it's an agent pipeline project)
4. If `telegram_bot/` already exists in the target, abort unless `--force` is passed

## `--force` Flag

When `--force` is provided, the script overwrites existing files (`telegram_bot/`, `run_bot.sh`, `telegram_bot.yaml`) without prompting. Without `--force`, if any of these already exist, the script prints an error and exits.

## Post-Install Output

After successful installation, print:
```
Telegram bot installed to /path/to/target/project

Next steps:
  1. Edit run_bot.sh and set your BOT_TOKEN
  2. Edit telegram_bot.yaml and set your allowed_users (Telegram user IDs)
  3. Run: ./run_bot.sh
```
