# HOTFIX: Add --verbose flag to Claude CLI subprocess args in session.py

## Metadata
- **From**: task_planner
- **To**: developer
- **Type**: enriched-ticket
- **Created**: 2026-03-09T01:15:00Z

## Requirements

1. In `artifacts/developer/telegram_bot/session.py`, in the `SessionManager.start_session()` method (around line 539-554), add `"--verbose"` to the `asyncio.create_subprocess_exec` argument list, immediately after `"--print"`.
2. The final CLI args must include: `"--print", "--verbose", "--output-format", "stream-json"` (in that order or equivalent — the key requirement is that `--verbose` is present).
3. In `artifacts/developer/tests/test_session.py`, update any test assertions that verify the CLI argument list to include `"--verbose"` in the expected args (around line 716-722).
4. All existing tests must continue to pass after the change.

## QA Steps

1. Read `session.py` and verify that `"--verbose"` is present in the `create_subprocess_exec` call args alongside `"--print"` and `"--output-format", "stream-json"`.
2. Run the test suite (`pytest artifacts/developer/tests/test_session.py`) and verify all tests pass.
3. If possible, manually start a session and verify the Claude CLI subprocess starts successfully (exit code 0 on normal operation) and produces valid stream-json output on stdout.
4. Verify no regression: the bot responds to a user message in Telegram without the "Session ended unexpectedly" error.

## Technical Context

### Relevant Files
- **`artifacts/developer/telegram_bot/session.py`** (lines 539-555): The `SessionManager.start_session()` method containing the `asyncio.create_subprocess_exec` call that spawns the Claude CLI. This is where `"--verbose"` must appear after `"--print"` (line 543-544).
- **`artifacts/developer/tests/test_session.py`** (lines 710-724): The `test_start_session_creates_process_and_session` test that asserts the CLI argument list via `mock_exec.call_args`. The assertion `assert "--verbose" in positional` must be present (line 718).

### Patterns and Conventions
- CLI flags are passed as individual string arguments to `asyncio.create_subprocess_exec` (one string per flag/value).
- Tests use `unittest.mock.patch` on `telegram_bot.session.asyncio.create_subprocess_exec` with `AsyncMock` to capture and verify subprocess arguments.
- Assertions check positional args via `mock_exec.call_args[0]` using `in` membership checks for individual flags.

### Dependencies and Integration Points
- The Claude CLI binary (configured via `self._claude_command`, defaults to `"claude"`) must support the `--verbose` flag in combination with `--print --output-format stream-json`.
- The `Session` class (same file) reads stdout from the subprocess — `--verbose` may produce additional output lines, but `stream-json` format parsing should be unaffected.

### Implementation Notes
- **⚠️ FIX ALREADY APPLIED**: The developer has already applied this fix (see forum discussion). Both `session.py` line 544 (`"--verbose"`) and `test_session.py` line 718 (`assert "--verbose" in positional`) are already in place. The developer should verify the fix is present and run tests to confirm, rather than making duplicate changes.
- If for any reason the fix is not present, add `"--verbose",` as a new line after `"--print",` (line 543) in the `create_subprocess_exec` call.
- In the test, add `assert "--verbose" in positional` after the `assert "--print" in positional` line.

## Design Context

The Claude CLI changed its requirements: `--output-format stream-json` now requires `--verbose` when used with `--print`. Without this flag, the CLI exits immediately with rc=1 and the error "When using --print, --output-format=stream-json requires --verbose". This causes a total outage — no user messages get responses. This is a one-line hotfix. See forum topic `2026-03-08T21:00:00Z-operator-claude-cli-stream-json-requires-verbose.md` for full diagnosis.
