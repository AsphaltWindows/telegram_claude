# session-timeout-user-notification

## Metadata
- **From**: product_manager
- **To**: task_planner

## Content

### Requirements

1. When a session is terminated due to idle timeout, the bot must send a message to the user via Telegram informing them that the session has ended (e.g., 'Session ended due to inactivity. Send a new message to start a new session.').
2. After a session is cleaned up (via `_finish("timeout")` and `SessionManager._remove_session()`), verify that new incoming messages from the user correctly trigger a new session rather than hitting a `ValueError("No active session")` with no user-visible feedback.
3. If the timeout notification message to Telegram fails to send (network error, API error), this failure must be logged at WARNING or ERROR level. The session cleanup must still proceed regardless.
4. The `on_end` callback path (session.py lines 393-395) should be reviewed to ensure exceptions in the callback do not prevent proper session cleanup or leave the bot in a state where it cannot accept new messages for that chat.

### QA Steps

1. Start a session and let it idle until the timeout fires. Verify the user receives a clear notification message in Telegram that the session was ended due to inactivity.
2. After receiving the timeout notification, send a new message. Verify a new session is started successfully and the bot responds normally.
3. Simulate a failure in sending the timeout notification (e.g., disconnect network briefly). Verify the session cleanup still completes and the bot can accept new messages for that chat afterward.
4. Check logs after a timeout event to confirm appropriate log entries exist for the timeout, the notification attempt, and the session cleanup.
5. Verify no race condition exists: rapidly send a message right as the timeout fires. Confirm the bot either delivers the timeout message and starts a new session, or the new message prevents the timeout — but does not leave the bot in a broken state.

### Design Context

This addresses the secondary issue from the bot unresponsiveness bug: when a session dies due to timeout, the bot goes completely silent with no user feedback. The user has no way to know what happened or that they need to send a new message. Silent failure is the worst UX outcome for a chat interface. The designer noted this is a UX bug independent of the timer fix. See forum topic: 2026-03-20-operator-bot-unresponsive-during-agent-file-reads.md. Developer analysis confirmed that after session removal, the code path for new messages may not gracefully handle the missing session. This ticket depends on the idle timer fix ticket (fix-idle-timer-agent-output) being implemented first or concurrently, but can be developed independently.
