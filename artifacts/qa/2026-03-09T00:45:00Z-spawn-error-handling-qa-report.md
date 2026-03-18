# QA Report: Add error handling for agent process spawn failure

## Metadata
- **Ticket**: Add error handling for agent process spawn failure
- **Tested**: 2026-03-09T00:45:00Z
- **Result**: PASS

## Steps

### Step 1: Code review — try/except around start_session()
- **Result**: PASS
- **Notes**: Two except blocks implemented at bot.py lines 232-251. First catches `(FileNotFoundError, OSError)` for expected subprocess spawn errors, second catches generic `Exception` for unexpected errors. Both return early after sending an error reply.

### Step 2: Code review — User-facing error reply
- **Result**: PASS
- **Notes**: Both except blocks send: "Failed to start session with `{agent_name}`. Check that `claude` is installed and available." Uses backticks around agent_name for Telegram formatting.

### Step 3: Code review — No session state left behind on failure
- **Result**: PASS
- **Notes**: `start_session()` raises before adding to `_sessions` dict, so no cleanup is needed. Handler returns early, skipping both the confirmation message and any first_message forwarding. Verified by `test_spawn_failure_no_session_left_behind`.

### Step 4: Code review — Logging at appropriate levels
- **Result**: PASS
- **Notes**: Expected OS errors (`FileNotFoundError`, `OSError`) logged with `logger.error` (line 233). Unexpected exceptions logged with `logger.exception` (line 243) which includes full traceback. Both include agent name and chat_id in the log message.

### Step 5: Code review — Confirmation message only sent on success
- **Result**: PASS
- **Notes**: Confirmation "Starting session with `{agent_name}`…" at line 254 is positioned after the try/except block, so it is only reached on successful session start. Verified by `test_spawn_failure_no_first_message_sent` which asserts only 1 reply (the error) is sent.

### Step 6: Test suite — all tests pass
- **Result**: PASS
- **Notes**: All 36 tests pass (31 existing + 5 new). New tests cover: FileNotFoundError, OSError, unexpected RuntimeError, no session left behind, and no first message sent on failure. Tests verify both the user-facing reply content and correct logger method usage.

### Step 7: Manual QA steps (deferred — require live environment)
- **Result**: DEFERRED
- **Notes**: The ticket's QA steps 1-4 require a live Telegram bot environment (renaming claude binary, sending commands, checking logs, restoring binary). These cannot be executed in automated QA. The unit tests provide comprehensive mock-based coverage of all code paths. Manual testing should be performed when deploying.

## Summary

All code-level QA checks pass. The implementation is clean and well-structured with two separate except blocks providing appropriate logging granularity (error vs exception with traceback). The 5 new tests thoroughly cover all spawn failure scenarios. The only untested aspect is live end-to-end behavior which requires a running bot instance — deferred to deployment-time manual testing.
