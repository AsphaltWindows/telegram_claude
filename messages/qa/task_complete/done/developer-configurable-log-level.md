# configurable-log-level

## Metadata
- **From**: developer
- **To**: qa

## Content

### Summary of Changes

Implemented configurable log level via the LOG_LEVEL environment variable in bot.py main().

### Files Changed

- **artifacts/developer/telegram_bot/bot.py** — Added `import os`, replaced hardcoded `logging.basicConfig(level=logging.INFO)` with LOG_LEVEL env var lookup with validation and fallback.
- **artifacts/developer/telegram_bot/tests/test_log_level.py** — New test file with 7 tests covering default, valid, case-insensitive, and invalid LOG_LEVEL handling.

### Requirements Addressed

1. Replaced hardcoded logging.basicConfig with configurable level from LOG_LEVEL env var — done.
2. Implementation uses getattr(logging, ...) pattern as specified — done.
3. Default to INFO when LOG_LEVEL not set — done.
4. Accepts standard Python logging level names — done.
5. Invalid values fall back to INFO with a warning — done, does not crash.
6. Logs active log level at startup at INFO level — done.

### QA Steps

1. Start the bot without setting LOG_LEVEL. Verify it runs at INFO level (same as current behavior). Verify the startup log shows the active log level.
2. Start the bot with LOG_LEVEL=DEBUG. Verify DEBUG-level messages now appear in the log.
3. Start the bot with LOG_LEVEL=WARNING. Verify INFO-level messages no longer appear.
4. Start the bot with LOG_LEVEL=invalid. Verify it falls back to INFO and logs a warning about the invalid value. Verify it does not crash.
5. Start the bot with LOG_LEVEL=debug (lowercase). Verify it correctly normalizes to DEBUG level.

### Test Coverage

7 tests in test_log_level.py:
- test_default_log_level_is_info
- test_log_level_debug
- test_log_level_warning
- test_log_level_case_insensitive
- test_invalid_log_level_falls_back_to_info
- test_invalid_log_level_logs_warning
- test_startup_logs_active_level

Run: python -m pytest artifacts/developer/telegram_bot/tests/test_log_level.py -v

### Notes

- The `os` module was not previously imported in bot.py and was added.
- The invalid level detection uses a flag (`invalid_log_level`) to avoid calling getattr twice while ensuring basicConfig is called before any logger.warning() call (since handlers need to be configured first).
