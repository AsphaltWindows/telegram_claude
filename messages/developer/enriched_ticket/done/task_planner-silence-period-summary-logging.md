# silence-period-summary-logging

## Metadata
- **From**: task_planner
- **To**: developer

## Content

### Requirements

1. Track a count of events received-but-filtered (events where `_extract_text_from_event` returned `None`) since the last successful text extraction. Reset this counter to 0 each time text is successfully extracted.
2. In the typing heartbeat loop (`_typing_heartbeat` or equivalent), when the heartbeat fires during agent silence, log at INFO level: the duration of the current silence period (in seconds) and the count of filtered events since last text output (e.g., `INFO: Agent silent for 23s, 47 events received but filtered`).
3. The silence duration should be computed from the existing `silence_start` timestamp that is set whenever `_read_stdout()` receives agent output. If `silence_start` tracking does not yet exist, it must be added: set `silence_start = now` in the session when the agent starts, and reset it each time `_read_stdout()` receives output.
4. The log line must only appear when the agent IS silent (i.e., silence duration > 0). Do not log this line if the agent just produced output.
5. This logging must not affect the typing indicator behavior — the heartbeat continues to send typing actions as before.

### QA Steps

1. Start a session and send a message that triggers a long agent operation (e.g., multi-step tool use). While the agent is working, check the bot log and verify INFO-level lines appear showing silence duration and filtered event count, updating each heartbeat interval (~5 seconds).
2. Verify the silence duration increases with each heartbeat (e.g., 5s, 10s, 15s...).
3. Verify the filtered event count reflects actual events received (should be > 0 if the agent is doing tool calls).
4. When the agent finally responds with text, verify the silence counters reset — the next silence period should start from 0s and 0 filtered events.
5. Verify the typing indicator still works correctly (Telegram shows "typing..." during silence).
6. Verify no log spam — only one silence summary per heartbeat interval, not per event.

### Technical Context

#### Relevant Files

- **`artifacts/developer/telegram_bot/session.py`** (PRIMARY) — Modify `Session.__init__()` (add filtered event counter), `_read_stdout()` (increment/reset counter), and `_typing_heartbeat()` (add INFO log line).
- **`artifacts/developer/telegram_bot/tests/test_typing_heartbeat.py`** — Existing test file for heartbeat tests. Add tests for the new silence logging.
- **`artifacts/developer/telegram_bot/tests/test_silence_start.py`** — Existing test file for silence_start behavior.

#### Patterns and Conventions

- **Instance variables in __init__**: Follow the existing pattern — `self.silence_start` is at line 188, `self._sent_15s_status` at line 189. Add the new counter nearby.
- **time.monotonic()**: All timing uses `time.monotonic()`, not `time.time()`. See lines 187-188, 403-407.
- **Logger**: Use `logger` (module-level, line 20).

#### Dependencies and Integration Points

- **`silence_start` already exists** (line 188): Initialized to `time.monotonic()` in `__init__`, reset in `_read_stdout()` at line 405. No need to add this — it is already implemented.
- **`_read_stdout()` (lines 391-421)**: This is where the filtered event counter must be incremented (when `_extract_text_from_event` returns `None`) and reset (when it returns text). The counter increment goes at line 417 (the `if text:` check) — increment on the else branch, reset on the if branch.
- **`_typing_heartbeat()` (lines 487-513)**: This is where the silence summary log goes. Add it inside the `if elapsed >= _TYPING_HEARTBEAT_INTERVAL:` block (line 504), before or after the typing indicator send.
- **`_sent_15s_status` / `_sent_60s_status` (lines 189-190)**: These flags are for progress status messages (a separate feature). The silence summary logging is independent — it logs EVERY heartbeat during silence, not just at 15s/60s thresholds.
- **Interacts with info-level-event-logging ticket**: Both tickets add INFO-level logging to the stdout pipeline. They are complementary — info-level-event-logging logs individual events, while this ticket logs aggregate silence summaries. No conflicts, but implement info-level-event-logging first for consistency.

#### Implementation Notes

1. **Add filtered event counter to `__init__`** (near line 190):
   ```python
   self._filtered_event_count: int = 0
   ```

2. **Update `_read_stdout`** (around lines 416-421):
   ```python
   text = _extract_text_from_event(raw)
   if text:
       self._filtered_event_count = 0  # Reset on successful extraction
       try:
           await self._on_response(self.chat_id, text)
       except Exception:
           logger.exception("on_response callback raised.")
   else:
       self._filtered_event_count += 1
   ```

3. **Update `_typing_heartbeat`** (inside the `if elapsed >= _TYPING_HEARTBEAT_INTERVAL:` block, around line 504):
   ```python
   silence_duration = time.monotonic() - self.silence_start
   if silence_duration > 0:
       logger.info(
           "Agent %s silent for %ds, %d events received but filtered (chat %d)",
           self.agent_name,
           int(silence_duration),
           self._filtered_event_count,
           self.chat_id,
       )
   ```

4. **Gotcha — silence_start resets on ANY stdout line**: `silence_start` is reset at line 405 on every stdout line, even filtered ones. This means "silence duration" measures time since ANY output, not time since last TEXT output. This is actually correct for the purpose — if events are arriving but no text is extracted, silence_duration will be very small (near 0), but `_filtered_event_count` will be high. The log line will still appear (since silence_duration > 0 is almost always true during heartbeat, as 5 seconds pass between checks). If you want silence_duration to measure time since last TEXT extraction instead, you'd need a separate timestamp. Consider which interpretation is more useful.

5. **Alternative interpretation**: If silence_start should track time since last TEXT (not any output), do NOT reset it on every stdout line. Instead, only reset it when text is extracted. This would require moving the reset from line 405 to inside the `if text:` block. But this changes the existing behavior of `_sent_15s_status` and `_sent_60s_status` which also depend on `silence_start`. Leave existing behavior unchanged — the current reset-on-any-output is correct for typing indicators and progress messages. For the logging, compute silence from last_activity which already tracks the right thing.

### Design Context

The typing heartbeat currently fires invisibly with no diagnostic output. During long agent operations, there is no way to tell whether events are being received and filtered versus the agent producing nothing at all. This change turns the heartbeat into an actionable diagnostic signal. Depends on `silence_start` timestamp tracking which is already implemented. See artifacts/designer/design.md, "Silence Period Summary Logging" subsection under "Diagnostic Logging".
