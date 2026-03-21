# implement-progress-status-messages

## Metadata
- **From**: developer
- **To**: qa

## Content

## Summary of Changes

Implemented progress status messages in the `_typing_heartbeat` loop. When the agent is silent for extended periods, the bot now sends user-visible status messages at two thresholds:
- **~15 seconds**: Sends '\u23f3 Still working...'
- **~60 seconds**: Sends '\u23f3 This is taking a while \u2014 still processing your request.'

No additional messages are sent beyond 60s. Messages are sent through the same retry-capable `_on_response` callback used for normal agent responses. Errors are logged and swallowed.

## Files Changed

- **`artifacts/developer/telegram_bot/session.py`** — Added `_PROGRESS_15S_THRESHOLD` and `_PROGRESS_60S_THRESHOLD` constants; modified `_typing_heartbeat()` to check silence thresholds and send status messages via `_on_response`.
- **`artifacts/developer/telegram_bot/tests/test_progress_status.py`** — New test file with 14 tests covering all requirements.

## Requirements Addressed

1. 15s status message sent after threshold — implemented in `_typing_heartbeat` with `_PROGRESS_15S_THRESHOLD` check
2. 60s status message sent after threshold — implemented with `_PROGRESS_60S_THRESHOLD` check
3. No additional messages beyond 60s — enforced by `_sent_15s_status` / `_sent_60s_status` flags
4. Each message sent once per silence period — flags checked before sending, reset on agent output (in `_read_stdout`)
5. Messages sent via `_on_response` callback (retry + circuit breaker path) — yes
6. Messages prefixed with \u23f3 emoji — yes
7. Status messages not deleted/edited after agent responds — not implemented (simple, no cleanup)
8. Errors logged and swallowed — try/except with `logger.exception()`

## QA Steps

1. Send a prompt that triggers a long agent operation. Verify '\u23f3 Still working...' appears at ~15s.
2. Continue waiting. Verify '\u23f3 This is taking a while \u2014 still processing your request.' at ~60s.
3. Verify no additional status messages after 60s.
4. After agent responds, trigger another long operation. Verify 15s and 60s messages fire again (reset works).
5. Verify no status message if agent responds within 10s.
6. Verify 60s message NOT sent if agent responds between 15s and 60s.
7. Verify \u23f3 prefix on status messages.
8. Verify typing indicator continues every 5s regardless.
9. Verify failed status message send is logged but session continues.

## Test Coverage

14 tests in `test_progress_status.py`:
- 15s message fires after threshold
- 15s message NOT sent before threshold
- 15s message sent exactly once
- 60s message fires after threshold
- 60s message NOT sent between 15s-60s
- 60s message sent exactly once
- No messages beyond 60s (exactly 2 total)
- Messages fire again after flag reset (simulating new silence period)
- 15s send failure logged and swallowed
- 60s send failure logged and swallowed
- Typing indicator continues alongside status messages
- Threshold constants have expected values
- 15s < 60s threshold ordering
- No status when silence_start is None (edge case)

Run: `python -m pytest artifacts/developer/telegram_bot/tests/test_progress_status.py -v`

All 14 new tests pass. All 22 existing tests (typing heartbeat + silence start) also pass.

## Notes

- Both tickets (`send-progress-status-messages` and `implement-progress-status-messages`) describe the same work and are satisfied by this single implementation.
- Timing precision: heartbeat fires every 5s, so 15s message arrives at ~15-20s and 60s at ~60-65s. This is acceptable per requirements.
- The `silence_start is not None` guard is defensive — after the prerequisite ticket, it's always a float, but the check prevents crashes if initialization order changes.
