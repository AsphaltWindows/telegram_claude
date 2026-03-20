# Fix subprocess invocation and output parsing for non-interactive claude CLI usage

## Metadata
- **From**: task_planner
- **To**: developer
- **Type**: enriched-ticket
- **Created**: 2026-03-09T00:35:00Z

## Requirements

1. Change the subprocess invocation in `SessionManager.start_session()` (session.py, lines ~337-345) from `claude --agent <name>` to use the correct CLI flags for non-interactive piped mode. At minimum, add `--print` (`-p`) which is required for stdout output when stdin/stdout are pipes. Determine the correct output-format flag (e.g., `--output-format stream-json`, `--output-format text`, or similar) by testing the CLI.

2. If `--output-format stream-json` (or similar structured format) is used, update `_read_stdout()` (session.py, lines ~203-231) to parse the structured output. Extract only the assistant's text content from JSON events, filtering out tool-use events, system messages, and other non-text events. Aggregate partial message chunks into complete responses before relaying to Telegram.

3. If `--input-format stream-json` is used for multi-turn support, update `Session.send()` (session.py, lines ~93-112) to format user messages as JSON objects matching the expected input protocol, rather than sending raw text.

4. If the CLI requires it, add a permission-mode flag (e.g., `--permission-mode bypassPermissions` or equivalent) to prevent the subprocess from hanging on interactive permission prompts in headless mode.

5. After the fix, the end-to-end path must work: user sends message in Telegram -> bot writes to stdin -> claude process produces output on stdout -> `_read_stdout()` reads and parses it -> response is relayed to Telegram via `send_long_message()`.

6. The fix must support multi-turn conversation within a single session (not just single-shot prompt-response), since sessions are long-lived until `/end` or idle timeout.

## QA Steps

1. **Manual CLI test**: Run `echo "hello" | claude --agent operator -p [flags]` in a terminal and verify stdout output appears as expected (text or parseable JSON lines). Document the exact flags used.

2. **Basic relay test**: Start a session via `/<agent_name>`, send a simple message, and confirm a response appears in Telegram within 30 seconds.

3. **Multi-turn test**: Within one session, send 3+ messages in sequence. Confirm each message gets a response and the agent maintains conversational context across turns.

4. **Empty start test**: Start a session with `/<agent_name>` (no message), then send a follow-up message. Confirm the follow-up triggers a response.

5. **Long response test**: Ask the agent a question that produces a lengthy multi-line response. Confirm the full response is relayed (split into multiple Telegram messages if needed via `send_long_message`).

6. **Graceful shutdown test**: Start a session, send a message, get a response, then send `/end`. Confirm the agent receives the shutdown message, produces final output, and the session cleans up properly.

7. **No hanging**: Confirm the bot process does not hang or block indefinitely at any point (no readline() blocking forever, no permission prompts).

## Technical Context

### Relevant Files

| File | Path | Why |
|------|------|-----|
| **session.py** | `artifacts/developer/telegram_bot/session.py` | **Primary file to modify.** Contains `SessionManager.start_session()` (subprocess invocation, lines 337-345), `Session.send()` (stdin writing, lines 93-112), `Session._read_stdout()` (stdout parsing, lines 203-231), and `Session.shutdown()` (graceful exit, lines 114-158). |
| **bot.py** | `artifacts/developer/telegram_bot/bot.py` | Contains `send_long_message()` (lines 120-137) which is the downstream consumer of `on_response` output. Also contains `agent_command_handler()` (lines 168-261) which wires up the `on_response` and `on_end` callbacks. Review to understand how parsed output flows to Telegram. |
| **test_session.py** | `artifacts/developer/tests/test_session.py` | **Must update.** Existing tests mock `create_subprocess_exec` and assert `args[0][:3] == ("claude", "--agent", "designer")` (line 488). This assertion will break when new CLI flags are added. Also, `Session.send()` tests assert `process.stdin.write.assert_called_with(b"Hello agent\n")` (line 208) — will need updating if send() switches to JSON format. The `_make_mock_process` helper (lines 40-98) produces plain byte lines for stdout — will need updating to produce JSON events if the parser changes. |
| **config.py** | `artifacts/developer/telegram_bot/config.py` | `BotConfig` and `_DEFAULT_SHUTDOWN_MESSAGE` (line 22-24). The shutdown message is sent raw via `stdin.write()` in `Session.shutdown()` (line 146-148). If stdin switches to stream-json format, the shutdown message may also need to be sent as a JSON object. |

### Patterns and Conventions

