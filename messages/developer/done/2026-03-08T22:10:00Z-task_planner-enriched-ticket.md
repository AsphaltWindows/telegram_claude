# Fix subprocess invocation and implement stream-json protocol for agent sessions

## Metadata
- **From**: task_planner
- **To**: developer
- **Type**: enriched-ticket
- **Created**: 2026-03-08T22:10:00Z

## Requirements

1. Change the subprocess invocation in `SessionManager.start_session()` (session.py, currently lines 337-345) from `claude --agent <name>` to `claude --agent <name> -p --output-format stream-json --input-format stream-json`. This enables non-interactive print mode with structured JSON I/O.

2. Determine whether a permission bypass flag (e.g. `--permission-mode bypassPermissions` or similar) is needed to prevent the headless subprocess from hanging on permission prompts. If needed, add it to the invocation.

3. Update `_read_stdout()` (session.py, currently lines 203-231) to parse each line from stdout as a JSON object instead of treating it as plain text. The method must:
   - Parse each line as JSON
   - Filter for assistant text content events only (ignore tool-use events, system messages, progress indicators, etc.)
   - Aggregate partial message chunks into complete responses before relaying to Telegram via `on_response`
   - Handle malformed JSON lines gracefully (log a warning and skip)

4. Update `Session.send()` (session.py, currently lines 93-112) to format user messages as JSON objects per the `stream-json` input protocol instead of writing raw text to stdin.

5. The exact JSON structures for both input and output must be determined empirically by testing the CLI. The developer should run: `echo '{"type":"user","content":"hello"}' | claude --print --output-format stream-json 2>/dev/null` and inspect the actual output to determine field names, event types, and message structure before implementing the parser.

6. Multi-turn conversation must still work — the `--input-format stream-json` flag should allow multiple user messages to be sent over the session lifetime without the process exiting after the first response.

## QA Steps

1. **Basic relay test**: Start an agent session via Telegram (e.g. `/operator hello`), confirm that a response from the agent appears in Telegram within 30 seconds.

2. **Multi-turn test**: Start a session, send multiple messages in sequence, confirm each message gets a distinct response relayed back.

3. **Empty start test**: Start a session with just `/<agent_name>` (no message), then send a follow-up message — confirm the follow-up triggers a response.

4. **Long response test**: Ask the agent a question that produces a lengthy, multi-line response — confirm the full response is relayed (potentially split via `send_long_message`).

5. **Process lifecycle test**: Start a session, interact, then `/end` — confirm the session shuts down gracefully and the agent's final response is relayed.

6. **No raw JSON leak**: Confirm that the user only sees the agent's text content in Telegram — no raw JSON objects, tool-use events, or system messages should be relayed.

7. **Permission handling**: Confirm the subprocess does not hang on permission prompts (if a bypass flag was added, verify it works).

## Technical Context

### Relevant Files

| File | Path | What needs to change |
|------|------|---------------------|
| **session.py** | `artifacts/developer/telegram_bot/session.py` | **Primary implementation file.** The subprocess invocation (lines 484-497), `send()` (lines 197-226), `_read_stdout()` (lines 318-378), `_extract_text_from_event()` (lines 29-103), and `_extract_text_from_content()` (lines 106-131) have all **already been updated** with the stream-json protocol. The main remaining work is: (a) investigate/add a permission bypass flag, and (b) update tests. |
| **test_session.py** | `artifacts/developer/tests/test_session.py` | **Tests are stale — must be updated.** Multiple test assertions still expect the old raw-text stdin/stdout behavior. See "Implementation Notes" below for specifics. |
| **bot.py** | `artifacts/developer/telegram_bot/bot.py` | No changes needed. The `on_response` callback (line 209) already accepts `(chat_id, text)` which is what `_read_stdout()` will call after extracting text from JSON events. |
| **design.md** | `artifacts/designer/design.md` | Reference only. Sections "Subprocess Invocation" and "Stream-JSON Protocol" describe the expected behavior. |

### Patterns and Conventions

- **JSON encoding for stdin**: `json.dumps({"type": "user", "content": text})` followed by `\n` (newline-delimited). Used in both `send()` (line 222) and `shutdown()` (line 260).
- **JSON parsing for stdout**: Each line is parsed via `_extract_text_from_event()` which handles multiple event shapes: `assistant`, `content_block_delta`, `result`, plus explicit skip list for system/tool events. Non-JSON lines are passed through as-is (line 59).
- **Logger**: `logger = logging.getLogger(__name__)` at line 19. Used throughout for INFO lifecycle events and DEBUG verbose output.
- **Test helpers**: `_make_mock_process()` creates mock processes with configurable stdout/stderr lines. `_make_session()` builds Session objects with sensible defaults.
- **Test pattern for log assertions**: Patch `telegram_bot.session.logger` — see `test_stderr_logged_at_warning_level` (line 170) for the pattern.

