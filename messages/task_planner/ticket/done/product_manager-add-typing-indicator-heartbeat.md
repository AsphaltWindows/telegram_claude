# add-typing-indicator-heartbeat

## Metadata
- **From**: product_manager
- **To**: task_planner

## Content

### Requirements

1. During long-running agent operations, when no agent output has been received for a configurable period (suggest 5-10 seconds), the bot should send a Telegram typing indicator (`chat_action: typing`) to the user's chat.
2. The typing indicator should repeat periodically while the agent is still working (Telegram typing indicators expire after ~5 seconds).
3. The typing indicator must stop when agent output is received or the session ends.
4. Failure to send a typing indicator must not crash the session or interfere with normal message relay — treat send errors as non-critical (log and continue).
5. This is a lower-priority enhancement. It depends on the idle timer fix (ticket: fix-idle-timer-reset-on-agent-output) being completed first, as that ticket establishes the agent-output activity tracking this feature builds on.

### QA Steps

1. Start a session and send a message that triggers a long agent operation. Verify the Telegram chat shows a "typing..." indicator while the agent is working.
2. Verify the typing indicator stops once the agent sends its response.
3. Verify that if the typing indicator send fails (e.g., network error), the session continues normally and the agent response is still delivered.
4. Verify the typing indicator does not appear during normal fast request/response exchanges.

### Design Context

This is an enhancement to improve UX during long-running agent operations. While the idle timer fix prevents premature session death, users may still be confused by long silences. A typing indicator provides visual feedback that the bot is still active. See `artifacts/designer/design.md`, section 'Heartbeat / Typing Indicator (Enhancement)'. This is explicitly marked as lower priority than the timer fix and death notifications.
