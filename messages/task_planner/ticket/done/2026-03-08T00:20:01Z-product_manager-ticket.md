# Add session-start confirmation message

## Metadata
- **From**: product_manager
- **To**: task_planner
- **Type**: ticket
- **Created**: 2026-03-08T00:20:01Z

## Requirements

1. In `telegram_bot/bot.py`, the `agent_command_handler` must send an immediate confirmation message to the user after `start_session()` returns successfully, before forwarding any first message to the agent.
2. The confirmation message text must be: "Starting session with `<agent_name>`…" (using the actual agent name, with backtick formatting around the agent name).
3. This confirmation must be sent regardless of whether the user included a first message with the command.

## QA Steps

1. Send `/<agent_name>` (without a message) in Telegram. Verify the bot immediately replies with "Starting session with `<agent_name>`…" before any agent output appears.
2. Send `/<agent_name> hello` (with a first message) in Telegram. Verify the confirmation message appears before the agent's response to "hello".
3. Verify the confirmation message uses the correct agent name matching what the user typed.
4. Verify that if `start_session()` fails (e.g., agent not found), no confirmation message is sent (the error path should handle this separately).

## Design Context

Users reported the bot appearing unresponsive because there was no feedback between sending a command and receiving the agent's first output, which can take several seconds. The design now requires an immediate confirmation message as step 4 in the "Starting a Session" flow. See artifacts/designer/design.md, "Starting a Session" step 4.
