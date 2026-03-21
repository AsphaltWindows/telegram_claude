# silence-period-summary-logging

## Metadata
- **From**: developer
- **To**: qa

## Content

### Summary of Changes

Implemented silence period summary logging in the typing heartbeat. Added a filtered event counter that tracks how many events were received but filtered since the last successful text extraction. The typing heartbeat now logs silence duration and filtered event count at INFO level each heartbeat interval.

### Files Changed

- **artifacts/developer/telegram_bot/session.py** — Added `_filtered_event_count` to `__init__` (initialised to 0). Updated `_read_stdout` to reset counter on text extraction and increment on filtered events. Added INFO log in `_typing_heartbeat` showing silence duration, filtered event count, agent name, and chat ID.
- **artifacts/developer/telegram_bot/tests/test_silence_logging.py** — New test file (8 tests) covering counter initialisation, increment/reset behavior, silence summary logging content, and typing indicator non-interference.

### Requirements Addressed

1. Track filtered event count, reset on text extraction — done.
2. Log silence duration and filtered event count in heartbeat at INFO — done.
3. Silence duration computed from existing silence_start timestamp — done.
4. Log only when silence_duration > 0 — done.
5. Typing indicator behavior unchanged — done (verified by test).

### QA Steps

1. Send a message triggering long agent operation. Verify INFO-level silence summary lines appear each heartbeat (~5s).
2. Verify silence duration increases with each heartbeat.
3. Verify filtered event count reflects actual events received.
4. When agent responds with text, verify counters reset.
5. Verify typing indicator still works.
6. Verify only one silence summary per heartbeat interval.

### Test Coverage

8 tests in test_silence_logging.py:
- test_initial_value (counter starts at 0)
- test_increments_on_filtered_events
- test_resets_on_text_extraction
- test_increments_after_reset
- test_silence_summary_logged (includes count)
- test_silence_summary_includes_agent_name_and_chat_id
- test_silence_summary_does_not_affect_typing
- test_no_log_when_session_just_started

Run: python -m pytest artifacts/developer/telegram_bot/tests/test_silence_logging.py -v

### Notes

- silence_start resets on ANY stdout line (existing behavior), so silence_duration measures time since any output, not just text output. The _filtered_event_count provides the complementary signal of how many events arrived without producing text.
- The silence summary log fires on every heartbeat during silence. This is by design per the ticket — it provides continuous diagnostic visibility, unlike the 15s/60s progress messages which fire once.
