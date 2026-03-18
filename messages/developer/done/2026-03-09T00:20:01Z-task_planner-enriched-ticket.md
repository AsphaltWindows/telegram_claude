# Add session-start confirmation message

## Metadata
- **From**: task_planner
- **To**: developer
- **Type**: enriched-ticket
- **Created**: 2026-03-09T00:20:01Z

## Requirements

1. In `telegram_bot/bot.py`, the `agent_command_handler` must send an immediate confirmation message to the user after `start_session()` returns successfully, before forwarding any first message to the agent.
2. The confirmation message text must be: "Starting session with `<agent_name>`…" (using the actual agent name, with backtick formatting around the agent name).
3. This confirmation must be sent regardless of whether the user included a first message with the command.

## QA Steps

1. Send `/<agent_name>` (without a message) in Telegram. Verify the bot immediately replies with "Starting session with `<agent_name>`…" before any agent output appears.
2. Send `/<agent_name> hello` (with a first message) in Telegram. Verify the confirmation message appears before the agent's response to "hello".
3. Verify the confirmation message uses the correct agent name matching what the user typed.
4. Verify that if `start_session()` fails (e.g., agent not found), no confirmation message is sent (the error path should handle this separately).

## Technical Context

### Relevant Files
- **`artifacts/developer/telegram_bot/bot.py`** — Contains `agent_command_handler` (lines 166-232). The `start_session()` call is at lines 223-228. The confirmation message must be inserted between the `start_session()` return (line 228) and the first message forward (lines 230-232).
- **`artifacts/developer/telegram_bot/tests/test_bot.py`** — Contains `TestAgentCommandHandler` (lines 251-314). Tests use `_make_update()`, `_make_context()`, `_make_session_manager()` helpers. The mock session manager's `start_session` returns an `AsyncMock`.

### Patterns and Conventions
- Messages to users are sent via `update.message.reply_text()` (for direct replies) or `bot.send_message()` (for async callbacks).
- The `bot` instance is extracted from `context.bot` (line 205).
- Backtick formatting in Telegram messages: the requirement says backtick formatting around the agent name. Since the bot uses `reply_text()` without `parse_mode`, backticks will appear as literal characters in plain text mode. If MarkdownV2 formatting is desired, use the `send_with_markdown_fallback()` helper — but the simpler approach is `reply_text()` with literal backticks (consistent with the error messages at lines 190-193, 199-201 which also use plain `reply_text`).
- Test assertions check the reply text via `update.message.reply_text.call_args[0][0]`.

### Dependencies and Integration Points
- The `start_session()` method (in `SessionManager`, session.py line 302) can raise `ValueError` if a session already exists, but this is already guarded by the `has_session()` check at line 188.
- The confirmation message should use `update.message.reply_text()` for consistency with other handler messages.
- Note: Ticket 3 (spawn failure handling) adds a try/except around `start_session()`. If both tickets are implemented, the confirmation must come AFTER the try/except succeeds, not inside the try block before the call.

### Implementation Notes
1. **Insert confirmation after start_session (bot.py, after line 228)**:
   ```python
   session = await session_manager.start_session(
       chat_id=chat_id,
       agent_name=agent_name,
       on_response=on_response,
       on_end=on_end,
   )

   # Send confirmation to user.
   await update.message.reply_text(
       f"Starting session with `{agent_name}`…"
   )

   # Forward the first message if provided.
   if first_message:
       await session.send(first_message)
   ```
2. **Tests**: Add tests in `TestAgentCommandHandler`:
   - Test that `reply_text` is called with the confirmation message containing the agent name after a successful start.
   - Test that `reply_text` is called BEFORE `session.send()` (ordering check).
   - Test that confirmation appears both with and without a first message.
3. **Ordering concern**: The `reply_text` for confirmation must happen before `session.send()` to ensure the user sees confirmation before agent output. Since both are `await`ed sequentially, this is guaranteed.

## Design Context

Users reported the bot appearing unresponsive because there was no feedback between sending a command and receiving the agent's first output, which can take several seconds. The design now requires an immediate confirmation message as step 4 in the "Starting a Session" flow. See artifacts/designer/design.md, "Starting a Session" step 4.
