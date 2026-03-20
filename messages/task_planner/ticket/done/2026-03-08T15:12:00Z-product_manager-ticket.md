# Telegram Bot: Session Management & Process Lifecycle

## Metadata
- **From**: product_manager
- **To**: task_planner
- **Type**: ticket
- **Created**: 2026-03-08T15:12:00Z

## Requirements

1. Create `telegram_bot/session.py` implementing a `Session` class (or equivalent) that manages a single agent session
2. A session must hold: the `asyncio.subprocess.Process` handle, the user's Telegram chat ID, the agent name, and a last-activity timestamp
3. Spawning: start a `claude --agent <agent_name>` process via `asyncio.subprocess` from the project root directory, with stdin=PIPE, stdout=PIPE, stderr=PIPE
4. Sending messages: write user messages to the process's stdin, followed by a newline, and flush
5. Reading responses: run a continuous asyncio task that reads the agent's stdout and invokes a callback with each response (to be wired to Telegram message sending by the bot layer)
6. stderr: log stderr output for debugging; do not send to the user
7. Graceful shutdown (`end_session`): send the configured `shutdown_message` to the agent's stdin, wait for the agent to produce its final response, then terminate the process. Apply a reasonable timeout (e.g., 60 seconds) before force-killing.
8. Idle timeout: maintain a per-session timer that resets on each user message. After `idle_timeout` seconds of inactivity, trigger the same graceful shutdown as `/end`. Invoke a callback to notify the user of the timeout.
9. Crash handling: if the agent process exits unexpectedly (non-graceful), detect this and invoke a callback to notify the bot layer
10. Implement a `SessionManager` (or equivalent) that enforces one active session per user and provides methods to start, send, and end sessions
11. `SessionManager.start_session` must reject if the user already has an active session

## QA Steps

1. Start a session with a valid agent name; verify a `claude --agent <name>` subprocess is spawned
2. Send a message to the session; verify it is written to the process's stdin
3. Verify agent stdout is read and the response callback is invoked
4. Call `end_session`; verify the shutdown message is sent, final response is relayed, and the process is terminated
5. Simulate idle timeout by setting a short timeout (e.g., 2 seconds) and waiting; verify graceful shutdown is triggered and the timeout callback fires
6. Verify that starting a second session for the same user while one is active is rejected with an appropriate error
7. Simulate a process crash (kill the subprocess externally); verify the crash callback fires and session state is cleaned up
8. Verify stderr output is logged but not sent to the response callback

## Design Context

Session management is the core of the bot — it manages the lifecycle of `claude` agent processes and bridges communication between Telegram and the CLI. See `artifacts/designer/design.md`, sections "Agent Sessions", "Process Management", "Idle Timeout Implementation", and "Ending a Session".

**Dependency**: Requires the config module from the scaffolding ticket (for `idle_timeout` and `shutdown_message` values).
