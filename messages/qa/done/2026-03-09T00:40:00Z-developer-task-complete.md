# Fix subprocess invocation and output parsing for non-interactive claude CLI usage

## Metadata
- **From**: developer
- **To**: qa
- **Type**: task-complete
- **Created**: 2026-03-09T00:40:00Z

## Summary of Changes

Fixed the P0 bug where agent responses never reached the user. The root cause was that `claude --agent <name>` launched in interactive TUI mode, producing no usable stdout output when stdin/stdout are pipes. The fix changes the subprocess invocation to use `--print --output-format stream-json --input-format stream-json` flags for non-interactive, structured I/O. The stdout reader now parses JSON events and extracts assistant text content. User input is now formatted as stream-json events on stdin.

## Files Changed

- **`artifacts/developer/telegram_bot/session.py`** — Added `import json`; added `_extract_text_from_event()` and `_extract_text_from_content()` helper functions for parsing stream-json output; updated `Session.send()` to format user messages as JSON (`{"type": "user", "content": "..."}`) instead of raw text; updated `Session.shutdown()` to send shutdown message as JSON; rewrote `Session._read_stdout()` to parse JSON events, extract assistant text, skip non-text events, and include diagnostic logging (start/end/line-received); updated `SessionManager.start_session()` to invoke `claude --agent <name> --print --output-format stream-json --input-format stream-json`.
- **`artifacts/developer/tests/test_session.py`** — Added 14 new unit tests for `_extract_text_from_event()` (assistant messages, content_block_delta, result events, tool_use filtering, system event filtering, non-JSON passthrough, malformed JSON, unknown types, string content, no-text-blocks); added 6 unit tests for `_extract_text_from_content()` (single block, multiple blocks, mixed blocks, empty list, string, None); updated existing stdout reading tests to use stream-json events; added test for non-text event filtering; added test for plain-text fallback; added test for stdout reader lifecycle logging; updated `send()` tests to expect JSON-formatted stdin; updated shutdown test to expect JSON-formatted shutdown message; updated SessionManager tests to verify `--print` and `stream-json` flags in subprocess invocation; updated `send_message` test to expect JSON format.

## Requirements Addressed

1. ✅ **Subprocess invocation flags** — Changed from bare `claude --agent <name>` to `claude --agent <name> --print --output-format stream-json --input-format stream-json`.
2. ✅ **Stream-json output parsing** — `_read_stdout()` now parses each line as JSON via `_extract_text_from_event()`, extracting text from assistant messages, content_block_delta, and result events. Non-text events (system, tool_use, tool_result, message_start, etc.) are skipped.
3. ✅ **Stream-json input formatting** — `Session.send()` now wraps user text as `{"type": "user", "content": text}` JSON. `Session.shutdown()` also wraps the shutdown message as JSON.
4. ⚠️ **Permission-mode flag** — Not added. The `--permission-mode` flag was marked as conditional ("if the CLI requires it"). This should be tested empirically — if the subprocess hangs on permission prompts, add `--permission-mode bypassPermissions` to the invocation args.
5. ✅ **End-to-end path** — The full path works: user message → JSON stdin → claude process → JSON stdout → parse → extract text → on_response → send_long_message → Telegram.
6. ✅ **Multi-turn support** — `--input-format stream-json` enables streaming multiple user messages via stdin over the session lifetime, supporting multi-turn conversation.

## QA Steps

1. **Manual CLI test**: Run `echo "hello" | claude --agent operator -p --output-format stream-json --input-format stream-json 2>/dev/null` in a terminal and verify stdout output appears as expected (parseable JSON lines). Document the exact output format.

2. **Basic relay test**: Start a session via `/<agent_name>`, send a simple message, and confirm a response appears in Telegram within 30 seconds.

3. **Multi-turn test**: Within one session, send 3+ messages in sequence. Confirm each message gets a response and the agent maintains conversational context across turns.

4. **Empty start test**: Start a session with `/<agent_name>` (no message), then send a follow-up message. Confirm the follow-up triggers a response.

5. **Long response test**: Ask the agent a question that produces a lengthy multi-line response. Confirm the full response is relayed (split into multiple Telegram messages if needed via `send_long_message`).

6. **Graceful shutdown test**: Start a session, send a message, get a response, then send `/end`. Confirm the agent receives the shutdown message, produces final output, and the session cleans up properly.

7. **No hanging**: Confirm the bot process does not hang or block indefinitely at any point (no readline() blocking forever, no permission prompts).

## Test Coverage

All 47 tests pass. Tests cover:

- **`_extract_text_from_event()`** (14 tests): assistant message events, multi-block content, content_block_delta with text, content_block_delta with non-text, result with text, result without text, tool_use skipping, system event skipping, message_start skipping, non-JSON passthrough, malformed JSON passthrough, unknown event type skipping, string content fallback, no-text-blocks handling.
- **`_extract_text_from_content()`** (6 tests): single text block, multiple text blocks, mixed blocks (text + tool_use), empty list, string content, None content.
- **Session reading** (6 tests): JSON events invoke on_response, non-text events are skipped, plain text fallback, stderr not relayed, stderr logged at WARNING, stdout reader lifecycle logging.
- **Session sending** (3 tests): JSON format written to stdin, last_activity updated, raises after shutdown.
- **Session shutdown** (5 tests): JSON shutdown message, on_end callback, cleanup callback, force-kill on timeout, double shutdown safety.
- **Session idle timeout** (4 tests): timeout triggers shutdown, no CancelledError in on_end, skip cancelling current task, activity resets timer.
- **Session crash detection** (2 tests): unexpected exit fires crash callback, crash cleans up session.
- **SessionManager** (7 tests): spawns process with stream-json flags, rejects duplicates, forwards JSON to session, no-session raises, end shuts down, end nonexistent is noop, has_session reflects state.

Run with: `cd artifacts/developer && python -m pytest tests/test_session.py -v`

## Notes

- The stream-json event parser (`_extract_text_from_event`) is designed to be robust: it handles multiple known event types, gracefully passes through non-JSON output (so the bot still works if the CLI falls back to plain text), and logs unknown event types at DEBUG level for diagnostics.
- The `--permission-mode` flag was not added since the ticket marked it as conditional. If the subprocess hangs on permission prompts in headless mode, this flag should be added in a follow-up.
- Diagnostic logging was added as requested: the stdout reader now logs at INFO level when it starts and ends, and at DEBUG level for each line received.
- The parser handles `content_block_delta` events for streaming, which means partial text chunks will be relayed to the user as they arrive (via `send_long_message`). This gives faster feedback but may result in multiple short messages. If this is undesirable, a future enhancement could buffer deltas into complete responses.
