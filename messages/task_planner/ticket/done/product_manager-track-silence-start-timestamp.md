# track-silence-start-timestamp

## Metadata
- **From**: product_manager
- **To**: task_planner

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

### Design Context

This ticket implements the silence tracking infrastructure required by the 'Heartbeat / Typing Indicator & Long-Wait Feedback' design (see artifacts/designer/design.md, lines 234-236). The design requires tracking a silence_start timestamp that is reset on each agent output event, used by the progress status message logic to determine when silence thresholds are crossed. This is a prerequisite for the progress status messages ticket.
