# telegram-send-circuit-breaker

## Metadata
- **From**: product_manager
- **To**: task_planner

## Content

### Requirements

1. Track consecutive send failures per chat session. Each time the retry wrapper (from ticket telegram-send-retry-with-logging) reports a failed send, increment a per-session consecutive failure counter. Each time a send succeeds, reset the counter to 0.

2. After 5 consecutive send failures within a single session, automatically end the session. Use the existing session-end mechanism (SessionManager.end_session or equivalent).

3. When the circuit breaker triggers, log at ERROR level: 'Session ended: {N} consecutive Telegram send failures for chat {chat_id}'.

4. When the circuit breaker triggers, attempt to send one final notification to the user: 'Session ended due to repeated message delivery failures. Please start a new session.' This notification must use the retry wrapper but if it also fails, log and move on — do not block or enter any additional retry loop.

5. After the circuit breaker ends a session, new messages from the user must follow the normal 'no active session' flow (the existing behavior that prompts them to start a new session). No special handling is required beyond the standard flow.

6. If the 'no active session' notification itself fails to send, log the failure and move on — do not enter any retry loop for non-session messages.

7. The consecutive failure counter must only count response-delivery sends (messages sent as part of an active session's Claude responses), not one-off notifications like session-start confirmations.

### Dependencies

- Depends on ticket **telegram-send-retry-with-logging** (needs the retry wrapper's success/failure signal to track consecutive failures).

### QA Steps

1. **Unit test — counter resets on success**: Simulate 4 consecutive failures followed by 1 success. Verify the counter resets to 0 and the session is NOT ended.

2. **Unit test — circuit breaker triggers at 5**: Simulate exactly 5 consecutive send failures. Verify the session is ended and the ERROR log message includes the failure count and chat_id.

3. **Unit test — circuit breaker final notification**: Simulate 5 consecutive failures triggering circuit breaker. Verify one attempt is made to send the user notification message 'Session ended due to repeated message delivery failures. Please start a new session.'

4. **Unit test — final notification failure is non-blocking**: Simulate 5 failures triggering circuit breaker, and mock the final notification to also fail. Verify no exception propagates and the failure is logged.

5. **Unit test — post-circuit-breaker message routing**: After circuit breaker ends a session, send a new user message. Verify it enters the normal no-active-session flow.

6. **Unit test — counter scoped to session**: Verify that failures in one chat's session do not affect the counter for another chat.

7. **Integration test — end-to-end**: Start a session, mock Telegram API to fail on all sends, send 5 Claude responses. Verify the session is ended, the log contains the circuit breaker message, and a subsequent user message gets the 'no active session' response.

### Design Context

Implements the 'Consecutive Failure Circuit Breaker' and 'Post-Failure Message Routing' sections of the Telegram Send Error Handling design. See artifacts/designer/design.md, section 'Telegram Send Error Handling'. The circuit breaker prevents sessions from running indefinitely while silently dropping all output, which was the core user-reported bug.
