# Telegram Bot: Project Scaffolding & Configuration Loading

## Metadata
- **From**: developer
- **To**: qa
- **Type**: task-complete
- **Created**: 2026-03-08T17:45:00Z

## Summary of Changes

Implemented the foundational project scaffolding and configuration loading for the Telegram bot integration. Created the `telegram_bot` Python package with a typed config module that loads settings from environment variables and a YAML config file, with full validation and sensible defaults.

## Files Changed

- `artifacts/developer/requirements.txt` — Created with `python-telegram-bot` and `pyyaml` dependencies
- `artifacts/developer/telegram_bot/__init__.py` — Package init file with docstring
- `artifacts/developer/telegram_bot/config.py` — Configuration loading module with `BotConfig` dataclass and `load_config()` function
- `artifacts/developer/telegram_bot.yaml` — Template config file with placeholder user IDs and documented defaults
- `artifacts/developer/tests/__init__.py` — Test package init
- `artifacts/developer/tests/test_config.py` — 11 unit tests covering happy paths, missing required values, and validation edge cases

## Requirements Addressed

1. ✅ Created `telegram_bot/` package with `__init__.py`
2. ✅ Created `telegram_bot/config.py` that:
   - a. Loads `TELEGRAM_BOT_TOKEN` from env vars; raises `ValueError` if missing
   - b. Loads `telegram_bot.yaml` with `allowed_users`, `idle_timeout` (default 600), and `shutdown_message` (default provided)
   - c. Exposes `BotConfig` dataclass with typed access to all fields
3. ✅ Created `telegram_bot.yaml` template at project root with placeholder user IDs
4. ✅ Created `requirements.txt` with `python-telegram-bot` and `pyyaml`
5. ✅ Config loading raises clear `ValueError` for missing `TELEGRAM_BOT_TOKEN` and missing/empty `allowed_users`

## QA Steps

1. Verify `telegram_bot/__init__.py` exists and the package is importable
2. Set `TELEGRAM_BOT_TOKEN=test123` env var, create a valid `telegram_bot.yaml` with sample user IDs, and verify `config.py` loads all values correctly
3. Verify that omitting `TELEGRAM_BOT_TOKEN` raises a clear error message
4. Verify that omitting `allowed_users` from the yaml raises a clear error
5. Verify that `idle_timeout` defaults to 600 when not specified in yaml
6. Verify that `shutdown_message` defaults correctly when not specified
7. Verify `telegram_bot.yaml` template exists at project root with correct structure
8. Verify `requirements.txt` includes `python-telegram-bot` and `pyyaml`

## Test Coverage

11 unit tests in `tests/test_config.py` covering:

- **Happy path** (3 tests): Full config loading, default value application, return type verification
- **Missing required values** (4 tests): Missing token, missing `allowed_users`, empty `allowed_users` list, missing YAML file
- **Validation edge cases** (3 tests): Non-integer user IDs, negative idle timeout, whitespace-only shutdown message
- **Package import** (1 test): Verifies `telegram_bot` package is importable

Run with: `cd artifacts/developer && python -m pytest tests/test_config.py -v`

## Notes

- Python 3.7 compatibility: Used `from __future__ import annotations` and `typing.List`/`typing.Optional` instead of `list[int]` and `Path | None` syntax.
- The `load_config()` function accepts an optional `config_path` keyword argument for testability (overrides the default YAML file location). This makes unit testing straightforward without needing to mock file I/O.
- `_PROJECT_ROOT` is computed as two levels up from `config.py` (i.e., `artifacts/developer/`), which is where `telegram_bot.yaml` lives.
- Used `yaml.safe_load()` (not `yaml.load()`) per security best practices.