### Dependencies and Integration Points

- **`claude` CLI**: Must support `--print --output-format stream-json --input-format stream-json`. The developer should run `claude --help` to verify flag availability and check if a `--permission-mode` or `--dangerously-skip-permissions` flag exists.
- **bot.py `on_response` callback**: Receives `(chat_id, text)` where `text` is the extracted assistant text. No changes needed in bot.py.
- **bot.py `send_long_message`**: Splits text at 4096 chars for Telegram. Works with any string — no JSON awareness needed.

### Implementation Notes

**The core session.py implementation is already done.** The subprocess invocation at lines 484-497 already includes `--print`, `--output-format stream-json`, and `--input-format stream-json`. The `_read_stdout()` method parses JSON events, `send()` formats JSON, and diagnostic logging is in place.

**Remaining work:**

1. **Permission bypass flag (Requirement #2)**: Run `claude --help` and look for flags like `--permission-mode`, `--dangerously-skip-permissions`, or `--no-permissions`. If a suitable flag exists, add it to the `create_subprocess_exec` call at line 484-497. Without this, the headless subprocess may hang on permission prompts since there is no TTY to accept user input.

2. **Update stale tests in `test_session.py`**: The following test assertions are broken because they expect old raw-text behavior:

   - **`test_send_writes_to_stdin` (line 208)**: Asserts `process.stdin.write.assert_called_with(b"Hello agent\n")`. Must change to assert JSON: `b'{"type": "user", "content": "Hello agent"}\n'`.

   - **`test_shutdown_sends_shutdown_message` (line 254)**: Asserts `process.stdin.write.assert_called_with(b"Please exit.\n")`. Must change to assert JSON: `b'{"type": "user", "content": "Please exit."}\n'`.

   - **`test_start_session_spawns_process` (line 488)**: Asserts `args[0][:3] == ("claude", "--agent", "designer")`. Must expand to verify all args including `--print`, `--output-format`, `stream-json`, `--input-format`, `stream-json`.

   - **`test_send_message_forwards_to_session` (line 546)**: Asserts `process.stdin.write.assert_called_with(b"Hello\n")`. Must change to assert JSON.

   - **`test_stdout_lines_invoke_on_response` (lines 137-151)**: Sends raw text lines `b"Hello\n"` and expects `on_response(100, "Hello")`. Now that `_read_stdout()` parses JSON via `_extract_text_from_event()`, the test must send JSON event lines (e.g. `b'{"type":"assistant","message":{"content":[{"type":"text","text":"Hello"}]}}\n'`) or it will only work because non-JSON lines are passed through (line 59). Consider testing both JSON events and non-JSON fallback.

3. **Add new tests for JSON parsing**: Add test cases for `_extract_text_from_event()`:
   - Assistant message event → extracts text
   - `content_block_delta` with `text_delta` → extracts text
   - `result` event with string → extracts text
   - Tool-use/system events → returns `None`
   - Malformed JSON → falls through as raw text
   - Empty/blank lines → skipped

4. **Empirical validation (Requirement #5)**: Before finalizing the parser, the developer should test the actual CLI output format by running:
   ```bash
   echo '{"type":"user","content":"hello"}' | claude --print --output-format stream-json 2>/dev/null
   ```
   Compare the actual event structure against what `_extract_text_from_event()` handles and adjust if needed.

## Design Context

This is the **P0 usability blocker** identified in forum topic `2026-03-08T00:03:00Z-operator-no-agent-responses-after-session-start`. The bot currently spawns `claude --agent <name>` in interactive TUI mode, which produces no usable stdout output when stdin/stdout are pipes. The `readline()` call in `_read_stdout()` blocks forever, making the bot completely non-functional — users never receive agent responses.

The fix changes the invocation to use `-p --output-format stream-json --input-format stream-json` for proper programmatic bidirectional communication, and updates both the output parser and input formatter to work with the JSON protocol.

See `artifacts/designer/design.md`, sections "Subprocess Invocation", "Stream-JSON Protocol", and "Process Management".

**Note:** The core implementation in session.py is already complete. The primary remaining work is (a) investigating the permission bypass flag, and (b) updating the test suite to match the new JSON-based behavior.
