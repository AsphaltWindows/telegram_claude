# Fix stream-json input envelope format — bot crashes on first message

## Metadata
- **From**: product_manager
- **To**: task_planner
- **Type**: ticket
- **Created**: 2026-03-08T22:30:00Z

## Requirements

1. Determine the correct JSON envelope format expected by `claude --input-format stream-json` by empirically testing against the CLI. The current format `{"type": "user", "content": "..."}` causes `TypeError: undefined is not an object (evaluating '$.message.role')`, indicating the CLI expects a `message` object with a `role` field. Test candidates:
   - `{"message": {"role": "user", "content": "hello"}}`
   - `{"role": "user", "content": [{"type": "text", "text": "hello"}]}`
   - Any other format the CLI documentation or error messages suggest.

2. Update `Session.send()` (artifacts/developer/telegram_bot/session.py, line 252) to use the correct envelope format when writing user messages to the agent's stdin.

3. Update `Session.shutdown()` (artifacts/developer/telegram_bot/session.py, lines 290-293) to use the same correct envelope format when sending the shutdown message.

4. Both `send()` and `shutdown()` must use a consistent envelope format — do not fix one without the other.

## QA Steps

1. Start the bot and send a simple text message (e.g., "hello") via Telegram. Verify the agent process does **not** crash with a "Error parsing streaming input line" error in stderr.
2. Verify the agent responds with a valid assistant message after receiving the user message.
3. Trigger a session shutdown (e.g., via idle timeout or explicit command). Verify the shutdown message is sent without errors and the agent process exits cleanly (rc=0).
4. Check the bot logs for any `TypeError` or JSON parsing errors related to stream-json input — there should be none.
5. Send multiple messages in a single session to verify the conversation flow works end-to-end.

## Design Context

This is a P0 usability blocker — the bot is completely non-functional because the agent subprocess crashes immediately upon receiving the first user message. The subprocess invocation flags were fixed in a prior iteration, but the input protocol format was not updated to match what `claude --input-format stream-json` actually expects.

See forum topic: forum/open/2026-03-08T22:15:00Z-operator-stream-json-input-format-mismatch.md
