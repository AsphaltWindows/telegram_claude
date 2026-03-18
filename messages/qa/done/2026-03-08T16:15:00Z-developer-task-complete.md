# Telegram Bot: Session Management & Process Lifecycle

## Metadata
- **From**: developer
- **To**: qa
- **Type**: task-complete
- **Created**: 2026-03-08T16:15:00Z

## Summary of Changes

Implemented `Session` and `SessionManager` classes in `telegram_bot/session.py` that manage the full lifecycle of `claude --agent <name>` subprocesses. Sessions handle stdin/stdout communication, idle timeouts, graceful shutdown with configurable shutdown messages, crash detection, and cleanup callbacks. The `SessionManager` enforces one active session per user.

## Files Changed

- `artifacts/developer/telegram_bot/session.py` — **Created.** Contains `Session` class (manages a single agent subprocess with stdout/stderr reading, idle timeout, graceful shutdown, crash detection) and `SessionManager` class (enforces one session per user, spawns processes, delegates send/end operations).
- `artifacts/developer/tests/test_session.py` — **Created.** 21 tests covering all requirements: stdout relay, stderr logging, stdin writing, last-activity tracking, graceful shutdown (including force-kill on timeout), idle timeout with timer reset, crash detection, and all `SessionManager` operations (start, send, end, duplicate rejection, has_session).

## Requirements Addressed

| # | Requirement | Implementation |
|---|---|---|
| 1 | `Session` class managing a single agent session | `Session` class in `session.py` |
| 2 | Session holds process handle, chat ID, agent name, last-activity timestamp | All stored as instance attributes |
| 3 | Spawn `claude --agent <name>` via `asyncio.subprocess` | `SessionManager.start_session` uses `asyncio.create_subprocess_exec` with stdin/stdout/stderr=PIPE, cwd=project_root |
| 4 | Write user messages to stdin + newline + flush | `Session.send()` writes `text.encode() + b"\n"` then awaits `drain()` |
| 5 | Continuous stdout reader with callback | `_read_stdout` asyncio task reads lines and invokes `on_response(chat_id, text)` |
| 6 | Log stderr, don't send to user | `_read_stderr` asyncio task logs via `logger.debug()` |
| 7 | Graceful shutdown with shutdown_message + timeout + force-kill | `Session.shutdown()` sends shutdown message, waits with 60s timeout, kills on timeout |
| 8 | Idle timeout with per-session timer that resets on activity | `_idle_timer` task sleeps for `idle_timeout`, checks elapsed time; `_reset_idle_timer()` cancels and restarts on each `send()` |
| 9 | Crash handling with callback | `_read_stdout` detects EOF without `_shutting_down` flag and calls `on_end(chat_id, agent_name, "crash")` |
| 10 | `SessionManager` with one session per user | `SessionManager` with `_sessions: Dict[int, Session]` |
| 11 | Reject duplicate sessions | `start_session` raises `ValueError` if `chat_id` already in `_sessions` |

## QA Steps

1. Start a session with a valid agent name; verify a `claude --agent <name>` subprocess is spawned
2. Send a message to the session; verify it is written to the process's stdin
3. Verify agent stdout is read and the response callback is invoked
4. Call `end_session`; verify the shutdown message is sent, final response is relayed, and the process is terminated
5. Simulate idle timeout by setting a short timeout (e.g., 2 seconds) and waiting; verify graceful shutdown is triggered and the timeout callback fires
6. Verify that starting a second session for the same user while one is active is rejected with an appropriate error
7. Simulate a process crash (kill the subprocess externally); verify the crash callback fires and session state is cleaned up
8. Verify stderr output is logged but not sent to the response callback

## Test Coverage

All 21 tests pass. Run with:
```
cd artifacts/developer && python -m pytest tests/test_session.py -v
```

Tests are organized into 8 classes:
- **TestSessionReading** (2 tests): stdout relay to callback, stderr logged but not relayed
- **TestSessionSend** (3 tests): stdin write, last_activity update, raises after shutdown
- **TestSessionShutdown** (5 tests): shutdown message sent, on_end callback with reason, cleanup callback, force-kill on timeout, double-shutdown safety
- **TestSessionIdleTimeout** (2 tests): timeout triggers shutdown, activity resets timer
- **TestSessionCrashDetection** (2 tests): unexpected exit fires crash callback, crash triggers cleanup
- **TestSessionManagerStart** (2 tests): spawns process correctly, rejects duplicate
- **TestSessionManagerSend** (2 tests): forwards to session, raises with no session
- **TestSessionManagerEnd** (2 tests): shuts down and removes session, no-op for nonexistent
- **TestSessionManagerHasSession** (1 test): reflects session state

## Notes

- **Python 3.7 compatibility**: The environment runs Python 3.7, which lacks `unittest.mock.AsyncMock`. The test file includes a minimal `AsyncMock` polyfill that falls back to `MagicMock` with an async `__call__`.
- **Self-cancellation guard**: The `shutdown()` method detects when called from within the idle timer task (via `asyncio.current_task()`) and avoids cancelling itself, which would interrupt the shutdown sequence.
- **`block_stdout` test helper**: Mock processes that need to stay alive use `block_stdout=True` to prevent the stdout reader from immediately detecting EOF and triggering crash handling.
- **Callback pattern**: The `Session` accepts `on_response` and `on_end` async callbacks plus a synchronous `cleanup` callable. This keeps the session decoupled from both `SessionManager` and the bot layer.
