# fix-idle-timer-reset-on-agent-output

## Metadata
- **From**: task_planner
- **To**: developer

## Content

### Requirements

1. In `session.py`, the `_read_stdout()` method must update the `last_activity` timestamp each time it successfully receives and parses a line of output from the agent process.
2. The idle timeout check task must consider both user input AND agent output when determining inactivity — a session is only idle when neither the user nor the agent has produced activity for 10 minutes.
3. The `last_activity` field (or equivalent) must be a single shared timestamp that is updated by both `send()` (user input) and `_read_stdout()` (agent output).
4. No change to the timeout duration (remains 10 minutes) or the graceful shutdown path.

### QA Steps

1. Start a session and send a message that triggers a long-running agent operation (e.g., reading multiple files). Verify the session remains alive throughout the operation and does not timeout while the agent is actively producing output.
2. Start a session, send one message, then wait without sending further messages. Verify that once the agent finishes responding and 10 minutes pass with no user input AND no agent output, the session times out normally.
3. Inspect the `_read_stdout()` code path and confirm `last_activity` is updated on each successfully parsed stdout line.
4. Check logs to verify the idle timer correctly reflects the most recent activity timestamp from either source.

### Technical Context

#### Relevant Files

- **`telegram_bot/session.py`** (lines 361-427) — `_read_stdout()` method. This is the PRIMARY file. The fix is already implemented at lines 385-388: `self.last_activity = time.monotonic()` and `self._reset_idle_timer()` are called on each non-empty stdout line.
- **`telegram_bot/session.py`** (lines 227-254) — `send()` method. Already updates `last_activity` at line 253. This is the user-input side.
- **`telegram_bot/session.py`** (lines 450-465) — `_idle_timer()` method. Checks `time.monotonic() - self.last_activity` against `_idle_timeout`.
- **`telegram_bot/session.py`** (lines 467-471) — `_reset_idle_timer()` method. Cancels and restarts the idle timer task.
- **`artifacts/developer/telegram_bot/tests/test_session_idle_timer.py`** — Existing test file with 6 tests covering this exact feature: `test_read_stdout_resets_last_activity`, `test_read_stdout_calls_reset_idle_timer`, `test_read_stdout_resets_on_non_text_events`, `test_read_stdout_resets_before_on_response_callback`, `test_read_stdout_resets_on_each_line`, `test_empty_lines_do_not_reset_timer`.

#### Patterns and Conventions

- Tests use `pytest` with `pytest-asyncio` (`@pytest.mark.asyncio`).
- Mocks use `mock.AsyncMock` and `mock.MagicMock`.
- Session test helper `_make_session()` creates a Session with mocked process/callbacks.
- `_reset_idle_timer()` is stubbed with `MagicMock()` in tests to avoid creating real asyncio tasks.
- `session._shutting_down = True` is set in tests to prevent `_finish()` from running when stdout EOF triggers crash detection.

#### Dependencies and Integration Points

- `time.monotonic()` is used for timestamps (not `time.time()`).
- `_reset_idle_timer()` creates a new `asyncio.Task` each time, so tests must stub it.
- The `_idle_timer()` loop sleeps for `_idle_timeout` seconds, then checks elapsed time. Resetting the timer via `_reset_idle_timer()` cancels the old task and starts a new one.

#### Implementation Notes

- **THIS FIX IS ALREADY IMPLEMENTED.** The code at `session.py` lines 385-388 already resets `last_activity` and calls `_reset_idle_timer()` on each non-empty stdout line. The tests in `test_session_idle_timer.py` already pass.
- The developer should verify the implementation is correct by running the existing tests: `cd artifacts/developer/telegram_bot && python -m pytest tests/test_session_idle_timer.py -v`
- The idle timer reset happens BEFORE `_extract_text_from_event()` and the `on_response` callback, so even non-text events (tool_use, system) keep the session alive. This is correct — the agent is active even when using tools.
- No new code needs to be written. This ticket can be closed after verification.

### Design Context

The idle timer previously only reset on user input, causing sessions to be killed during legitimate long-running agent work (file reads, multi-step tool use). This fix ensures agent output also counts as activity. See `artifacts/designer/design.md`, section "Idle Timeout Implementation".
