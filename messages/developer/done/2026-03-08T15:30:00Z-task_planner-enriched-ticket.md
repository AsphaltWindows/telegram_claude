# Telegram Bot: Session Management & Process Lifecycle

## Metadata
- **From**: task_planner
- **To**: developer
- **Type**: enriched-ticket
- **Created**: 2026-03-08T15:30:00Z

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

## Technical Context

### Relevant Files

| File | Status | Relevance |
|---|---|---|
| `telegram_bot/session.py` | **To create** | The primary module for this ticket. Contains `Session` and `SessionManager` classes. |
| `telegram_bot/config.py` | Exists (`artifacts/developer/telegram_bot/config.py`) | Provides `BotConfig` dataclass with `idle_timeout` (int, seconds, default 600) and `shutdown_message` (str). `SessionManager` will need these values from the config. Import as `from telegram_bot.config import BotConfig`. |
| `telegram_bot/__init__.py` | Exists (`artifacts/developer/telegram_bot/__init__.py`) | Package init, contains docstring only. |
| `tests/test_config.py` | Exists (`artifacts/developer/tests/test_config.py`) | Reference for testing patterns: uses `pytest`, `tmp_path`, `monkeypatch`, class-based test organization with `pytest.mark.usefixtures`. Follow this style. |
| `artifacts/designer/design.md` | Exists (read-only) | Full design spec. Sections "Agent Sessions", "Process Management", "Idle Timeout Implementation", and "Ending a Session" are directly relevant. |
| `pipeline.yaml` | Exists | Defines agents. Not directly used by session.py, but the `agent_name` passed to `Session` must match an agent name from this file. |

### Patterns and Conventions

- **Dataclasses for data containers** — `BotConfig` in `config.py` uses `@dataclass`. Follow this for any data-holding classes.
- **Type hints throughout** — `config.py` uses `from __future__ import annotations`, `List`, `Optional` from `typing`. Use the same style (or modern `list[str]` / `str | None` syntax if `from __future__ import annotations` is present).
- **Docstrings** — `config.py` uses Google/NumPy-style docstrings with `Parameters`, `Returns`, `Raises` sections. Match this.
- **Path resolution** — `config.py` uses `Path(__file__).resolve().parent.parent` to find the project root. The developer code currently lives at `artifacts/developer/telegram_bot/`, so the project root is two levels up. For session spawning, the process CWD should be the project root.
- **Testing** — Tests in `tests/test_config.py` use pytest with fixtures, class-based grouping, and `monkeypatch` for env vars. Use `unittest.mock.AsyncMock` and `asyncio` test support for async testing in this ticket.
- **PyYAML** — Already a dependency (used in config.py).

### Dependencies and Integration Points

- **`BotConfig`** — `SessionManager` needs `idle_timeout` and `shutdown_message` from the config. Accept these as constructor parameters or accept the full `BotConfig` object.
- **`asyncio.subprocess`** — Core dependency for process spawning. Use `asyncio.create_subprocess_exec("claude", "--agent", agent_name, stdin=PIPE, stdout=PIPE, stderr=PIPE, cwd=project_root)`.
- **Callback pattern** — The `Session` needs two callbacks that the bot layer (`bot.py`, future ticket) will provide:
  - `on_response(chat_id: int, text: str)` — called when the agent writes to stdout
  - `on_session_end(chat_id: int, agent_name: str, reason: str)` — called on timeout, crash, or graceful end
- **Downstream consumer** — `bot.py` (future ticket) will create a `SessionManager`, pass it config values, and use it to manage sessions. Keep the interface clean: `start_session(chat_id, agent_name, on_response, on_end)`, `send_message(chat_id, text)`, `end_session(chat_id)`.
- **Logging** — Use `logging.getLogger(__name__)` for stderr output and debug info.

### Implementation Notes

1. **File to create**: `telegram_bot/session.py` (and `tests/test_session.py`).

