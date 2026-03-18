# QA Report: Add pre-flight claude CLI check at bot startup and surface stderr on agent crash

## Metadata
- **Ticket**: Add pre-flight claude CLI check at bot startup and surface stderr on agent crash
- **Tested**: 2026-03-09T02:15:00Z
- **Result**: PASS

## Steps

### Step 1: Pre-flight check — claude not found
- **Result**: PASS (code review + unit tests)
- **Notes**: `_check_claude_cli()` catches `FileNotFoundError`, logs a clear error mentioning the CLI is not found on PATH, and calls `sys.exit(1)`. The `main()` function calls this before `build_application()`, so the Telegram polling loop never starts. Verified by `test_file_not_found_exits` test.

### Step 2: Pre-flight check — claude exits with error
- **Result**: PASS (code review + unit tests)
- **Notes**: Non-zero exit code is handled at line 92-101 of bot.py. The stderr snippet (up to 200 chars) is logged. Verified by `test_nonzero_exit_code_exits` and `test_nonzero_exit_logs_stderr_snippet` tests. OSError and TimeoutExpired are also handled.

### Step 3: Pre-flight check — success logs version
- **Result**: PASS (code review + unit tests)
- **Notes**: On success, the version string from stdout is stripped and logged at INFO level: `"claude CLI version: %s"`. Verified by `test_success_logs_version_at_info` test.

### Step 4: Crash with stderr — user receives diagnostics
- **Result**: PASS (code review + unit tests)
- **Notes**: The `_finish()` method in session.py passes `stderr_tail` to the `on_end` callback (line 355-358). The `on_end` callback in bot.py appends a `Diagnostics:` code block when `reason == "crash"` and `stderr_tail` is non-empty (line 291-292). The message is sent via `send_long_message` to handle potential length overflow. Verified by `test_crash_passes_stderr_tail_to_on_end` (session) and `test_crash_message_includes_stderr` (bot) tests.

### Step 5: Crash with empty stderr — clean message
- **Result**: PASS (code review + unit tests)
- **Notes**: When `stderr_tail` is empty, no `Diagnostics:` section is appended (the `if reason == "crash" and stderr_tail:` guard on line 291). Verified by `test_crash_with_empty_stderr_passes_empty_string` and `test_crash_message_without_stderr` tests.

### Step 6: Long stderr truncated
- **Result**: PASS (code review + unit tests)
- **Notes**: `stderr_tail` property truncates to `_STDERR_MAX_CHARS` (500 chars) from the end of joined lines. The deque is bounded to `_STDERR_BUFFER_LINES` (10 lines). Crash messages use `send_long_message` which splits at 4096-char Telegram limit. Verified by `test_stderr_tail_truncated_to_max_chars` and `test_stderr_buffer_bounded_to_last_n_lines` tests.

## Summary

All 6 QA steps pass. The implementation is thorough and well-tested:

- **17 new tests** added (8 pre-flight CLI, 6 stderr buffering, 3 on_end with stderr), all passing.
- **100 total tests pass** with no failures.
- The `_finish()` method correctly awaits the stderr reader (up to 0.5s) before cancelling, ensuring crash diagnostics are captured even in race conditions.
- The `on_end` callback signature change is backward-compatible (keyword-only with default).
- Normal shutdown correctly omits diagnostics even if stderr was produced during the session.
- Edge cases are well-handled: empty stderr, very long stderr, timeout, missing binary, permission errors.

No concerns identified. Implementation matches all stated requirements.
