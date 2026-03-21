# fix-idle-timer-agent-output

## Metadata
- **From**: developer
- **To**: qa

## Content

## Summary of Changes

Fixed the idle timer in Session._read_stdout() to reset on agent output, preventing premature session termination during long-running agent operations (e.g., file reads). Previously, the idle timer only reset on user input (in send()), so sessions were killed when agents took longer than the idle timeout to respond.

## Files Changed

- **telegram_bot/session.py** — Added 2 lines in _read_stdout() after the empty-line check (line 385-388): reset last_activity and call _reset_idle_timer() on every non-empty stdout line from the agent.
- **artifacts/developer/telegram_bot/session.py** — Same change applied to developer workspace copy.
- **artifacts/developer/telegram_bot/tests/test_session_idle_timer.py** — NEW: 6 test cases covering the idle timer reset behavior in _read_stdout().

## Requirements Addressed

1. **Update last_activity in _read_stdout()** — Done. self.last_activity = time.monotonic() added after line 383 (empty check), before event parsing.
2. **Call _reset_idle_timer() in same location** — Done. self._reset_idle_timer() called immediately after updating last_activity.
3. **Idle timeout still works when genuinely idle** — Unchanged. The _idle_timer() logic is untouched; it still fires when no activity occurs for the configured period.
4. **No timeout duration/config changes** — Confirmed. No changes to _idle_timeout or configuration.

## QA Steps

1. Start a session and send a message that triggers a long-running agent operation (e.g., reading multiple files). Verify the session stays alive throughout the entire operation and the agent response is delivered to the user.
2. Start a session and leave it idle (no user input, no agent activity) for longer than the configured idle timeout. Verify the session is still terminated by the idle timer as expected.
3. Start a session and trigger agent activity that produces output over a period exceeding the idle timeout (e.g., agent reads files for 10+ minutes if timeout is 10 min). Verify the session is NOT killed during this active processing.
4. Review the code change to confirm last_activity is updated AND _reset_idle_timer() is called in _read_stdout(), not just one or the other.

## Test Coverage

Tests in artifacts/developer/telegram_bot/tests/test_session_idle_timer.py:
- test_read_stdout_resets_last_activity — verifies last_activity is updated on agent output
- test_read_stdout_calls_reset_idle_timer — verifies _reset_idle_timer() is called
- test_read_stdout_resets_on_non_text_events — verifies reset happens on tool_use events (not just text)
- test_read_stdout_resets_before_on_response_callback — verifies timing: reset happens before callback
- test_read_stdout_resets_on_each_line — verifies reset happens for every line, not just the first
- test_empty_lines_do_not_reset_timer — verifies blank lines are correctly skipped

Run: pytest artifacts/developer/telegram_bot/tests/test_session_idle_timer.py -v

## Notes

- The fix is exactly 2 lines of code, matching the pattern established in send() (lines 253-254).
- Reset happens on ALL non-empty stdout lines, not just text events. This is intentional — tool_use and system events also indicate an active agent.
- The reset is placed BEFORE the on_response callback to ensure the timestamp is updated even if the callback raises.
