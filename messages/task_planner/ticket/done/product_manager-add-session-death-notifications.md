# add-session-death-notifications

## Metadata
- **From**: product_manager
- **To**: task_planner

## Content

### Requirements

1. When a session is terminated by idle timeout, the bot must send the user: "Session with `<agent_name>` timed out after 10 minutes of inactivity. Work has been saved."
2. When a session ends due to an unexpected agent process crash, the bot must send the user: "Session with `<agent_name>` ended unexpectedly: {last stderr lines}" — including the last few lines of stderr for diagnostics.
3. When a session ends due to the consecutive send failure circuit breaker (5 failures), the bot must attempt to send: "Session ended due to repeated message delivery failures. Please start a new session." (no retry if this also fails).
4. After ANY session termination (timeout, crash, circuit breaker), the bot must fully clean up session state so that subsequent user messages follow the normal "no active session" flow and the bot remains responsive.
5. Silent session death — where the bot stops responding without notifying the user — must not occur under any termination scenario.

### QA Steps

1. Simulate an idle timeout (wait 10 minutes or temporarily lower the timeout). Verify the user receives the timeout notification message in Telegram.
2. Kill the agent subprocess externally (e.g., `kill -9` the claude process). Verify the user receives the unexpected crash notification with stderr content.
3. Simulate 5 consecutive Telegram send failures (e.g., mock the send method to raise NetworkError). Verify the circuit breaker triggers and attempts to send the circuit breaker notification.
4. After each termination scenario, send a new message to the bot and verify it responds with the "No active session" prompt (confirming session state was cleaned up).
5. Review all session termination code paths and confirm each one sends a user-facing message before cleanup.

### Design Context

Silent session death was identified as a critical UX problem — users had no way to know their session had ended and the bot appeared permanently unresponsive. This ticket ensures every termination path notifies the user. See `artifacts/designer/design.md`, section 'Session Death Notifications'.