- **Logging**: The module uses `logger = logging.getLogger(__name__)` at module level (line 15). Follow existing patterns: `logger.info()` for lifecycle events, `logger.warning()` for unexpected conditions, `logger.debug()` for verbose data, `logger.exception()` for caught exceptions.
- **Async patterns**: All I/O methods are `async`. Background tasks are created via `asyncio.create_task()` and stored as instance attributes. Tasks check for `asyncio.CancelledError` and return gracefully.
- **Error handling**: The `_read_stdout()` method wraps the `on_response` callback in try/except (lines 214-217). Follow this pattern for any new parsing logic — log and continue rather than crashing the reader.
- **Type hints**: Module uses `from __future__ import annotations` and provides type hints on all public methods.
- **Docstrings**: All public methods and classes have numpy-style docstrings.
- **Constants**: Module-level constants use `_UPPER_SNAKE_CASE` with leading underscore (e.g., `_SHUTDOWN_TIMEOUT`).
- **Testing**: Tests use `pytest` with `@pytest.mark.asyncio`. Mock processes are built via the `_make_mock_process()` helper. The `block_stdout=True` pattern is used to prevent the stdout reader from detecting process exit during tests that need the session alive.

### Dependencies and Integration Points

1. **`claude` CLI** — The subprocess. Must be invoked with correct flags. Key flags from the forum discussion: `--print` (non-interactive mode), `--output-format stream-json` (structured JSON output), `--input-format stream-json` (JSON input for multi-turn), `--verbose` (may be needed for diagnostics).
2. **`json` stdlib module** — Will need to be imported for parsing stream-json output in `_read_stdout()`.
3. **`send_long_message()` in bot.py** — The `on_response` callback (defined in `agent_command_handler()`, line 209-210) calls this with `(bot, chat_id, text)`. The text passed must be a plain string (not JSON). So `_read_stdout()` must extract the text content from JSON events before calling `on_response`.
4. **`Session.shutdown()` → stdin** — Lines 146-148 write the shutdown message as raw bytes. If stdin expects stream-json format, this needs to be wrapped in a JSON envelope.
5. **`Session.send()` → stdin** — Line 109 writes `text.encode() + b"\n"`. If stdin expects stream-json, this must become a JSON object.

### Implementation Notes

1. **First: determine the exact stream-json protocol.** Before writing code, run a manual test:
   ```bash
   echo '{"type":"user","content":"hello"}' | claude --print --output-format stream-json --input-format stream-json 2>/dev/null
   ```
   Also try: `echo "hello" | claude -p --output-format stream-json 2>/dev/null` to see what JSON events are emitted. The output structure will determine how `_read_stdout()` must parse.

2. **Subprocess invocation change** (lines 337-345): Add the new flags to `create_subprocess_exec`. The args tuple should become something like:
   ```python
   "claude", "--agent", agent_name, "--print",
   "--output-format", "stream-json",
   "--input-format", "stream-json",
   ```
   Consider also `--verbose` for diagnostics and `--permission-mode` to avoid hanging on permission prompts.

3. **`_read_stdout()` parsing** (lines 203-231): Each line from stdout will be a JSON object. Parse with `json.loads()`. The stream-json format likely emits events like:
   - `{"type": "assistant", "content": [{"type": "text", "text": "..."}]}` — extract and relay the text
   - `{"type": "tool_use", ...}` — skip or log
   - `{"type": "result", ...}` — may indicate completion

   Wrap `json.loads()` in try/except `json.JSONDecodeError` to handle any non-JSON lines gracefully (log and skip).

4. **Response aggregation**: Consider whether to relay each text event immediately or buffer them into complete responses. Immediate relay is simpler and gives the user faster feedback. The existing `on_response` → `send_long_message` pipeline already handles splitting long texts.

5. **`Session.send()` formatting** (lines 93-112): If using `--input-format stream-json`, wrap user text:
   ```python
   import json
   msg = json.dumps({"type": "user", "content": text}) + "\n"
   self.process.stdin.write(msg.encode())
   ```

6. **`Session.shutdown()` formatting** (lines 144-149): The shutdown message also goes through stdin. If stream-json is used, wrap it the same way as `send()`.

7. **Test updates**:
   - Update `_make_mock_process()` to produce JSON-formatted stdout lines
   - Update the subprocess invocation assertion in `test_start_session_spawns_process` (line 488)
   - Update `test_send_writes_to_stdin` (line 208) to expect JSON-formatted input
   - Add new tests for JSON parsing in `_read_stdout()` (valid events, malformed JSON, tool-use filtering)

8. **Risk mitigation**: The exact stream-json protocol format is not documented in this codebase. The developer MUST empirically test the CLI output before implementing the parser. If `stream-json` doesn't work for multi-turn, fall back to `--output-format text` with `--input-format stream-json` or explore other flag combinations.

## Design Context

This is a **P0 / critical** fix. The bot is completely non-functional without it — agent responses never reach the user. The root cause is that `claude --agent <name>` defaults to interactive/TUI mode, which produces no usable stdout output when stdin/stdout are pipes. The design has been updated to require non-interactive invocation with appropriate CLI flags. See `artifacts/designer/design.md`, sections "Subprocess Invocation" and "Process Management". Forum topic `2026-03-08T00:03:00Z-operator-no-agent-responses-after-session-start` contains detailed analysis from the developer and task_planner on the correct flags (`--print --output-format stream-json --input-format stream-json`).
