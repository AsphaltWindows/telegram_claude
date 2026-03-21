# configurable-log-level

## Metadata
- **From**: task_planner
- **To**: developer

## Content

### Requirements

1. Replace the hardcoded `logging.basicConfig(level=logging.INFO)` in `bot.py` with a configurable level read from the `LOG_LEVEL` environment variable.
2. The implementation should be: `logging.basicConfig(level=getattr(logging, os.environ.get('LOG_LEVEL', 'INFO').upper()))`.
3. Default value when `LOG_LEVEL` is not set: `INFO` (preserves current behavior).
4. Accepted values: `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL` (standard Python logging level names).
5. If an invalid value is provided (e.g., `LOG_LEVEL=VERBOSE`), the bot should fall back to `INFO` and log a warning about the invalid value. Do not crash on an invalid LOG_LEVEL.
6. Log the active log level at startup at INFO level (e.g., `INFO: Log level set to DEBUG`).

### QA Steps

1. Start the bot without setting `LOG_LEVEL`. Verify it runs at INFO level (same as current behavior). Verify the startup log shows the active log level.
2. Start the bot with `LOG_LEVEL=DEBUG`. Verify DEBUG-level messages now appear in the log (e.g., raw stdout lines from session.py).
3. Start the bot with `LOG_LEVEL=WARNING`. Verify INFO-level messages no longer appear.
4. Start the bot with `LOG_LEVEL=invalid`. Verify it falls back to INFO and logs a warning about the invalid value. Verify it does not crash.
5. Start the bot with `LOG_LEVEL=debug` (lowercase). Verify it correctly normalizes to DEBUG level (case-insensitive).

### Technical Context

#### Relevant Files

- **`artifacts/developer/telegram_bot/bot.py`** (PRIMARY) — Contains the `main()` function (lines 567-588) where `logging.basicConfig(level=logging.INFO)` is hardcoded at line 573. This is the only line to change.
- **`artifacts/developer/telegram_bot/tests/test_bot.py`** — Add tests for the log level configuration logic.

#### Patterns and Conventions

- **Import `os`**: Not currently imported in bot.py — needs to be added to the imports section.
- **Logger**: Use `logger = logging.getLogger(__name__)` already defined at line 30.
- **Startup logging**: The main() function already logs startup info at line 586-587. Add the log level message near there.
- **Validation pattern**: Use `getattr(logging, value, None)` to check validity — returns `None` for invalid level names, which can trigger the fallback.

#### Dependencies and Integration Points

- **`config.py`**: Does NOT need changes — LOG_LEVEL is read directly from `os.environ` in `main()`, not through the config system. This is consistent with the design doc which lists it as an env var, not a YAML config.
- **All other modules**: No changes needed. All modules already use `logging.getLogger(__name__)` which inherits from the root logger configured by `basicConfig`.

#### Implementation Notes

1. **Location**: All changes are in `main()` function of `bot.py`, lines 573-576. Replace:
   ```python
   logging.basicConfig(
       level=logging.INFO,
       format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
   )
   ```
   with logic that reads `LOG_LEVEL` env var, validates it, falls back to INFO, and configures accordingly.

2. **Validation approach**:
   ```python
   import os
   log_level_name = os.environ.get("LOG_LEVEL", "INFO").upper()
   log_level = getattr(logging, log_level_name, None)
   if log_level is None:
       log_level = logging.INFO
       # Warning will be logged after basicConfig is called
   logging.basicConfig(level=log_level, format=...)
   if getattr(logging, log_level_name, None) is None:
       logger.warning("Invalid LOG_LEVEL %s, falling back to INFO", os.environ.get("LOG_LEVEL"))
   logger.info("Log level set to %s", logging.getLevelName(log_level))
   ```

3. **Gotcha — logging before basicConfig**: You cannot log a warning about invalid LOG_LEVEL before calling `basicConfig()` (no handlers configured yet). Call `basicConfig()` first with the fallback level, then log the warning.

4. **Keep it simple**: This is a small, self-contained change. Do not over-engineer.

### Design Context

The bot currently hardcodes `logging.basicConfig(level=logging.INFO)` which means the only way to get DEBUG-level logs (including raw agent stdout) is to edit source code. This is especially painful because turning on DEBUG globally floods the log with Telegram API internals, httpx traffic, and asyncio noise. The LOG_LEVEL env var provides a simple toggle for users to increase verbosity when diagnosing issues. See artifacts/designer/design.md, "Configurable Log Level" subsection under "Diagnostic Logging" and the LOG_LEVEL entry in the Environment Variables table.
