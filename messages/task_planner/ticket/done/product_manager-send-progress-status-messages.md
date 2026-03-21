# send-progress-status-messages

## Metadata
- **From**: product_manager
- **To**: task_planner

## Content

### Requirements

1. Modify the `_typing_heartbeat` loop in `session.py` (currently lines 480-506) to check `silence_start` against two thresholds on each iteration:
   - **~15 seconds of silence**: Send the status message '⏳ Still working...' to the user via the existing `_on_response` callback (or a similar retry-capable send path). Set `_sent_15s_status = True`.
   - **~60 seconds of silence**: Send the status message '⏳ This is taking a while — still processing your request.' to the user. Set `_sent_60s_status = True`.
2. Each status message must be sent **once** per silence period — check the `_sent_15s_status` / `_sent_60s_status` flags before sending. These flags are reset when agent output arrives (implemented in the prerequisite ticket 'track-silence-start-timestamp').
3. Beyond 60 seconds of silence, no additional status messages are sent. The typing indicator continues as before until the agent responds or idle timeout fires.
4. Status messages must be sent through the same retry-capable send path as normal agent responses (the `_on_response` callback with retry and circuit breaker logic in `bot.py`).
5. Status messages must be prefixed with the hourglass emoji (⏳) to visually distinguish them from agent responses.
6. Do NOT delete or edit status messages after the agent eventually responds — keep the implementation simple.
7. Errors sending status messages should be logged and swallowed (same pattern as typing indicator errors) — a failed status message must never crash the session.

### QA Steps

1. Start a session and send a prompt that triggers a long agent operation (e.g., a complex code generation task). Verify that after ~15 seconds of silence, the message '⏳ Still working...' appears in the chat.
2. Continue waiting and verify that after ~60 seconds of silence, the message '⏳ This is taking a while — still processing your request.' appears.
3. Verify that no additional status messages appear beyond the 60-second message, even if the agent remains silent for several more minutes.
4. After the agent responds, send another prompt that triggers a long operation. Verify that the 15s and 60s messages fire again (timers reset properly).
5. Verify that if the agent produces output at 10 seconds (before the 15s threshold), no status message is sent.
6. Verify that if the agent produces output between 15s and 60s, the 60s message is NOT sent (flags reset on output).
7. Verify that status messages appear with the ⏳ prefix and are visually distinct from agent responses.
8. Verify that the typing indicator continues to fire every 5 seconds regardless of status messages.
9. Verify that if `_on_response` fails when sending a status message, the error is logged but the session continues normally.

### Design Context

This ticket implements the user-visible progress status messages described in the 'Progress Status Messages' subsection of the design (see artifacts/designer/design.md, lines 224-241). The motivation is that the typing indicator alone makes the bot appear frozen during long agent operations — users need explicit textual feedback. This ticket depends on 'track-silence-start-timestamp' which provides the silence_start tracking and per-silence-period flags.
