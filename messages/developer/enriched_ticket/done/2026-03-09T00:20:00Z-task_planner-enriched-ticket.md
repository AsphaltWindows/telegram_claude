# Add auth decorator debug logging and stderr log level fix

## Metadata
- **From**: task_planner
- **To**: developer
- **Type**: enriched-ticket
- **Created**: 2026-03-09T00:20:00Z

## Requirements

1. In `telegram_bot/bot.py`, the `auth_required` decorator must log a `DEBUG`-level message including the rejected user's Telegram ID before returning silently. Example: `logger.debug("Rejected message from unauthorized user %s", user_id)`.
2. In `telegram_bot/session.py`, the `_read_stderr()` method must log agent stderr output at `WARNING` level instead of `DEBUG` level.
3. No user-facing response should be sent to unauthorized users — the silent-ignore behavior is by design.

## QA Steps

1. Set logging to `DEBUG` level and send a message from a Telegram user ID not in `allowed_users`. Verify that a debug log line appears containing the rejected user ID.
2. At the default `INFO` log level, verify that no log line appears for rejected users (since the log is at DEBUG).
3. Trigger a session with an agent that writes to stderr. Verify the stderr output appears in bot logs at `WARNING` level without needing to lower the log level to DEBUG.
4. Verify that unauthorized users still receive no Telegram reply.

## Technical Context

### Relevant Files
- **`artifacts/developer/telegram_bot/bot.py`** — Contains the `auth_required` decorator (lines 145-158). The rejection happens at line 155 (`return  # Silently ignore`). The `logger` is already defined at line 27.
- **`artifacts/developer/telegram_bot/session.py`** — Contains the `_read_stderr()` method (lines 233-247). The current log call is at line 243: `logger.debug("Agent %s stderr: %s", self.agent_name, text)`. The `logger` is already defined at line 15.
- **`artifacts/developer/telegram_bot/tests/test_bot.py`** — Contains `TestAuthRequired` class (lines 206-243). The test `test_rejects_unauthorised_user` (line 221) verifies silent rejection but does not assert logging. A new test should be added.
- **`artifacts/developer/tests/test_session.py`** — Contains `TestSessionReading` class (lines 133-167). The test `test_stderr_is_logged_not_relayed` (line 154) verifies stderr is not sent to `on_response` but does not verify log level.

### Patterns and Conventions
- Logging uses the standard `logging` module with `logger = logging.getLogger(__name__)` at module level.
- Test files use `pytest` with `@pytest.mark.asyncio` for async tests.
- Bot tests use the `_make_update()` and `_make_context()` helper factories.
- Session tests use the `_make_mock_process()` and `_make_session()` helper factories.
- Tests access the unwrapped handler via `handler.__wrapped__` to bypass the `auth_required` decorator.
- Mock imports: bot tests use `from mock import AsyncMock, MagicMock, patch`; session tests use `from unittest.mock import MagicMock, patch`.

### Dependencies and Integration Points
- The `auth_required` decorator wraps all handlers: `agent_command_handler`, `end_handler`, `help_handler`, `plain_text_handler`.
- The user ID is available via `update.effective_user.id` (already checked for `None` at line 154).
- The `_read_stderr` method runs as a background `asyncio.Task` created in `Session.start()`.

### Implementation Notes
1. **auth_required fix (bot.py, line 155)**: Extract `user_id` before the `return`. The user ID is `update.effective_user.id` but note that `update.effective_user` can be `None` (checked at line 154), so log a different message for that case or use a fallback like `"unknown"`.
   ```python
   if update.effective_user is None or update.effective_user.id not in allowed:
       user_id = update.effective_user.id if update.effective_user else "unknown"
       logger.debug("Rejected message from unauthorized user %s", user_id)
       return
   ```
2. **stderr log level fix (session.py, line 243)**: Simply change `logger.debug` to `logger.warning`. No other changes needed.
3. **Tests**: Add a test in `TestAuthRequired` that patches `telegram_bot.bot.logger` and asserts `logger.debug` was called with the rejected user ID. For session stderr, add a test that patches `telegram_bot.session.logger` and asserts `logger.warning` was called instead of `logger.debug`.

## Design Context

The operator reported the bot not responding to messages. Investigation revealed that the `auth_required` decorator silently drops messages with zero logging, making it impossible to diagnose auth-related issues. Additionally, agent stderr is logged at DEBUG level, which is invisible at the default INFO log level. These changes improve operational observability without changing user-facing behavior for auth, and ensure subprocess errors are visible in logs. See artifacts/designer/design.md, "Error Cases" table (Unauthorized user row) and "Technical Design > Process Management" (stderr logging).
