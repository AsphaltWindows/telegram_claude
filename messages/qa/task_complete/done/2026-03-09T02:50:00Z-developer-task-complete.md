# Fix stream-json input envelope format — bot crashes on first message

## Metadata
- **From**: developer
- **To**: qa
- **Type**: task-complete
- **Created**: 2026-03-09T02:50:00Z

## Summary of Changes

Added the top-level `"type": "user"` field to the stream-json input envelope sent to the Claude CLI subprocess. The CLI expects `{"type": "user", "message": {"role": "user", "content": "..."}}` but the code was sending `{"message": {"role": "user", "content": "..."}}` (missing the `type` discriminator). This caused the CLI to crash with `TypeError: undefined is not an object (evaluating '$.message.role')` because the top-level `type` field is used as a discriminator before accessing `message.role`.

## Files Changed

- **`artifacts/developer/telegram_bot/session.py`** — Updated `Session.send()` (line 252) and `Session.shutdown()` (lines 290-293) envelope construction to include `"type": "user"` at the top level. Updated docstring in `send()` to reflect the correct format.
- **`artifacts/developer/tests/test_session.py`** — Updated expected JSON assertions in `test_send_writes_json_to_stdin` (line 431), `test_shutdown_sends_json_shutdown_message` (line 478), and `test_send_message_forwards_json_to_session` (line 831) to match the corrected envelope format.

## Requirements Addressed

1. **Correct envelope format** — The envelope now includes `"type": "user"` at the top level alongside the `"message"` wrapper with `"role": "user"`, matching what `claude --input-format stream-json` expects.
2. **Updated `Session.send()`** — Line 252 now produces `{"type": "user", "message": {"role": "user", "content": "<text>"}}`.
3. **Updated `Session.shutdown()`** — Lines 290-293 now produce the same correct envelope format for the shutdown message.
4. **Consistent format** — Both `send()` and `shutdown()` use the identical envelope structure.

## QA Steps

1. Start the bot and send a simple text message (e.g., "hello") via Telegram. Verify the agent process does **not** crash with a "Error parsing streaming input line" error in stderr.
2. Verify the agent responds with a valid assistant message after receiving the user message.
3. Trigger a session shutdown (e.g., via idle timeout or explicit command). Verify the shutdown message is sent without errors and the agent process exits cleanly (rc=0).
4. Check the bot logs for any `TypeError` or JSON parsing errors related to stream-json input — there should be none.
5. Send multiple messages in a single session to verify the conversation flow works end-to-end.

## Test Coverage

All 55 existing tests pass. Three test assertions were updated to verify the corrected envelope format:

- `test_send_writes_json_to_stdin` — Verifies `send()` writes `{"type": "user", "message": {"role": "user", "content": "Hello agent"}}` to stdin.
- `test_shutdown_sends_json_shutdown_message` — Verifies `shutdown()` writes `{"type": "user", "message": {"role": "user", "content": "Please exit."}}` to stdin.
- `test_send_message_forwards_json_to_session` — Verifies `SessionManager.send_message()` forwards the correct envelope format.

Run tests with: `cd artifacts/developer && python -m pytest tests/test_session.py -v`

## Notes

- The fix adds `"type": "user"` to the envelope. The `session_id` and `parent_tool_use_id` fields mentioned in the enriched ticket as potentially needed were omitted — the minimal format with `type` and `message.role` should resolve the `$.message.role` evaluation error. If the CLI requires those additional fields, a follow-up fix would be needed, but the error message specifically points to `$.message.role` which is now present.
- The "pending tasks destroyed" warnings in test output are benign — they come from tests that use `block_stdout=True` where background tasks are intentionally left running when the test completes.
