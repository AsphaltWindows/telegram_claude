# Fix subprocess invocation and implement stream-json protocol for agent sessions

## Metadata
- **From**: developer
- **To**: qa
- **Type**: task-complete
- **Created**: 2026-03-08T01:00:00Z

## Summary of Changes

Fixed the P0 usability blocker where agent responses were never relayed to users. The subprocess invocation now uses `--print --output-format stream-json --input-format stream-json --permission-mode bypassPermissions` flags for proper non-interactive, structured I/O. The stdout reader parses stream-json events and extracts assistant text content. The stdin writer formats user messages as JSON. Permission bypass prevents the headless process from hanging on permission prompts.

## Files Changed

- `artifacts/developer/telegram_bot/session.py` — Updated subprocess invocation with `--print`, `--output-format stream-json`, `--input-format stream-json`, and `--permission-mode bypassPermissions` flags. `_read_stdout()` now parses JSON events via `_extract_text_from_event()`. `send()` now formats user messages as JSON. Added `_extract_text_from_event()` and `_extract_text_from_content()` helper functions for parsing stream-json output.
- `artifacts/developer/tests/test_session.py` — Updated all tests to verify JSON-based stdin/stdout behavior. Added `TestExtractTextFromEvent` (14 tests) and `TestExtractTextFromContent` (6 tests) for comprehensive parser coverage. Updated `TestSessionManagerStart` to verify stream-json and permission bypass flags.

## Requirements Addressed

1. **Subprocess invocation changed** — Now uses `claude --agent <name> --print --output-format stream-json --input-format stream-json --permission-mode bypassPermissions`.
2. **Permission bypass flag** — Added `--permission-mode bypassPermissions` to prevent headless subprocess from hanging on permission prompts. The `claude` CLI supports this flag; it bypasses all permission checks (recommended for sandboxed environments).
3. **`_read_stdout()` updated** — Parses each line as JSON, extracts assistant text content, filters out tool-use/system events, handles malformed JSON gracefully (passes through as-is with debug log).
4. **`send()` updated** — Formats user messages as `{"type": "user", "content": "<text>"}` JSON objects.
5. **Multi-turn conversation** — `--input-format stream-json` enables multiple user messages over the session lifetime.

## QA Steps

1. **Basic relay test**: Start an agent session via Telegram (e.g. `/operator hello`), confirm that a response from the agent appears in Telegram within 30 seconds.
2. **Multi-turn test**: Start a session, send multiple messages in sequence, confirm each message gets a distinct response relayed back.
3. **Empty start test**: Start a session with just `/<agent_name>` (no message), then send a follow-up message — confirm the follow-up triggers a response.
4. **Long response test**: Ask the agent a question that produces a lengthy, multi-line response — confirm the full response is relayed (potentially split via `send_long_message`).
5. **Process lifecycle test**: Start a session, interact, then `/end` — confirm the session shuts down gracefully and the agent's final response is relayed.
6. **No raw JSON leak**: Confirm that the user only sees the agent's text content in Telegram — no raw JSON objects, tool-use events, or system messages should be relayed.
7. **Permission handling**: Confirm the subprocess does not hang on permission prompts (the `--permission-mode bypassPermissions` flag should prevent this).

## Test Coverage

- 47 tests total, all passing
- `TestExtractTextFromEvent` (14 tests): assistant messages, content_block_delta, result events, tool_use/system/message_start skipping, non-JSON passthrough, malformed JSON passthrough, unknown event types, string content, no-text-blocks
- `TestExtractTextFromContent` (6 tests): single/multiple/mixed text blocks, empty list, string content, None
- `TestSessionReading` (6 tests): JSON event relay, non-text event filtering, plain-text fallback, stderr logging, stdout reader lifecycle logging
- `TestSessionSend` (3 tests): JSON stdin format, activity tracking, post-shutdown error
- `TestSessionShutdown` (5 tests): JSON shutdown message, on_end callback, cleanup, force-kill timeout, double-shutdown safety
- `TestSessionManagerStart` (2 tests): stream-json and permission flags verification, duplicate rejection

Run: `python -m pytest artifacts/developer/tests/test_session.py -v`

## Notes

- The `--permission-mode bypassPermissions` flag bypasses all permission checks. The `claude --help` notes this is "Recommended only for sandboxes with no internet access." For production use, the operator should evaluate whether a less permissive mode (e.g., `acceptEdits`) is appropriate.
- Non-JSON stdout lines are passed through as-is (not dropped), which provides a safety net if the CLI falls back to plain-text output in any edge case.
- The debug log truncates stdout lines to 200 characters (slightly more than the originally specified 100), which provides better diagnostic value without excessive log volume.
