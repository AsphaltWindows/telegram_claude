# implement-circuit-breaker

## Metadata
- **From**: developer
- **To**: qa

## Content

### Summary of Changes

Implemented the consecutive failure circuit breaker for Telegram send operations. After 5 consecutive send failures in a session, the circuit breaker automatically ends the session, logs the event, and attempts a final notification to the user.

### Files Changed

- **artifacts/developer/telegram_bot/bot.py** — Added circuit breaker logic to the `on_response` closure in `agent_command_handler()`. Tracks consecutive failures via a `failure_state` dict, triggers at threshold of 5, sends final notification, and calls `session_manager.end_session()`.
- **telegram_bot/bot.py** — Same changes applied to the project root copy.
- **artifacts/developer/telegram_bot/tests/test_bot.py** — Added 9 new tests across 7 test classes covering all QA steps.

### Requirements Addressed

1. **Track consecutive send failures** — Implemented via `failure_state` dict with `consecutive_failures` counter in the `on_response` closure. Incremented on `send_long_message` returning False, reset to 0 on success.
2. **End session after 5 failures** — When counter reaches 5, calls `session_manager.end_session(cid)`.
3. **ERROR log on trigger** — Logs `Session ended: {N} consecutive Telegram send failures for chat {chat_id}` at ERROR level.
4. **Final notification** — Sends notification via `retry_send_message`. Wrapped in try/except — failure is logged and does not block.
5. **Normal no-active-session flow** — No changes needed. After `end_session`, existing `plain_text_handler` flow handles new messages.
6. **No retry loop for non-session notifications** — Not applicable to this code path; notification uses `retry_send_message` with standard 3 attempts max.
7. **Counter scoped to response-delivery sends** — Counter is in the `on_response` closure which is only called for Claude response delivery. `on_end` sends are separate and do not increment the counter.

### QA Steps

1. **Unit test — counter resets on success**: Simulate 4 consecutive failures followed by 1 success. Verify the counter resets to 0 and the session is NOT ended.
2. **Unit test — circuit breaker triggers at 5**: Simulate exactly 5 consecutive send failures. Verify the session is ended and the ERROR log message includes the failure count and chat_id.
3. **Unit test — circuit breaker final notification**: Simulate 5 consecutive failures triggering circuit breaker. Verify one attempt is made to send the user notification message.
4. **Unit test — final notification failure is non-blocking**: Simulate 5 failures triggering circuit breaker, and mock the final notification to also fail. Verify no exception propagates and the failure is logged.
5. **Unit test — post-circuit-breaker message routing**: After circuit breaker ends a session, send a new user message. Verify it enters the normal no-active-session flow.
6. **Unit test — counter scoped to session**: Verify that failures in one chat session do not affect the counter for another chat.
7. **Integration test — end-to-end**: Start a session, mock Telegram API to fail on all sends, send 5 Claude responses. Verify the session is ended, the log contains the circuit breaker message, and a subsequent user message gets the no-active-session response.

### Test Coverage

9 new tests across 7 test classes:
- `TestCircuitBreakerCounterReset` — 1 test (QA step 1)
- `TestCircuitBreakerTriggersAt5` — 2 tests (QA step 2)
- `TestCircuitBreakerFinalNotification` — 1 test (QA step 3)
- `TestCircuitBreakerFinalNotificationFailure` — 1 test (QA step 4)
- `TestCircuitBreakerPostBreaker` — 1 test (QA step 5)
- `TestCircuitBreakerSessionScoping` — 1 test (QA step 6)
- `TestCircuitBreakerEndToEnd` — 2 tests (QA step 7 + short-circuit test)

Run with: `python -m pytest artifacts/developer/telegram_bot/tests/test_bot.py -v`

All 72 tests pass (including 63 pre-existing + 9 new).

### Notes

- The `failure_state` dict uses a `circuit_broken` flag to short-circuit subsequent `on_response` calls after the breaker trips. This prevents double-ending the session if more stdout lines arrive before the session fully shuts down.
- The counter is naturally scoped per session because it lives in a closure created per `agent_command_handler` invocation.
- Both `telegram_bot/bot.py` (project root) and `artifacts/developer/telegram_bot/bot.py` were updated — the test imports from the artifacts copy.
