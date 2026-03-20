# Fix subprocess invocation and implement stream-json protocol for agent sessions

## Metadata
- **From**: product_manager
- **To**: task_planner
- **Type**: ticket
- **Created**: 2026-03-08T22:00:00Z

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

## Design Context

This is the **P0 usability blocker** identified in forum topic `2026-03-08T00:03:00Z-operator-no-agent-responses-after-session-start`. The bot currently spawns `claude --agent <name>` in interactive TUI mode, which produces no usable stdout output when stdin/stdout are pipes. The `readline()` call in `_read_stdout()` blocks forever, making the bot completely non-functional — users never receive agent responses.

The fix changes the invocation to use `-p --output-format stream-json --input-format stream-json` for proper programmatic bidirectional communication, and updates both the output parser and input formatter to work with the JSON protocol.

See `artifacts/designer/design.md`, sections "Subprocess Invocation", "Stream-JSON Protocol", and "Process Management".
