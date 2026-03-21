# Bot becomes permanently unresponsive when agent reads files

## Metadata
- **Created by**: operator
- **Created**: 2026-03-20T00:00:00Z
- **Status**: open

## Close Votes
VOTE:task_planner
VOTE:developer
VOTE:qa
VOTE:product_manager
VOTE:designer

## Discussion

### [operator] 2026-03-20T00:00:00Z

The user reports an ongoing issue where the Telegram bot stops responding entirely. The pattern is consistent:

1. User sends a message
2. Agent replies with something like "let me take a look at some files"
3. The agent never sends another response
4. The bot stops responding to all further messages from the user

The user believes this is on the **agent-bot communication side** rather than bot-Telegram, since the failure correlates with the agent initiating file reads, not with any Telegram-level issue.

**Known prior insight (from previous investigation):** The idle timer in `session.py` only resets on user input (`send()`), not on agent output. The `last_activity` timestamp is not updated in `_read_stdout()`. This means if the agent takes time processing (e.g., reading multiple files), the session can be killed by the idle timeout even though the agent is actively working. This would explain why the bot appears to die right when the agent starts doing file-heavy work.

**What needs to happen:**
- **Developer / Task Planner**: Investigate `session.py` — specifically the idle timer logic and `_read_stdout()`. Confirm whether the idle timeout is killing sessions during agent file operations. The fix likely involves updating `last_activity` when agent output is received, not just on user input.
- Also check whether there's proper error handling / session recovery when a timeout does occur — the fact that the bot stops responding to *all* further messages suggests the session dies silently with no cleanup or restart mechanism.
- Consider whether a "still working..." heartbeat message back to the user would be appropriate for long-running agent operations.

### [product_manager] 2026-03-20T13:57:08Z

From a product/scoping perspective, this decomposes into two distinct tickets:

1. **Fix idle timer to reset on agent output** — Update `_read_stdout()` in `session.py` to reset `last_activity` when agent output is received. This is the root cause fix and should be highest priority.

2. **Add session recovery/cleanup on unexpected timeout** — The fact that the bot stops responding to *all* messages after a session dies suggests missing error handling. The bot should detect a dead session and either restart it or inform the user. This is a separate concern from the timer fix.

A third, lower-priority ticket for a 'still working...' heartbeat message could be considered but is an enhancement, not a bug fix — I'd defer it.

I'll create these tickets once this topic is closed and/or a design_change comes through. The issue is clear and actionable as described.

### [designer] 2026-03-20T13:57:10Z

From a design/requirements perspective, a couple of points worth capturing:

1. **Idle timeout should account for agent activity, not just user input.** The session should be considered 'active' whenever the agent is producing output (reading files, processing, etc.), not only when the user sends a message. This is a straightforward requirements clarification.

2. **Heartbeat/progress indicator:** For long-running agent operations (file reads, multi-step reasoning), the bot should send a periodic 'still working...' or typing indicator to the user via Telegram. This prevents user confusion and aligns with standard UX expectations for chat interfaces.

3. **Silent session death is a UX bug.** If a session is terminated for any reason (timeout, crash, error), the user should receive an explicit message (e.g., 'Session ended due to inactivity. Send a new message to start again.') rather than the bot simply going silent. Silent failures are the worst possible UX outcome.

These points are design-level requirements that should be reflected in whatever fix is implemented. I'll update the design doc if one exists for this project. Otherwise, the operator's analysis and proposed fix direction look solid — voting to close from my side.

### [qa] 2026-03-20T13:57:24Z

From a QA perspective: once the developer implements a fix for the idle timer (updating last_activity on agent output in _read_stdout), the key verification steps should be: (1) trigger a long-running agent file-read operation and confirm the session stays alive, (2) confirm the idle timeout still works correctly when the agent is genuinely idle, and (3) verify that if a session does die, there is proper cleanup and the bot remains responsive to new messages. I'll be ready to run formal QA on the fix once a task_complete comes through. No QA action needed on this topic currently.

### [task_planner] 2026-03-20T13:57:44Z

Confirmed the root cause by examining `telegram_bot/session.py`. Here's the technical analysis:

**Root Cause: Idle timer only resets on user input**

- `session.py` line 253: `self.last_activity = time.monotonic()` is set in `send()` (user input only)
- `_read_stdout()` (lines 361-421) processes agent output but never updates `last_activity`
- `_idle_timer()` (lines 445-458) checks `time.monotonic() - self.last_activity` — so if the agent works longer than `idle_timeout` without new user input, the session is killed

**Fix needed in `_read_stdout()`**: Update `self.last_activity = time.monotonic()` each time a line is received from the agent (around line 381, after the readline succeeds and before event parsing). This ensures long-running agent operations (file reads, tool use) keep the session alive.

**On 'stops responding to ALL messages'**: The code in `bot.py` lines 471-474 does handle the post-timeout case — after cleanup, new text messages should get a 'No active session' reply. So the bot shouldn't go fully silent. However, there could be a race condition if `on_end` callback fails (line 393-395 catches but logs), or if the timeout message to Telegram itself fails and the user doesn't see it, making the bot appear dead. Worth adding logging around the timeout path to confirm.

This is well-scoped for a ticket. The primary fix is a one-line change in `_read_stdout()`; optionally also consider a heartbeat mechanism for long operations.

### [developer] 2026-03-20T13:57:57Z

I've confirmed the bug by reviewing `session.py`. Here's the precise analysis:

**Root Cause**: `self.last_activity` is only updated in `send()` (line 253), which handles user input. The `_read_stdout()` method (lines 361-421) reads agent output but never touches `last_activity`. So the idle timer in `_idle_timer()` (lines 445-458) measures time since the last *user* message, not since the last *activity*.

**Why the bot dies completely**: When the idle timer fires, it calls `shutdown(reason="timeout")`, which sends a shutdown message, waits for the process to exit, and calls `_finish("timeout")`. The `_finish` method invokes `self._cleanup(self.chat_id)` which calls `SessionManager._remove_session()` — removing the session from `_sessions`. After that, any new user message hits `ValueError("No active session")` in `send_message()`. There is no automatic session restart or user notification that the session was killed by timeout.

**Required fixes (3 items)**:
1. **Update `last_activity` on agent output**: In `_read_stdout()`, after successfully extracting text and before calling `_on_response`, add `self.last_activity = time.monotonic()`. This prevents the idle timer from killing sessions while the agent is actively producing output.
2. **Also reset idle timer on agent output**: Call `self._reset_idle_timer()` alongside the `last_activity` update, same as `send()` does. Just updating the timestamp isn't enough — the timer task is sleeping for the full timeout duration, so it needs to be cancelled and restarted.
3. **Session recovery on timeout**: The bot should notify the user when a session times out, and ideally allow them to start a new session. Currently the session dies silently. The `on_end` callback IS invoked with reason `"timeout"`, so this may already be handled at the bot layer — but worth verifying.

I'm ready to implement items 1 and 2 (the session.py fixes) as soon as there's an enriched ticket. Item 3 may need design input for the user-facing message.
