# configurable-log-level

## Metadata
- **From**: product_manager
- **To**: task_planner

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

### Design Context

The bot currently hardcodes `logging.basicConfig(level=logging.INFO)` which means the only way to get DEBUG-level logs (including raw agent stdout) is to edit source code. This is especially painful because turning on DEBUG globally floods the log with Telegram API internals, httpx traffic, and asyncio noise. The LOG_LEVEL env var provides a simple toggle for users to increase verbosity when diagnosing issues. See artifacts/designer/design.md, "Configurable Log Level" subsection under "Diagnostic Logging" and the LOG_LEVEL entry in the Environment Variables table.
