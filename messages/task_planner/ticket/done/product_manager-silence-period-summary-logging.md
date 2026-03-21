# silence-period-summary-logging

## Metadata
- **From**: product_manager
- **To**: task_planner

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

### Design Context

The typing heartbeat currently fires invisibly with no diagnostic output. During long agent operations, there is no way to tell whether events are being received and filtered versus the agent producing nothing at all. This change turns the heartbeat into an actionable diagnostic signal. Depends on `silence_start` timestamp tracking which may be implemented as part of the progress status messages work. See artifacts/designer/design.md, "Silence Period Summary Logging" subsection under "Diagnostic Logging".
