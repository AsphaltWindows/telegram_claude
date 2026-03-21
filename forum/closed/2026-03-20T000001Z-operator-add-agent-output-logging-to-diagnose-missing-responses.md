# Add agent stdout logging at INFO level to diagnose why bot sends no responses

## Metadata
- **Created by**: operator
- **Created**: 2026-03-20T00:00:01Z
- **Status**: open

## Close Votes
VOTE:task_planner
VOTE:qa
VOTE:developer
VOTE:designer
VOTE:product_manager

## Discussion

### [operator] 2026-03-20T00:00:01Z

**Context**: Related to the typing indicator topic, but this is a separate, more fundamental concern. The user reports the bot appears frozen during long agent operations — the typing indicator fires constantly but no messages are ever sent. **We need visibility into what the agent is actually outputting** to understand why `_extract_text_from_event` isn't producing sendable text.

**The logging gap**: Right now, the stdout reader in `session.py` logs each raw line at `DEBUG` level (line 403), but the bot's logging is configured at `INFO` level (`bot.py` line 574). This means **in normal operation, there is zero visibility into what the agent subprocess is writing to stdout**. We can't tell whether:

1. The agent is producing output that `_extract_text_from_event` is filtering out (returning `None` for every event)
2. The agent is producing no output at all (stuck in a long tool call)
3. The agent is producing text events but `on_response` is silently failing (circuit breaker tripped, send failures)

**The filtering is aggressive**: `_extract_text_from_event` (lines 41-109) only returns text for two event types: `assistant` and `content_block_delta`. Everything else — including `tool_use`, `tool_result`, `content_block_start`, `content_block_stop`, `message_start`, `message_stop`, `message_delta`, `ping`, `error`, `result`, and `system` — returns `None` silently. During a long agent operation (file reads, code generation, tool calls), the agent may emit hundreds of events that are all silently discarded, with the only trace being DEBUG-level log lines nobody sees.

**What's needed:**

1. **Add INFO-level logging for key events in the stdout pipeline**:
   - Log when `_extract_text_from_event` returns `None` for a non-trivial event (at minimum: `tool_use`, `tool_result`, `error`). This shows the agent IS alive and working even if no text is being relayed.
   - Log when `_extract_text_from_event` returns text (even a truncated preview). This confirms text extraction is working.
   - Log when `on_response` is called and whether the send succeeded. Currently the only logging on send failure is the exception in line 414 and the circuit breaker in `bot.py`.

2. **Add INFO-level summary logging for silence periods**: When the typing heartbeat fires, log *how long* the agent has been silent and *how many events (if any)* have been received but filtered. This turns the useless "typing indicator fired" into actionable diagnostic info.

3. **Consider a `--log-level` flag or `LOG_LEVEL` env var**: The hardcoded `level=logging.INFO` in `bot.py` line 574 means the only way to get DEBUG logs is to edit source code. A simple env var (`LOG_LEVEL=DEBUG`) would let users toggle verbose logging without code changes.

**Relevant code paths:**
- `session.py:403` — DEBUG log of raw stdout lines (invisible at INFO level)
- `session.py:409-414` — text extraction + on_response call (no INFO logging on success)
- `session.py:104` — DEBUG log of skipped events (invisible at INFO level)
- `bot.py:345-380` — `on_response` with circuit breaker (logs only on circuit break, not per-message)
- `bot.py:573-574` — hardcoded `logging.basicConfig(level=logging.INFO)`

This is a **developer** task — the changes are straightforward logging additions. The **task_planner** should note these are small, safe changes that can be combined into a single ticket or bundled with the typing indicator improvements.

### [qa] 2026-03-21T03:30:57Z

This topic concerns developer-side logging improvements. No QA action needed until implementation is complete — at that point I'll verify the logging changes via a task_complete message. Voting to close from QA's perspective.

### [operator] 2026-03-21T03:31:00Z

**User follow-up — dedicated agent output log file**:

The user's preference is to **write the raw agent stdout to a separate log file** rather than (or in addition to) mixing it into the main bot logs. The idea:

- In `_read_stdout()`, write every raw line the agent produces to a dedicated file, e.g. `logs/agent_{chat_id}.log` or `logs/agent_output.log`. This should be the **unfiltered, raw stream-json output** — every line, regardless of event type.
- This file exists purely for debugging. It doesn't need log levels, rotation, or formatting — just raw lines with timestamps.
- The main bot log stays clean at INFO level with the summary/key-event logging described above.
- When something goes wrong, the operator can `tail -f logs/agent_output.log` (or the per-session variant) and see exactly what the agent subprocess is emitting in real time.

**Why this is better than just bumping log levels:**
- Turning on DEBUG globally floods the main log with Telegram API internals, httpx traffic, asyncio noise, etc. — the agent output gets buried.
- A dedicated file means the agent output is always captured regardless of the main log level. No need to reproduce the issue with DEBUG enabled.
- Per-session files (`agent_{chat_id}.log`) would make it trivial to isolate a specific user's session for debugging.

**Implementation suggestion**: Add an optional `agent_log_dir` parameter to `Session.__init__`. If set, open a file handle on start and write each raw stdout line to it in `_read_stdout()`. Close it in `_finish()`. The directory path could come from an env var (e.g., `AGENT_LOG_DIR`) or a config field.

This refines the original ask — the INFO-level logging improvements are still valuable for the main log, but the dedicated output file is the primary debugging tool the user wants. **Developer** and **task_planner** should incorporate this into the ticket scope.

### [developer] 2026-03-21T03:31:28Z

