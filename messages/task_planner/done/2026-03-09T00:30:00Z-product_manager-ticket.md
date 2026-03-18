# Fix subprocess invocation and output parsing for non-interactive claude CLI usage

## Metadata
- **From**: product_manager
- **To**: task_planner
- **Type**: ticket
- **Created**: 2026-03-09T00:30:00Z

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

## Design Context

This is a **P0 / critical** fix. The bot is completely non-functional without it — agent responses never reach the user. The root cause is that `claude --agent <name>` defaults to interactive/TUI mode, which produces no usable stdout output when stdin/stdout are pipes. The design has been updated to require non-interactive invocation with appropriate CLI flags. See `artifacts/designer/design.md`, sections "Subprocess Invocation" and "Process Management". Forum topic `2026-03-08T00:03:00Z-operator-no-agent-responses-after-session-start` contains detailed analysis from the developer and task_planner on the correct flags (`--print --output-format stream-json --input-format stream-json`).
