# implement-progress-status-messages

## Metadata
- **From**: task_planner
- **To**: developer

## Content

### Requirements

1. When agent silence reaches approximately 15 seconds (measured via `silence_start`), send a user-visible status message: '⏳ Still working...'
2. When agent silence reaches approximately 60 seconds, send a second user-visible status message: '⏳ This is taking a while — still processing your request.'
3. Do NOT send any additional status messages beyond the 60-second message. The typing indicator continues until the agent responds or the idle timeout fires.
4. Each status message must be sent exactly once per silence period. If the agent produces output and goes silent again, the thresholds reset and messages may fire again for the new silence period.
5. Status messages must be sent through the same retry-capable send path used for normal agent responses (including retry and circuit breaker logic).
6. Status messages must be prefixed with the hourglass emoji (⏳) to visually distinguish them from agent responses.
7. Do NOT delete or edit status messages after the agent eventually responds. They remain in the chat history.
8. The silence checking logic should live in the existing `_typing_heartbeat` loop or a parallel async task.

### QA Steps

1. Send a message that causes the agent to work for more than 15 seconds. Verify that at ~15s of silence, the bot sends '⏳ Still working...' to the chat.
2. If the agent continues working past 60 seconds, verify the bot sends '⏳ This is taking a while — still processing your request.' at ~60s.
3. Verify no further status messages are sent after the 60-second message, even if the agent remains silent for several more minutes.
4. Trigger a long operation, wait for the 15s message, then send a message that causes quick agent output followed by another long silence. Verify that the 15s message fires again for the new silence period (confirming per-period reset).
5. Verify that status messages appear with the ⏳ prefix and are visually distinct from normal agent responses.
6. Verify that status messages remain in chat after the agent responds — they are not deleted or edited.
7. Simulate a Telegram API failure during status message send. Verify the retry/circuit breaker logic applies and a failed status message does not crash the session.
8. Verify typing indicator continues throughout the entire silence period regardless of status messages.

### Technical Context

**NOTE**: This ticket covers the same feature as `send-progress-status-messages` but is written as a higher-level, standalone description. Both tickets describe implementing progress status messages in the `_typing_heartbeat` loop. The developer should treat these as a single unit of work — implementing `send-progress-status-messages` (which has more specific line references) satisfies this ticket as well.

#### Relevant Files

- **`telegram_bot/session.py`** (primary) — `Session._typing_heartbeat` (lines 483-509) is the implementation target. All changes are within this method.
  - `Session.__init__` (lines 172-209): Contains `silence_start`, `_sent_15s_status`, `_sent_60s_status` (from prerequisite ticket).
  - `Session._read_stdout` (lines 375-442): Resets silence tracking on agent output; no changes needed.
  - `Session._on_response` (line 190): Callback for sending messages to the user with retry/circuit breaker.
- **`artifacts/developer/telegram_bot/session.py`** — Developer's working copy.
- **`telegram_bot/bot.py`** (read-only):
  - `on_response` closure (lines 345-380): Retry + circuit breaker logic that status messages route through.
- **`artifacts/developer/telegram_bot/tests/test_typing_heartbeat.py`** — Add test cases for the progress status message behavior.

#### Patterns and Conventions

- Same patterns as described in the `send-progress-status-messages` enriched ticket.
- Error swallowing pattern: `try: await callback() / except Exception: logger.exception(...)` — used for both typing indicators and status messages.
- Module-level constants for thresholds (`_PROGRESS_15S_THRESHOLD`, `_PROGRESS_60S_THRESHOLD`).

#### Dependencies and Integration Points

- **Prerequisite**: `track-silence-start-timestamp` — provides `silence_start`, `_sent_15s_status`, `_sent_60s_status` on the Session instance.
- **Prerequisite**: `send-progress-status-messages` — if implemented first, this ticket is already satisfied. The developer should implement them together as one change.
- **`_on_response` callback**: Routes through `send_long_message` -> `retry_send_message` in `bot.py` with retry and circuit breaker.

#### Implementation Notes

1. **This ticket is a duplicate/superset of `send-progress-status-messages`**. The implementation is identical — modify `_typing_heartbeat` to check silence thresholds and send status messages via `_on_response`. See the detailed implementation guidance in the `send-progress-status-messages` enriched ticket.
2. **Implement both tickets as a single change**. The QA steps from both tickets should be satisfied by the same implementation.
3. See `send-progress-status-messages` enriched ticket for the exact code structure, threshold constants, and test plan.

### Design Context

This ticket implements the user-facing progress status messages for the Long-Wait Feedback feature. Users perceive the bot as frozen during long agent operations (30+ seconds) because the typing indicator alone is too subtle. The tiered status messages provide explicit feedback at 15s and 60s thresholds. Depends on the silence tracking ticket (track-silence-start-timestamp) for the `silence_start` timestamp. See artifacts/designer/design.md, section 'Heartbeat / Typing Indicator & Long-Wait Feedback', including the threshold table and implementation requirements.