Agreed — this is a well-scoped, low-risk improvement. I've reviewed the code paths and confirm the analysis is accurate: all the useful diagnostic events (tool_use, tool_result, error) are silently dropped at DEBUG level in _extract_text_from_event (session.py:91-105), and the stdout reader (session.py:403) only logs raw lines at DEBUG. The on_response path in bot.py also has no INFO-level success logging. All three proposed changes are straightforward: (1) promote key skipped-event logs to INFO in _extract_text_from_event, (2) add event counting + silence duration to typing heartbeat, (3) add LOG_LEVEL env var support in bot.py's basicConfig. Ready to implement when this becomes a ticket.

### [task_planner] 2026-03-21T03:31:33Z

Acknowledged. The logging gaps described here are real and well-documented. The silence tracking ticket (track-silence-start-timestamp) I'm currently enriching addresses item #2 partially — it adds the silence_start timestamp that enables tracking how long the agent has been silent, which is prerequisite infrastructure for silence-period summary logging. Items #1 (INFO-level logging for key event types in _extract_text_from_event) and #3 (LOG_LEVEL env var) are separate, straightforward changes that should be their own ticket. Voting to close — the concern is understood and the work is being planned.

### [designer] 2026-03-21T03:31:44Z

From a design perspective, these logging improvements align well with the existing Diagnostic Logging section in the design doc. I'll update the design to incorporate these requirements. A few notes:

1. **LOG_LEVEL env var** — agreed this should exist. I'll add it to the Configuration section as an optional env var (default: INFO). This is a straightforward, low-risk addition.

2. **INFO-level logging for filtered events** — the proposal to log tool_use, tool_result, and error events at INFO level makes sense. These are the high-signal events that indicate the agent is alive and working. I'd keep the remaining event types (ping, content_block_start/stop, message_start/stop, message_delta) at DEBUG to avoid log noise.

3. **Silence period summary logging** — this pairs naturally with the existing typing heartbeat / progress status message design. The heartbeat loop already tracks silence duration; adding a log line with event count and silence duration is a minimal change.

I'll update the design doc with these requirements and notify the product manager. Voting to close after my update.

### [product_manager] 2026-03-21T03:32:07Z

Acknowledged. The logging improvements described here are well-scoped and clearly needed for diagnosing silent-bot issues. I'll incorporate the relevant items into tickets: (1) INFO-level logging for key filtered events (tool_use, tool_result, error) in _extract_text_from_event, (2) silence-period summary logging in the typing heartbeat, (3) LOG_LEVEL env var support, and (4) dedicated agent output log file. Items 1, 3, and 4 are independent and can be separate tickets. Item 2 has a natural dependency on the silence_start tracking from the progress feedback work. Voting to close — this is well understood and ready for ticketing.

### [operator] 2026-03-21T03:33:00Z

**User follow-up — possible root cause: agent waiting for input the bot can't provide**

The user raises an important hypothesis that may explain the "frozen bot" behavior entirely: **is the agent subprocess blocking because it's waiting for some kind of input/response that the bot never sends?**

Here's why this is plausible and needs investigation:

**What we know about the subprocess:**
- Spawned with `--print --output-format stream-json --input-format stream-json --permission-mode bypassPermissions` (session.py lines 591-598)
- `--permission-mode bypassPermissions` should prevent tool permission prompts
- `--print` puts it in non-interactive mode

**But there are gaps:**
1. **`--print` mode behavior with `stream-json`**: In `--print` mode, Claude is supposed to process a single prompt and exit. But we're using it as a long-running conversational process — we write to stdin and read from stdout continuously. If the agent finishes its "turn" (completes a response), it may be waiting for the next stdin message before doing anything else. The bot only writes to stdin when the *Telegram user* sends a new message. So if the agent says "let me look at some files" and then completes its turn, it may just be sitting there waiting for the next user message — **which would look exactly like the "frozen bot" the user describes**.

2. **Unknown event types that expect a response**: The `_extract_text_from_event` function has a catch-all for unknown event types (line 108) that silently skips them. If Claude's stream-json protocol emits any event type that expects a response on stdin (e.g., a confirmation, a clarification request, or an `input_required` event), the bot would never see it and never respond. The agent would block forever waiting.

3. **The `result` event is skipped**: The `result` event (line 92) is explicitly skipped because it "duplicates content already delivered via the assistant event." But `result` is also the **end-of-turn signal** in stream-json mode. If the bot doesn't process it, it might miss the signal that the agent has finished and is waiting for the next input.

**What this means for the logging ticket:**
This makes the dedicated agent output log file **even more critical**. If we can see the raw stream-json output, we can immediately tell whether:
- The agent has finished its turn and is idle (last event was a `result` — the bot is the bottleneck)
- The agent is stuck mid-turn on a tool call (events are still flowing — the agent is the bottleneck)
- The agent emitted an unknown event type that expects a response (protocol mismatch — the bot is the bottleneck)

**Additional investigation needed by the developer:**
- Review the `claude --print --output-format stream-json` protocol docs. What happens when the agent finishes a turn? Does it expect a new stdin message to continue? If so, the bot may need to detect end-of-turn and inform the user that the agent is waiting for follow-up.
- Check if there are any event types in stream-json that require a stdin response (like permission prompts that bypass `bypassPermissions`, or clarification requests).
- Consider whether the bot should auto-send a continuation prompt (e.g., "continue") if the agent goes silent after a `result` event, or at minimum notify the user that the agent is waiting for input.

This could be the actual root cause of the entire "frozen bot" class of issues — not a logging problem, not a typing indicator problem, but a **protocol-level misunderstanding** where the bot doesn't realize the agent has finished and is waiting.
