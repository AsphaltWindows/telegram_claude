# Add auth decorator debug logging and stderr log level fix

## Metadata
- **From**: developer
- **To**: qa
- **Type**: task-complete
- **Created**: 2026-03-09T00:35:00Z

## Summary of Changes

Added DEBUG-level logging to the `auth_required` decorator so rejected users are logged (with their Telegram ID or "unknown" if no effective user). Changed `_read_stderr()` in `Session` to log agent stderr at WARNING level instead of DEBUG, making subprocess errors visible at the default INFO log level.

## Files Changed

- **`artifacts/developer/telegram_bot/bot.py`** — Added `logger.debug(...)` call before the silent return in `auth_required`, logging the rejected user's ID (or "unknown" when `effective_user` is None).
- **`artifacts/developer/telegram_bot/session.py`** — Changed `logger.debug` to `logger.warning` in `_read_stderr()` (line 243).
- **`artifacts/developer/telegram_bot/tests/test_bot.py`** — Added two tests: `test_logs_debug_on_rejected_user` (verifies debug log with user ID) and `test_logs_debug_unknown_when_no_effective_user` (verifies "unknown" fallback).
- **`artifacts/developer/tests/test_session.py`** — Added `test_stderr_logged_at_warning_level` (verifies stderr is logged at WARNING, not DEBUG).

## Requirements Addressed

1. **Auth decorator debug logging**: Implemented. The decorator now logs `"Rejected message from unauthorized user %s"` at DEBUG level with the user ID before returning silently. When `effective_user` is None, "unknown" is used as the ID.
2. **Stderr log level fix**: Implemented. Changed `logger.debug` to `logger.warning` in `_read_stderr()`.
3. **No user-facing response to unauthorized users**: Preserved. The silent-ignore behavior is unchanged; only internal logging was added.

## QA Steps

1. Set logging to `DEBUG` level and send a message from a Telegram user ID not in `allowed_users`. Verify that a debug log line appears containing the rejected user ID.
2. At the default `INFO` log level, verify that no log line appears for rejected users (since the log is at DEBUG).
3. Trigger a session with an agent that writes to stderr. Verify the stderr output appears in bot logs at `WARNING` level without needing to lower the log level to DEBUG.
4. Verify that unauthorized users still receive no Telegram reply.

## Test Coverage

- **`test_logs_debug_on_rejected_user`**: Patches `telegram_bot.bot.logger`, calls auth_required with an unauthorized user ID (999), asserts `logger.debug` was called once with the correct message and user ID.
- **`test_logs_debug_unknown_when_no_effective_user`**: Same pattern but with `effective_user=None`, asserts the fallback `"unknown"` is logged.
- **`test_stderr_logged_at_warning_level`**: Patches `telegram_bot.session.logger`, creates a session with stderr output, asserts `logger.warning` was called with the stderr content and that `logger.debug` was NOT called with it.
- Run all tests: `python -m pytest artifacts/developer/ -v` (77 passed, 1 skipped)

## Notes

- The `block_stdout=True` flag is used in the new session test to prevent the stdout reader from finishing and triggering crash-handling before stderr is processed. This follows the pattern already established in `_make_mock_process`.
- No behavioral changes for end users — unauthorized users still receive no reply. Only internal logging observability is improved.
