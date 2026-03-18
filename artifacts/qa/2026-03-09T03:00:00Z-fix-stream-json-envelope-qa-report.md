# QA Report: Fix stream-json input envelope format — bot crashes on first message

## Metadata
- **Ticket**: Fix stream-json input envelope format — bot crashes on first message
- **Tested**: 2026-03-09T03:00:00Z
- **Result**: PASS (automated checks only — manual Telegram testing deferred)

## Steps

### Step 1: Verify envelope format in `Session.send()`
- **Result**: PASS
- **Notes**: Line 252-255 of `session.py` now constructs `{"type": "user", "message": {"role": "user", "content": text}}`. The `"type": "user"` discriminator field is present. Test `test_send_writes_json_to_stdin` asserts this exact format.

### Step 2: Verify envelope format in `Session.shutdown()`
- **Result**: PASS
- **Notes**: Lines 293-296 of `session.py` construct an identical envelope structure for the shutdown message. Test `test_shutdown_sends_json_shutdown_message` asserts this format.

### Step 3: Verify consistency between `send()` and `shutdown()`
- **Result**: PASS
- **Notes**: Both methods use the same `{"type": "user", "message": {"role": "user", "content": ...}}` structure. No divergence.

### Step 4: Verify `SessionManager.send_message()` forwards correct format
- **Result**: PASS
- **Notes**: Test `test_send_message_forwards_json_to_session` confirms the manager-level send produces the correct envelope.

### Step 5: All unit tests pass
- **Result**: PASS
- **Notes**: All 55 tests pass (`55 passed in 6.06s`). Three test assertions were updated to match the corrected envelope format. The "pending tasks destroyed" warnings are benign (documented in developer notes).

### Step 6–10: Manual Telegram integration tests (QA steps 1–5 from ticket)
- **Result**: DEFERRED
- **Notes**: The ticket's QA steps 1–5 require a live Telegram bot session (send message, verify response, trigger shutdown, check logs, multi-message flow). These cannot be executed in an automated QA pass. The code changes and unit tests are correct; manual integration testing should be performed before final sign-off.

## Summary

All automated checks pass. The code change is minimal and correct — `"type": "user"` has been added to the stream-json envelope in both `send()` and `shutdown()`, and all three affected test assertions have been updated to match. The fix directly addresses the reported `TypeError: undefined is not an object (evaluating '$.message.role')` crash.

Manual integration testing (sending a real Telegram message, verifying agent response, testing shutdown) is deferred to the user. No issues found in code review or automated tests.
