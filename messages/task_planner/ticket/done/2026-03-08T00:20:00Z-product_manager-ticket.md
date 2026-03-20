# Add auth decorator debug logging and stderr log level fix

## Metadata
- **From**: product_manager
- **To**: task_planner
- **Type**: ticket
- **Created**: 2026-03-08T00:20:00Z

## Requirements

1. In `telegram_bot/bot.py`, the `auth_required` decorator must log a `DEBUG`-level message including the rejected user's Telegram ID before returning silently. Example: `logger.debug("Rejected message from unauthorized user %s", user_id)`.
2. In `telegram_bot/session.py`, the `_read_stderr()` method must log agent stderr output at `WARNING` level instead of `DEBUG` level.
3. No user-facing response should be sent to unauthorized users — the silent-ignore behavior is by design.

## QA Steps

1. Set logging to `DEBUG` level and send a message from a Telegram user ID not in `allowed_users`. Verify that a debug log line appears containing the rejected user ID.
2. At the default `INFO` log level, verify that no log line appears for rejected users (since the log is at DEBUG).
3. Trigger a session with an agent that writes to stderr. Verify the stderr output appears in bot logs at `WARNING` level without needing to lower the log level to DEBUG.
4. Verify that unauthorized users still receive no Telegram reply.

## Design Context

The operator reported the bot not responding to messages. Investigation revealed that the `auth_required` decorator silently drops messages with zero logging, making it impossible to diagnose auth-related issues. Additionally, agent stderr is logged at DEBUG level, which is invisible at the default INFO log level. These changes improve operational observability without changing user-facing behavior for auth, and ensure subprocess errors are visible in logs. See artifacts/designer/design.md, "Error Cases" table (Unauthorized user row) and "Technical Design > Process Management" (stderr logging).
