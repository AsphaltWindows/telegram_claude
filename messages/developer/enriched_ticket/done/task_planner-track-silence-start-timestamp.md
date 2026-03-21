# track-silence-start-timestamp

## Metadata
- **From**: task_planner
- **To**: developer

## Content

### Requirements

1. Add a `silence_start` instance attribute to the `Session` class in `session.py`, initialized to `time.monotonic()` when the session starts (i.e., when the agent subprocess is launched).
2. In `_read_stdout()`, reset `silence_start` to `time.monotonic()` every time a non-empty line is received from the agent's stdout (alongside the existing `last_activity` reset at line 400).
3. `silence_start` must be reset on EVERY agent output line, not just lines that produce sendable text — this ensures the silence timer reflects actual agent activity, not just text output.
4. Add boolean flags `_sent_15s_status` and `_sent_60s_status` (initialized to `False`) to track whether each progress message has been sent for the current silence period.
5. When `silence_start` is reset (step 2), also reset both `_sent_15s_status` and `_sent_60s_status` to `False` so that a new silence period triggers fresh status messages.

### QA Steps

1. Add a print statement or log line in `_read_stdout()` after the silence_start reset and verify it fires on every agent stdout line by running the bot and sending a message.
2. Verify that `silence_start` is initialized at session start by checking the attribute exists immediately after `Session.__init__` completes.
3. Verify that both `_sent_15s_status` and `_sent_60s_status` reset to `False` when the agent produces output after a silence period.
4. Confirm that existing behavior (last_activity, idle timer reset, typing heartbeat) is unchanged — this ticket adds new fields only, no behavioral changes.

### Technical Context

#### Relevant Files

- **`telegram_bot/session.py`** (primary) — The `Session` class where all changes go. This is the production code.
  - `Session.__init__` (line 172-209): Constructor where new attributes are added.
  - `Session._read_stdout` (lines 375-442): Stdout reader loop where `silence_start` is reset on output. The reset already exists at **line 403** (`self.silence_start = now`), but `silence_start` is currently initialized to `None` (line 188) rather than `time.monotonic()` as the ticket requires.
  - `Session.send` (lines 241-268): User message sender — note this updates `last_activity` but must NOT update `silence_start` (silence tracks agent output, not user input).
- **`artifacts/developer/telegram_bot/session.py`** — Developer's working copy. Changes should go here; it mirrors the production file.
- **`artifacts/developer/telegram_bot/tests/test_silence_start.py`** — Existing test file for silence_start. Tests currently assert `silence_start` is `None` at creation (line 61). **These tests must be updated** because the ticket changes initialization from `None` to `time.monotonic()`.
- **`artifacts/developer/telegram_bot/tests/test_typing_heartbeat.py`** — Existing heartbeat tests. Should not need changes but verify no regressions.

#### Patterns and Conventions

- **Test structure**: Tests use `pytest` with `pytest.mark.asyncio`. Helper `_make_session()` creates a `Session` with mocked process and callbacks. See `test_silence_start.py` and `test_typing_heartbeat.py` for the exact pattern.
- **Mocking**: Uses `from mock import AsyncMock, MagicMock, patch` (not `unittest.mock`).
- **Time tracking**: The codebase uses `time.monotonic()` for all timing (never `time.time()`). Follow this convention.
- **Attribute naming**: Private flags use underscore prefix (`_sent_15s_status`), public state does not (`silence_start`, `last_activity`).
- **Docstring style**: NumPy-style docstrings with Parameters/Returns sections.

#### Dependencies and Integration Points

- **`_typing_heartbeat` (session.py lines 483-509)**: The follow-up ticket (send-progress-status-messages) will read `silence_start`, `_sent_15s_status`, and `_sent_60s_status` from within this loop. The flags added here are consumed there.
- **`on_response` callback (bot.py lines 345-380)**: The follow-up ticket will call this to send status messages. No changes needed in this ticket.
- **Existing `silence_start` attribute**: Already exists at line 188, initialized to `None`. Already reset at line 403. The ticket requires changing the initialization from `None` to `time.monotonic()` and adding the two boolean flags alongside it.

#### Implementation Notes

1. **Change `silence_start` initialization**: In `__init__` (line 188), change `self.silence_start: Optional[float] = None` to `self.silence_start: float = time.monotonic()`. This ensures silence tracking begins from session start, not from first output.
2. **Add the two boolean flags**: In `__init__`, add `self._sent_15s_status: bool = False` and `self._sent_60s_status: bool = False` right after `silence_start`.
3. **Reset flags in `_read_stdout`**: After line 403 where `self.silence_start = now`, add `self._sent_15s_status = False` and `self._sent_60s_status = False`.
4. **Update existing tests**: `test_silence_start.py` line 61 asserts `silence_start is None` — this must change to assert it is a float >= 0. Line 67 (`assert session.silence_start is None`) also needs updating. Line 149 (`assert session.silence_start == session.last_activity`) should still pass since both are set in `__init__` (though to different `time.monotonic()` calls, so they may differ slightly — consider testing `is not None` instead).
5. **Do NOT touch `send()`**: The `send()` method (line 267) updates `last_activity` but must not reset `silence_start` or the status flags — silence tracks agent output only.
6. **Type annotation update**: If `silence_start` changes from `Optional[float]` to `float`, update the type annotation accordingly.

### Design Context

This ticket implements the silence tracking infrastructure required by the 'Heartbeat / Typing Indicator & Long-Wait Feedback' design (see artifacts/designer/design.md, lines 234-236). The design requires tracking a silence_start timestamp that is reset on each agent output event, used by the progress status message logic to determine when silence thresholds are crossed. This is a prerequisite for the progress status messages ticket.