2. **`Session` class design**:
   ```python
   class Session:
       def __init__(self, chat_id: int, agent_name: str, process: asyncio.subprocess.Process,
                    on_response: Callable, on_end: Callable, idle_timeout: int,
                    shutdown_message: str):
           self.chat_id = chat_id
           self.agent_name = agent_name
           self.process = process
           self.last_activity = time.monotonic()  # or asyncio.get_event_loop().time()
           self._idle_timeout = idle_timeout
           self._shutdown_message = shutdown_message
           # Start stdout reader task and idle timer task
   ```

3. **stdout reading** — Use `asyncio.create_task` to run a loop that calls `self.process.stdout.readline()`. When a line is read, invoke `on_response(chat_id, line)`. When `readline()` returns empty bytes, the process has ended — check `returncode` to determine if it was graceful or a crash.

4. **stderr reading** — Similarly, start a task that reads stderr and logs it via `logger.debug()` or `logger.warning()`. Do not invoke the response callback.

5. **Sending messages** — `process.stdin.write(message.encode() + b"\n")` followed by `await process.stdin.drain()`. Update `self.last_activity` on each send.

6. **Idle timeout** — Use an `asyncio.Task` that loops: `await asyncio.sleep(check_interval)`, then checks `time.monotonic() - self.last_activity >= idle_timeout`. If exceeded, trigger graceful shutdown. An alternative is to use a single `asyncio.sleep(idle_timeout)` that gets cancelled and restarted on each message — this is cleaner and avoids polling.

7. **Graceful shutdown (`end_session`)** — Steps:
   - Send `shutdown_message` to stdin
   - Wait for the stdout reader to finish (the agent should produce a final response and exit)
   - Apply a timeout (e.g., 60s) via `asyncio.wait_for`
   - If timeout expires, `process.kill()`
   - Cancel the idle timer task
   - Clean up session state in `SessionManager`

8. **Crash detection** — The stdout reader loop naturally detects process exit. When `readline()` returns `b""`, check `process.returncode`. If the session wasn't in a graceful shutdown state, it's a crash — invoke `on_end(chat_id, agent_name, "crash")`.

9. **`SessionManager` class design**:
   ```python
   class SessionManager:
       def __init__(self, idle_timeout: int, shutdown_message: str, project_root: Path):
           self._sessions: dict[int, Session] = {}  # chat_id -> Session

       async def start_session(self, chat_id, agent_name, on_response, on_end) -> Session:
           if chat_id in self._sessions:
               raise ValueError(f"User {chat_id} already has an active session")
           process = await asyncio.create_subprocess_exec(...)
           session = Session(...)
           self._sessions[chat_id] = session
           return session

       async def send_message(self, chat_id, text):
           session = self._sessions.get(chat_id)
           if not session:
               raise ValueError("No active session")
           await session.send(text)

       async def end_session(self, chat_id):
           session = self._sessions.pop(chat_id, None)
           if session:
               await session.shutdown()
   ```

10. **Testing approach** — Mock `asyncio.create_subprocess_exec` to return a mock process with mock stdin/stdout/stderr streams. Use `asyncio.Queue` or `BytesIO` to simulate stdout data. Test idle timeout with a very short timeout (1-2 seconds). Test crash by setting `process.returncode` to a non-zero value and closing stdout.

11. **Important gotcha**: `process.stdin.write()` is not a coroutine — it buffers synchronously. Only `drain()` is async. So the pattern is:
    ```python
    self.process.stdin.write(data)
    await self.process.stdin.drain()
    ```

12. **Important gotcha**: When the session ends (graceful, timeout, or crash), make sure to remove it from `SessionManager._sessions`. The `on_end` callback or the `Session` itself should trigger this cleanup. Consider having `Session` hold a reference to a cleanup callable provided by `SessionManager`.

## Design Context

Session management is the core of the bot — it manages the lifecycle of `claude` agent processes and bridges communication between Telegram and the CLI. See `artifacts/designer/design.md`, sections "Agent Sessions", "Process Management", "Idle Timeout Implementation", and "Ending a Session".

**Dependency**: Requires the config module from the scaffolding ticket (for `idle_timeout` and `shutdown_message` values). The config module already exists at `artifacts/developer/telegram_bot/config.py`.
