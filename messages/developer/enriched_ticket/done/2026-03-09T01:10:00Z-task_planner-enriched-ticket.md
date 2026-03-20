# Add pre-flight claude CLI check at bot startup and surface stderr on agent crash

## Metadata
- **From**: task_planner
- **To**: developer
- **Type**: enriched-ticket
- **Created**: 2026-03-09T01:10:00Z

## Requirements

1. During bot startup (in `main()` or `build_application()`), run `claude --version` as a subprocess and verify it exits successfully (exit code 0).
2. If the `claude_path` config option is set (see ticket for configurable claude_path), use that path instead of bare `claude` for the version check. If `claude_path` is not yet implemented, use bare `claude`.
3. On success, log the detected claude CLI version at INFO level.
4. On failure (command not found, non-zero exit, timeout after 10 seconds), log a clear error message indicating the likely cause (e.g., "claude CLI not found on PATH — is nvm initialized?") and exit the bot process with a non-zero exit code. Do not proceed to start the Telegram polling loop.
5. In `SessionManager`, when the agent subprocess exits unexpectedly (non-zero exit code), capture the last 10 lines of stderr from the process.
6. Include the captured stderr content in the "Session ended unexpectedly" message sent to the user in Telegram, truncated to a reasonable length (e.g., 500 characters) to avoid hitting Telegram message limits.
7. If stderr is empty, the crash message should still be sent but without the stderr section.

## QA Steps

1. Temporarily rename the `claude` binary (or set PATH to exclude it) and start the bot. Verify the bot fails fast with a clear error message mentioning that `claude` is not available, and does not start the Telegram polling loop.
2. Create a mock `claude` script that exits with code 1 and outputs an error to stderr. Start the bot pointing to it. Verify the bot fails fast with the error output logged.
3. With a working `claude` binary, start the bot and verify the log contains the claude version at INFO level and the bot proceeds normally.
4. Simulate an agent subprocess crash (e.g., kill the process, or use a mock that writes to stderr then exits non-zero). Verify the Telegram user receives a "Session ended unexpectedly" message that includes the stderr content.
5. Simulate an agent subprocess crash where stderr is empty. Verify the user still receives the "Session ended unexpectedly" message without a blank/broken stderr section.
6. Verify that very long stderr output is truncated to avoid exceeding Telegram message limits.

## Technical Context

### Relevant Files

| File | Purpose |
|---|---|
| `artifacts/developer/telegram_bot/bot.py` | **Primary target.** Contains `main()` (line 358) and `build_application()` (line 314). The pre-flight check should be added here. Also contains `on_end` callback (line 212) inside `agent_command_handler` — this is where the crash message is constructed and needs stderr content. |
| `artifacts/developer/telegram_bot/session.py` | **Primary target.** Contains `Session._read_stderr()` (line 380) which currently only logs stderr lines — must be modified to buffer them. Contains `Session._read_stdout()` (line 318) which calls `_finish("crash")` on unexpected exit (line 378) — this is where stderr must be captured and passed through. Contains `Session._finish()` (line 295) and the `on_end` callback interface. |
| `artifacts/developer/telegram_bot/config.py` | Read the `claude_path` config if it exists (for requirement 2). Currently has no `claude_path` field in `BotConfig` — if implementing this ticket before the claude_path ticket, just use bare `"claude"`. |
| `artifacts/developer/telegram_bot/__main__.py` | Entry point — calls `main()`. No changes needed here. |

### Patterns and Conventions

- **Async subprocess usage**: The codebase uses `asyncio.create_subprocess_exec` (session.py line 484). The pre-flight check should use the same pattern with `asyncio.wait_for` for the 10-second timeout.
- **Logging**: Uses `logging.getLogger(__name__)` per module. INFO for operational events, WARNING for agent stderr, DEBUG for diagnostics.
- **Docstrings**: All functions/methods have NumPy-style docstrings with Parameters/Returns/Raises sections.
- **Error handling in handlers**: `agent_command_handler` (bot.py line 169) catches `FileNotFoundError` and `OSError` from `start_session`. Follow this pattern.
- **Type hints**: All functions use type annotations. `from __future__ import annotations` is at the top of every module.
- **Constants**: Module-level constants use `_UPPER_SNAKE_CASE` prefix (e.g., `_SHUTDOWN_TIMEOUT`, `_MAX_MESSAGE_LENGTH`).

### Dependencies and Integration Points

1. **`on_end` callback signature**: Currently `(chat_id: int, agent_name: str, reason: str)`. To include stderr, this needs to change — either add a 4th parameter (e.g., `stderr_tail: str = ""`) or pass it through Session metadata that the callback can access. The `on_end` callback is defined inline in `agent_command_handler` (bot.py line 212) and invoked in `Session._finish()` (session.py line 314).

2. **`Session._finish()` → `on_end`**: The `_finish` method (session.py line 295) calls `self._on_end(self.chat_id, self.agent_name, reason)`. If adding stderr, this call signature must be updated, and all callers of `_finish()` must be checked: it's called from `_read_stdout` (line 378), `shutdown` (line 273).

3. **`send_long_message`**: Already exists in bot.py (line 120) for splitting long messages. Use this for the stderr-augmented crash message.

### Implementation Notes

**Part 1: Pre-flight check**

1. Add an async function `async def _check_claude_available() -> str` in `bot.py` that:
   - Runs `asyncio.create_subprocess_exec("claude", "--version", ...)` with stdout/stderr PIPE
   - Wraps it in `asyncio.wait_for(..., timeout=10)`
   - Returns the version string on success
   - Raises a descriptive error on failure
2. Call it from `main()` before `app.run_polling()`. Since `main()` is not currently async, you'll need to either:
   - Make the check synchronous using `subprocess.run` (simpler, acceptable for a one-shot startup check), OR
   - Use `asyncio.run()` for just the check before calling `app.run_polling()`
   - **Recommendation**: Use `subprocess.run` with `timeout=10` — it's simpler and this is a synchronous startup context.
3. On failure, log the error and call `sys.exit(1)`.

**Part 2: Surface stderr on crash**

1. In `Session.__init__`, add `self._stderr_lines: List[str] = []` to buffer stderr.
2. In `Session._read_stderr()`, append each line to `self._stderr_lines` (keeping only the last 10 lines — use a bounded deque or slice).
3. Add a property or method `Session.stderr_tail` that returns the last 10 lines joined as a string, truncated to 500 chars.
4. Update `Session._finish()` to pass stderr info to the callback. Two clean approaches:
   - **Option A** (minimal change): Add `self.stderr_tail` as a public attribute, and let the `on_end` callback access the session object. This requires passing the session to the callback or making it accessible.
   - **Option B** (cleaner): Change `on_end` signature to `(chat_id, agent_name, reason, stderr_tail)`. Update the inline callback in `agent_command_handler` accordingly.
   - **Recommendation**: Option B — explicit is better. Add `stderr_tail: str = ""` as the 4th parameter.
5. In the `on_end` callback (bot.py line 212), when reason is `"crash"`, append the stderr tail to the message if non-empty.

## Design Context

The operator identified that when the bot runs in non-login environments (systemd, cron), nvm may not be initialized, causing `claude` to be unavailable or broken at runtime. Currently, such failures are silent or produce generic error messages. This ticket adds defense-in-depth: fail fast at startup if the CLI is broken, and surface stderr diagnostics to users when agent processes crash unexpectedly. See `artifacts/designer/design.md`, sections "Pre-flight Environment Check" and the updated error cases table.
