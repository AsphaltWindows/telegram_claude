# Telegram Bot: Project Scaffolding & Configuration Loading

## Metadata
- **From**: product_manager
- **To**: task_planner
- **Type**: ticket
- **Created**: 2026-03-08T15:10:00Z

## Requirements

1. Create the `telegram_bot/` package directory with an `__init__.py` file
2. Create `telegram_bot/config.py` that:
   a. Loads `TELEGRAM_BOT_TOKEN` from environment variables (required; raise an error if missing)
   b. Loads `telegram_bot.yaml` from the project root with the following fields:
      - `allowed_users`: list of integer Telegram user IDs
      - `idle_timeout`: integer seconds (default 600)
      - `shutdown_message`: string (default: "Record the product of this conversation as appropriate for your role and exit.")
   c. Exposes a config object/dataclass with typed access to all fields
3. Create `telegram_bot.yaml` at the project root as a template/example config file matching the schema in the design (with placeholder user IDs)
4. Create or update `requirements.txt` to include `python-telegram-bot` and `pyyaml` as dependencies
5. Config loading must raise clear errors for missing required fields (`TELEGRAM_BOT_TOKEN`, `allowed_users`)

## QA Steps

1. Verify `telegram_bot/__init__.py` exists and the package is importable
2. Set `TELEGRAM_BOT_TOKEN=test123` env var, create a valid `telegram_bot.yaml` with sample user IDs, and verify `config.py` loads all values correctly
3. Verify that omitting `TELEGRAM_BOT_TOKEN` raises a clear error message
4. Verify that omitting `allowed_users` from the yaml raises a clear error
5. Verify that `idle_timeout` defaults to 600 when not specified in yaml
6. Verify that `shutdown_message` defaults correctly when not specified
7. Verify `telegram_bot.yaml` template exists at project root with correct structure
8. Verify `requirements.txt` includes `python-telegram-bot` and `pyyaml`

## Design Context

This is the foundational scaffolding ticket for the Telegram bot integration. All other tickets depend on this package structure and config module existing. See `artifacts/designer/design.md`, sections "Configuration" and "File Structure".
