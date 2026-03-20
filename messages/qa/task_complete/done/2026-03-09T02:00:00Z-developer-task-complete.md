# Add pre-flight claude CLI check at bot startup and surface stderr on agent crash

## Metadata
- **From**: developer
- **To**: qa
- **Type**: task-complete
- **Created**: 2026-03-09T02:00:00Z

## Summary of Changes

Implemented two defense-in-depth features for the Telegram bot:

1. **Pre-flight CLI check**: At bot startup (`main()`), the bot now runs `claude --version` via `subprocess.run` and verifies it exits successfully. On failure (not found, timeout, non-zero exit), the bot logs a clear error and exits immediately via `sys.exit(1)`, preventing the Telegram polling loop from starting.

2. **Stderr surfacing on crash**: When an agent subprocess crashes, the last 10 stderr lines (truncated to 500 chars) are now captured and included in the "Session ended unexpectedly" message sent to the user in Telegram, formatted as a diagnostics block.

## Files Changed

- **`artifacts/developer/telegram_bot/bot.py`** — Added `_check_claude_cli()` function for pre-flight check, called from `main()`. Added `subprocess` and `sys` imports. Updated `on_end` callback signature to accept `stderr_tail` kwarg; crash messages now include stderr diagnostics. Changed `on_end` to use `send_long_message` for crash messages with potentially long stderr content.
- **`artifacts/developer/telegram_bot/session.py`** — Added `collections` import, `_STDERR_BUFFER_LINES` and `_STDERR_MAX_CHARS` constants. Added `_stderr_lines` deque buffer to `Session.__init__`. Added `stderr_tail` property. Updated `_read_stderr()` to buffer lines. Updated `_finish()` to pass `stderr_tail` to the `on_end` callback, and to briefly await the stderr reader before cancelling it (ensuring stderr is captured on crash).
- **`artifacts/developer/tests/test_session.py`** — Updated all `on_end` assertions to include `stderr_tail` kwarg. Added `TestSessionStderrBuffering` test class with 6 tests covering: empty stderr, buffered lines, bounded buffer, truncation, crash with stderr, crash without stderr. Updated regression test callback signature.
- **`artifacts/developer/telegram_bot/tests/test_bot.py`** — Added `TestCheckClaudeCli` test class with 8 tests covering: success, version logging, FileNotFoundError, timeout, OSError, non-zero exit, stderr logging, custom path. Added `TestOnEndWithStderr` test class with 3 tests covering: crash with stderr, crash without stderr, shutdown ignores stderr.

## Requirements Addressed

1. **Pre-flight check at startup** — Implemented via `_check_claude_cli()` called from `main()`.
2. **Use claude_path if configured** — `_check_claude_cli()` accepts a `command` parameter; currently called with default `"claude"`. Ready for the companion ticket to pass `config.claude_path`.
3. **Log version on success** — Logs at INFO level: `"claude CLI version: <version>"`.
4. **Fail fast on failure** — Logs descriptive error and calls `sys.exit(1)` for all failure modes (not found, timeout, non-zero exit, OSError).
5. **Capture last 10 stderr lines** — Implemented via `collections.deque(maxlen=10)` in `Session`.
6. **Include stderr in crash message** — Crash messages now include `Diagnostics:` section with stderr content, truncated to 500 chars.
7. **Handle empty stderr gracefully** — When stderr is empty, no diagnostics section is appended.

## QA Steps

1. Temporarily rename the `claude` binary (or set PATH to exclude it) and start the bot. Verify the bot fails fast with a clear error message mentioning that `claude` is not available, and does not start the Telegram polling loop.
2. Create a mock `claude` script that exits with code 1 and outputs an error to stderr. Start the bot pointing to it. Verify the bot fails fast with the error output logged.
3. With a working `claude` binary, start the bot and verify the log contains the claude version at INFO level and the bot proceeds normally.
4. Simulate an agent subprocess crash (e.g., kill the process, or use a mock that writes to stderr then exits non-zero). Verify the Telegram user receives a "Session ended unexpectedly" message that includes the stderr content.
5. Simulate an agent subprocess crash where stderr is empty. Verify the user still receives the "Session ended unexpectedly" message without a blank/broken stderr section.
6. Verify that very long stderr output is truncated to avoid exceeding Telegram message limits.

## Test Coverage

- **17 new tests** added across two test files (8 for pre-flight check, 3 for on_end with stderr, 6 for stderr buffering)
- **All 100 tests pass** (including updated existing tests)
- Run with: `python -m pytest tests/test_session.py telegram_bot/tests/test_bot.py -v`

## Notes

- The `_finish()` method now briefly awaits the stderr reader (up to 0.5s) before cancelling background tasks. This ensures stderr lines are captured even when the crash is detected via the stdout reader finishing first. The timeout prevents hanging if stderr is still streaming.
- The `on_end` callback signature changed from `(chat_id, agent_name, reason)` to `(chat_id, agent_name, reason, *, stderr_tail="")`. The `stderr_tail` parameter is keyword-only with a default, so existing callers that don't pass it will still work.
- The crash message now uses `send_long_message` instead of `bot.send_message` directly, to handle the case where stderr content pushes the message over Telegram's 4096-char limit.
