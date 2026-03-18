# HOTFIX: Add --verbose flag to Claude CLI subprocess args in session.py

## Metadata
- **From**: developer
- **To**: qa
- **Type**: task-complete
- **Created**: 2026-03-09T01:30:00Z

## Summary of Changes

Verified that the `--verbose` flag hotfix was already applied to both `session.py` and `test_session.py`. The fix adds `"--verbose"` to the Claude CLI subprocess arguments in `SessionManager.start_session()`, which is required because the Claude CLI now mandates `--verbose` when using `--print` with `--output-format stream-json`. All 55 tests pass.

## Files Changed

- **`artifacts/developer/telegram_bot/session.py`** (line 544): `"--verbose"` already present after `"--print"` in the `asyncio.create_subprocess_exec` call — no change needed.
- **`artifacts/developer/tests/test_session.py`** (line 718): `assert "--verbose" in positional` already present in the test assertions — no change needed.

## Requirements Addressed

1. ✅ `"--verbose"` is present in the `create_subprocess_exec` argument list after `"--print"` (line 544).
2. ✅ The final CLI args include `"--print", "--verbose", "--output-format", "stream-json"` in the correct order.
3. ✅ The test assertion `assert "--verbose" in positional` is present (line 718).
4. ✅ All 55 existing tests pass (verified via `pytest`).

## QA Steps

1. Read `session.py` and verify that `"--verbose"` is present in the `create_subprocess_exec` call args alongside `"--print"` and `"--output-format", "stream-json"`.
2. Run the test suite (`pytest artifacts/developer/tests/test_session.py`) and verify all tests pass.
3. If possible, manually start a session and verify the Claude CLI subprocess starts successfully (exit code 0 on normal operation) and produces valid stream-json output on stdout.
4. Verify no regression: the bot responds to a user message in Telegram without the "Session ended unexpectedly" error.

## Test Coverage

All 55 tests in `test_session.py` pass, including `test_start_session_spawns_process_with_stream_json_flags` which explicitly asserts that `"--verbose"` is in the positional arguments passed to `create_subprocess_exec`.

Run with: `pytest artifacts/developer/tests/test_session.py -v`

## Notes

- The fix was already applied prior to this ticket (as noted in the enriched ticket's implementation notes). This task confirmed the fix is in place and all tests pass.
- No code changes were made — this is a verification-only pass.
