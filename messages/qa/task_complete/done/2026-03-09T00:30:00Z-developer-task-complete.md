# Add error handling for agent process spawn failure

## Metadata
- **From**: developer
- **To**: qa
- **Type**: task-complete
- **Created**: 2026-03-09T00:30:00Z

## Summary of Changes

Added try/except error handling around the `start_session()` call in `agent_command_handler` in `bot.py`. When the subprocess spawn fails (e.g., `claude` binary not on PATH), the bot now replies with a clear error message and logs the failure. Two except blocks handle expected OS errors (`FileNotFoundError`, `OSError`) with `logger.error`, and unexpected exceptions with `logger.exception` (includes traceback). Added 5 new tests covering all spawn failure scenarios.

## Files Changed

- **`artifacts/developer/telegram_bot/bot.py`** — Wrapped `start_session()` call in try/except with two blocks: one for `FileNotFoundError`/`OSError` (logged with `logger.error`), one catch-all for unexpected exceptions (logged with `logger.exception`). Both send user-facing error reply and return early.
- **`artifacts/developer/telegram_bot/tests/test_bot.py`** — Added 5 new tests to `TestAgentCommandHandler`: `test_spawn_failure_file_not_found`, `test_spawn_failure_os_error`, `test_spawn_failure_unexpected_exception`, `test_spawn_failure_no_session_left_behind`, `test_spawn_failure_no_first_message_sent`.

## Requirements Addressed

1. **try/except around start_session()** — Implemented with two except blocks catching `FileNotFoundError`/`OSError` and generic `Exception`.
2. **User-facing error reply** — On spawn failure, replies with: "Failed to start session with `<agent_name>`. Check that `claude` is installed and available."
3. **No session state left behind** — Confirmed: `start_session()` only adds to `_sessions` after successful subprocess spawn, so no cleanup needed. Handler returns early. Verified by test.
4. **Logging at WARNING/ERROR level** — Expected OS errors logged with `logger.error`; unexpected exceptions logged with `logger.exception` (ERROR level with traceback).

## QA Steps

1. Temporarily rename or remove the `claude` binary from PATH. Send `/<agent_name>` in Telegram. Verify the bot replies with the spawn failure error message.
2. Verify that after a spawn failure, no session is left active — sending another `/<agent_name>` command should attempt to start a new session, not report an existing session.
3. Verify the spawn failure is logged with exception details at WARNING or ERROR level.
4. Restore `claude` to PATH and verify normal session start still works correctly.

## Test Coverage

5 new tests added to `TestAgentCommandHandler` in `test_bot.py`:

- **`test_spawn_failure_file_not_found`** — Mocks `start_session` raising `FileNotFoundError`, verifies error reply and `logger.error` call.
- **`test_spawn_failure_os_error`** — Same for `OSError`.
- **`test_spawn_failure_unexpected_exception`** — Mocks `RuntimeError`, verifies error reply and `logger.exception` call (traceback logging).
- **`test_spawn_failure_no_session_left_behind`** — Verifies `has_session` returns False after failure.
- **`test_spawn_failure_no_first_message_sent`** — Verifies no confirmation or first message is sent on failure, only the error reply (exactly 1 reply_text call).

Run with: `cd artifacts/developer && python -m pytest telegram_bot/tests/test_bot.py -v`

All 36 tests pass (30 existing + 6 new... correction: 5 new, total 36 including the pre-existing suite which had 31 tests).

## Notes

- The confirmation message ("Starting session with ...") is only sent AFTER a successful `start_session()` call, ensuring it's never sent on failure.
- Two separate except blocks are used: `(FileNotFoundError, OSError)` for expected subprocess errors (logged with `logger.error`), and a catch-all `Exception` for unexpected errors (logged with `logger.exception` to include full traceback). Both send the same user-facing message.
- No changes to `session.py` were needed — the session state is clean on spawn failure since `_sessions[chat_id]` is only assigned after successful subprocess creation.
