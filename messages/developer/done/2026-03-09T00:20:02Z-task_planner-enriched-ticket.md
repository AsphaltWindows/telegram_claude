# Add error handling for agent process spawn failure

## Metadata
- **From**: task_planner
- **To**: developer
- **Type**: enriched-ticket
- **Created**: 2026-03-09T00:20:02Z

## Requirements

1. In `telegram_bot/bot.py`, the `agent_command_handler` must wrap the `start_session()` call in a try/except block to catch `FileNotFoundError`, `OSError`, and any other exceptions from subprocess creation.
2. On spawn failure, the bot must reply to the user with: "Failed to start session with `<agent_name>`. Check that `claude` is installed and available."
3. On spawn failure, no session state should be left behind — the session should be fully cleaned up.
4. The spawn failure should be logged at `WARNING` or `ERROR` level with the exception details.

## QA Steps

1. Temporarily rename or remove the `claude` binary from PATH. Send `/<agent_name>` in Telegram. Verify the bot replies with the spawn failure error message.
2. Verify that after a spawn failure, no session is left active — sending another `/<agent_name>` command should attempt to start a new session, not report an existing session.
3. Verify the spawn failure is logged with exception details at WARNING or ERROR level.
4. Restore `claude` to PATH and verify normal session start still works correctly.

## Technical Context

### Relevant Files
- **`artifacts/developer/telegram_bot/bot.py`** — Contains `agent_command_handler` (lines 166-232). The `start_session()` call is at lines 223-228. This is the call that needs to be wrapped in try/except.
- **`artifacts/developer/telegram_bot/session.py`** — Contains `SessionManager.start_session()` (lines 302-366). The subprocess spawn is at lines 337-345: `asyncio.create_subprocess_exec("claude", "--agent", agent_name, ...)`. This is where `FileNotFoundError` or `OSError` would be raised if the binary is not found.
- **`artifacts/developer/telegram_bot/tests/test_bot.py`** — Contains `TestAgentCommandHandler` (lines 251-314). New tests should follow the same pattern using `_make_session_manager()`.
- **`artifacts/developer/tests/test_session.py`** — Contains `TestSessionManagerStart` (lines 440-495). Tests use `patch("telegram_bot.session.asyncio.create_subprocess_exec", ...)`.

### Patterns and Conventions
- Error messages to users use `update.message.reply_text()` (see lines 190-193, 199-201).
- Logging uses `logger.warning()` or `logger.exception()` for error conditions (see session.py line 171 for `logger.warning` pattern, bot.py line 220 for `logger.exception` pattern).
- The `logger` is already defined at bot.py line 27.

### Dependencies and Integration Points
- **Session cleanup on spawn failure**: If `start_session()` raises during `create_subprocess_exec`, the session is NOT added to `self._sessions` (the `self._sessions[chat_id] = session` assignment at session.py line 357 happens AFTER the subprocess spawn). So no cleanup of session state is needed in the handler — the `SessionManager` is already in a clean state.
- **Interaction with Ticket 2 (confirmation message)**: If both tickets are implemented, the confirmation message must only be sent on SUCCESS, not inside the try block before the potentially-failing call. The error reply in the except block replaces the confirmation.

### Implementation Notes
1. **Wrap start_session in try/except (bot.py, lines 222-228)**:
   ```python
   try:
       session = await session_manager.start_session(
           chat_id=chat_id,
           agent_name=agent_name,
           on_response=on_response,
           on_end=on_end,
       )
   except (FileNotFoundError, OSError) as exc:
       logger.error(
           "Failed to start session with agent '%s' for chat %d: %s",
           agent_name, chat_id, exc,
       )
       await update.message.reply_text(
           f"Failed to start session with `{agent_name}`. "
           f"Check that `claude` is installed and available."
       )
       return
   except Exception as exc:
       logger.exception(
           "Unexpected error starting session with agent '%s' for chat %d.",
           agent_name, chat_id,
       )
       await update.message.reply_text(
           f"Failed to start session with `{agent_name}`. "
           f"Check that `claude` is installed and available."
       )
       return
   ```
   Note: Two except blocks — one for expected subprocess errors (logged with `logger.error`), one catch-all for unexpected errors (logged with `logger.exception` to include traceback).

2. **Tests in test_bot.py**: Add tests to `TestAgentCommandHandler`:
   - Mock `sm.start_session` to raise `FileNotFoundError` → assert `reply_text` called with error message, assert `session.send` not called.
   - Mock `sm.start_session` to raise `OSError` → same assertions.
   - Verify no session state leaks (check `sm.has_session` returns False after failure).

3. **No session.py changes needed**: The spawn failure occurs before the session is registered in `_sessions`, so no cleanup logic is required in `SessionManager`.

## Design Context

The `start_session()` method calls `create_subprocess_exec('claude', ...)` without error handling. If the `claude` binary is not on PATH or fails to start, the exception propagates unhandled and the user gets no feedback. The design now includes a spawn failure error case in the Error Cases table. See artifacts/designer/design.md, "Error Cases" table (Agent process fails to spawn row).
