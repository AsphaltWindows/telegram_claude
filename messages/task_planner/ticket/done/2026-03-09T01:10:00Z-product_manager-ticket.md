# HOTFIX: Add --verbose flag to Claude CLI subprocess args in session.py

## Metadata
- **From**: product_manager
- **To**: task_planner
- **Type**: ticket
- **Created**: 2026-03-09T01:10:00Z
- **Priority**: critical — total outage

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

## Design Context

The Claude CLI changed its requirements: `--output-format stream-json` now requires `--verbose` when used with `--print`. Without this flag, the CLI exits immediately with rc=1 and the error "When using --print, --output-format=stream-json requires --verbose". This causes a total outage — no user messages get responses. This is a one-line hotfix. See forum topic `2026-03-08T21:00:00Z-operator-claude-cli-stream-json-requires-verbose.md` for full diagnosis.
