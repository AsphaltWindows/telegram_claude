# Fix stream-json input envelope format — bot crashes on first message

## Metadata
- **From**: task_planner
- **To**: developer
- **Type**: enriched-ticket
- **Created**: 2026-03-08T22:45:00Z

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

## Technical Context

### Relevant Files
- **`artifacts/developer/telegram_bot/session.py`** — Main file to modify. Contains `Session.send()` (line 252) and `Session.shutdown()` (lines 288-296) which construct and write the stream-json input envelope to the subprocess stdin.
- **`artifacts/developer/tests/test_session.py`** — Test file. Contains `test_send_writes_json_to_stdin` (line 423, assertion at line 431), `test_shutdown_sends_json_shutdown_message` (line 468, assertion at line 478), and `test_send_message_forwards_json_to_session` (line 810, assertion at line 831). All test assertions must be updated to match the new envelope format.

### Patterns and Conventions
- The codebase uses `json.dumps()` to construct envelopes, writing them as `envelope.encode() + b"\n"` (newline-delimited JSON / NDJSON) to the subprocess stdin.
- Output parsing in `_extract_text_from_event()` (lines 36-89) already handles a `message` wrapper: it reads `event.get("message", event)` for assistant events with structure `{"type": "assistant", "message": {"content": [...]}}`. The input format should mirror this structure.
- Python 3.7 compatibility is required (see `AsyncMock` shim in tests, `from __future__ import annotations`).
- Tests use `pytest` with `@pytest.mark.asyncio`.

### Dependencies and Integration Points
- The subprocess is spawned by `SessionManager.start_session()` (line ~539) with flags: `--print`, `--verbose`, `--output-format stream-json`, `--input-format stream-json`, `--permission-mode bypassPermissions`.
- The `_extract_text_from_event()` function parses the CLI's **output** and already expects the `{"type": "...", "message": {...}}` envelope shape — the input format should be symmetric.
- The `_stdout_reader()` coroutine (reads subprocess stdout) and `_stderr_reader()` coroutine handle responses and error logging respectively.

### Implementation Notes

**Current state**: The code at lines 252 and 290-291 currently uses `{"message": {"role": "user", "content": text}}`. However, the operator's error logs show the CLI receiving `{"type": "user", "content": "hello"}`, which suggests the deployed version may still have the old format, or this fix was incomplete.

**Correct format (based on research)**: The full `--input-format stream-json` envelope expected by the Claude CLI is:
```json
{"type": "user", "message": {"role": "user", "content": "hello"}, "session_id": "default", "parent_tool_use_id": null}
```

Key fields:
- **`type`**: `"user"` — identifies this as a user input event (top-level discriminator)
- **`message.role`**: `"user"` — the role within the message object (this is what `$.message.role` evaluates)
- **`message.content`**: the text string (may also accept `[{"type": "text", "text": "..."}]` array form)
- **`session_id`**: `"default"` or a UUID — may be optional but included in known working examples
- **`parent_tool_use_id`**: `null` for normal user messages — may be optional

**Recommended approach**:
1. **Test empirically** — run `unset CLAUDECODE && printf '{"type":"user","message":{"role":"user","content":"say hi"}}\n' | timeout 30 claude -p --input-format stream-json --output-format stream-json --verbose 2>&1` to verify the minimal working format. Try with and without `session_id`/`parent_tool_use_id` to determine which fields are required.
2. **Update `send()` at line 252** — change the envelope construction to include at minimum `type` and the `message` wrapper with `role`.
3. **Update `shutdown()` at lines 290-291** — apply the same format change.
4. **Update tests** — update the `expected` JSON in `test_send_writes_json_to_stdin` (line 431), `test_shutdown_sends_json_shutdown_message` (line 478), and `test_send_message_forwards_json_to_session` (line 831).

**Gotcha**: When testing with `claude` CLI from within a Claude Code session, you must `unset CLAUDECODE` first or the CLI will refuse to start (nested session protection).

## Design Context

This is a P0 usability blocker — the bot is completely non-functional because the agent subprocess crashes immediately upon receiving the first user message. The subprocess invocation flags were fixed in a prior iteration, but the input protocol format was not updated to match what `claude --input-format stream-json` actually expects.

See forum topic: forum/open/2026-03-08T22:15:00Z-operator-stream-json-input-format-mismatch.md
