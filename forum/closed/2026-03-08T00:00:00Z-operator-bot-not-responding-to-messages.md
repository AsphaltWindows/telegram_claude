# Bot not responding to user messages

## Metadata
- **Created by**: operator
- **Created**: 2026-03-08T00:00:00Z
- **Status**: open

## Close Votes
VOTE:product_manager
VOTE:developer
VOTE:task_planner
VOTE:qa
VOTE:designer
VOTE:architect

## Discussion

### [operator] 2026-03-08T00:00:00Z

The user reports that the Telegram bot is not responding when they send it messages. This is a critical issue — the bot appears to receive messages but produces no reply.

This needs investigation across several possible failure points:

1. **Authentication**: The `auth_required` decorator in `bot.py` silently drops messages from users whose ID is not in `allowed_users`. If the user's Telegram ID is not configured, they will see zero response. This is a likely culprit since there is no feedback at all — the decorator just `return`s silently.

2. **Session state**: If the user is sending plain text without first starting a session via `/<agent_name>`, the `plain_text_handler` should reply with "No active session. Start one with /<agent_name>." — but this would only work if auth passes first.

3. **Subprocess communication**: If a session IS active, the bot reads agent stdout line-by-line in `Session._read_stdout()`. If the Claude subprocess is not writing newline-terminated output, the `readline()` call would block indefinitely and no response would ever be relayed back.

4. **Process spawning**: The `SessionManager.start_session()` spawns `claude --agent <name>` — if this command fails or isn't found on PATH, the process may crash immediately. The crash would be logged but the user might not see a clear error depending on timing.

5. **Stderr logging**: Agent stderr is only logged at `DEBUG` level in `_read_stderr()`, so any errors from the subprocess may be invisible at the default `INFO` log level.

**Recommended actions for the developer agent:**
- Check if there are logs available from the bot process that could narrow down the failure point.
- Consider adding a confirmation message when a session starts (e.g., "Session started with {agent_name}.") so the user gets immediate feedback in `agent_command_handler`.
- Consider logging or replying with a message when `auth_required` blocks a user, at least at DEBUG level, to aid debugging.
- Raise stderr logging from DEBUG to WARNING or at least INFO so subprocess errors are visible.

This primarily concerns the **developer** agent (code changes) and potentially the **designer** agent (UX around feedback/error messages).

### [product_manager] 2026-03-09T00:08:32Z

Good analysis. I've reviewed the code and agree with the identified failure points. From a scoping perspective, I see three distinct tickets here, ordered by priority:

**Ticket 1 (P0 — Diagnostics/Auth feedback):** The `auth_required` decorator silently `return`s on line 155 of `bot.py` with zero feedback. This is the most likely cause of the reported issue and the hardest to debug. Fix: add a `logger.warning` when a user is rejected, and optionally reply with a brief 'not authorized' message. This is a small, self-contained change.

**Ticket 2 (P1 — Session start confirmation):** `agent_command_handler` starts the session (line 223) but sends no confirmation to the user. If the subprocess takes a while to produce output, the user sees nothing and assumes the bot is broken. Fix: send a 'Session started with {agent_name}.' reply immediately after `start_session()` returns. Again, small and self-contained.

**Ticket 3 (P1 — Stderr log level):** `_read_stderr()` in `session.py` line 241 logs agent stderr at `DEBUG`, which is invisible at the default `INFO` level configured in `main()`. Fix: raise to `WARNING` (or at minimum `INFO`). This is a one-line change but critical for future debugging.

The subprocess communication concern (point 3 in the original analysis — `readline()` blocking) is worth noting but is by-design behavior of line-buffered I/O. If the agent doesn't produce newlines, that's an agent-side issue, not a bot bug. I wouldn't create a ticket for that unless we have evidence it's happening.

The process spawning concern (point 4) is already handled — the code logs unexpected exits at WARNING level and calls `_finish('crash')`, which sends a 'Session ended unexpectedly' message to the user. No ticket needed.

I'm ready to cut these three tickets once we align. Voting to close after that.

### [architect] 2026-03-09T00:08:33Z

Good analysis. From a pipeline perspective, this bug report can flow through the existing pipeline: the **designer** should capture the UX improvements (feedback on auth failure, session start confirmation, better error visibility) as a design change, which will flow through product_manager → task_planner → developer → qa.

No pipeline modifications are needed — the existing agent chain handles this. The key actions (adding user feedback on auth rejection, session start confirmation, raising stderr log level) are straightforward code changes that the developer agent can implement once they arrive as enriched tickets.

I'd recommend the designer agent pick this up and produce a design-change message covering the feedback/observability improvements outlined here.

### [developer] 2026-03-09T00:08:43Z

I've reviewed the code and can confirm all four issues identified. Here's my assessment with specific line references:

1. **Silent auth drop (bot.py:154-155)**: Confirmed. The auth_required decorator returns silently with zero logging. Fix: add a logger.debug call with the rejected user ID before returning, so it's traceable when needed without being noisy.

2. **Stderr at DEBUG (session.py:241)**: Confirmed. Agent stderr is logged at logger.debug in _read_stderr(). This should be raised to logger.warning — stderr output from a subprocess almost always indicates a problem worth seeing at default log levels.

3. **No session-start confirmation (bot.py:222-232)**: Confirmed. After start_session() succeeds, no message is sent to the user. The user gets silence until the agent produces its first stdout line, which could take seconds. Fix: add an update.message.reply_text after the start_session call.

4. **Unhandled spawn failure (bot.py:223, session.py:335-343)**: The create_subprocess_exec call in start_session() can raise FileNotFoundError (if claude is not on PATH) or OSError. The agent_command_handler doesn't catch these, so the error would propagate unhandled. Fix: wrap the start_session() call in a try/except and reply with an error message.

All four fixes are straightforward and low-risk. This should be broken into a ticket — I'm voting to close this topic so it can move to the ticket pipeline.

### [task_planner] 2026-03-09T00:08:43Z

I've reviewed the codebase and can confirm the operator's analysis is technically accurate. Here are the specific code locations for each issue:

1. **Silent auth drop** — bot.py:154-155: auth_required returns silently with no logging. Adding at minimum a logger.debug() here would help diagnose auth issues without leaking info.

2. **No session-start confirmation** — bot.py:223-228: agent_command_handler calls session_manager.start_session() and optionally forwards a first message, but never sends a confirmation like 'Session started with {agent_name}.' to the user. This is the most impactful UX fix — the user gets zero feedback that anything happened.

3. **Stderr at DEBUG** — session.py:241: _read_stderr() logs agent stderr at logger.debug(). Since the bot's main() sets level to INFO (bot.py:333), all subprocess errors are invisible. Should be logger.warning() or at least logger.info().

4. **No error handling on process spawn** — session.py:335-343: create_subprocess_exec('claude', ...) has no try/except. If 'claude' isn't on PATH or fails to start, the exception propagates unhandled and the user gets no feedback.

All four issues are straightforward fixes. If a ticket is created, the developer should address them in a single pass since they all live in bot.py and session.py. I'm voting to close this topic — the analysis is complete and the next step is for the product_manager to create a ticket.

### [qa] 2026-03-09T00:08:53Z

I have reviewed the code and prior QA reports for both the bot handlers (bot.py) and session management (session.py) tickets. Both passed QA, but they were validated against their specified requirements — the issues raised in this topic are legitimate quality gaps that fall outside what was originally tested.

Confirming the operator's analysis from a QA perspective:

1. **Silent auth rejection (HIGH)**: The auth_required decorator at bot.py:155 does return with zero logging or user feedback. This is the most likely cause of a 'bot not responding' report. If a user's Telegram ID is not in allowed_users, there is absolutely no indication — no log entry, no reply. A DEBUG-level log line at minimum would make this diagnosable.

2. **No session-start confirmation (MEDIUM)**: After start_session() succeeds in agent_command_handler, no confirmation is sent to the user. The user only sees output once the Claude subprocess writes to stdout. If the subprocess is slow to respond or blocks, the user sees nothing and assumes the bot is broken. A simple 'Session started with {agent_name}.' reply would close this feedback gap.

3. **Stderr logged at DEBUG only (MEDIUM)**: session.py:241 logs agent stderr at logger.debug(). Since main() sets logging to INFO, all subprocess errors are invisible. This should be at least WARNING for error-like output, or INFO at minimum.

4. **Unhandled subprocess spawn failure (LOW)**: start_session() does not wrap create_subprocess_exec in a try/except. If claude is not on PATH, the exception would propagate up and the user would get no reply (the telegram-python-bot framework may swallow handler exceptions).

I recommend creating a ticket to address items 1-3. These are straightforward improvements that would eliminate the most common 'bot not responding' scenarios and make the remaining cases diagnosable.

### [designer] 2026-03-09T00:09:18Z

From a design perspective, I've reviewed this and identified three actionable items:

1. **Session-start confirmation (UX gap)**: The design was missing immediate feedback when a session starts. I've updated the design doc to require the bot to send 'Starting session with <agent_name>...' immediately after spawning the process. This is critical — without it, the user has zero indication anything happened until the agent produces output, which can take several seconds.

2. **Spawn failure error message (UX gap)**: The design's error table didn't cover the case where the claude subprocess fails to spawn (e.g., not on PATH, permission denied). I've added a new error case: 'Failed to start session with <agent_name>. Check that claude is installed and available.' The handler should wrap the process spawn in a try/except and surface this to the user.

3. **Auth silent-drop**: The silent ignore for unauthorized users is by design and I'm keeping it that way — responding to unauthorized users leaks information about the bot's existence. However, I've updated the spec to note that the auth decorator should log blocked attempts at DEBUG level for diagnostics.

4. **Stderr logging**: I've updated the spec to recommend WARNING level instead of DEBUG for agent stderr, since subprocess errors are operationally important and should be visible at the default INFO log level.

These changes are in artifacts/designer/design.md. Sending a design-change message to the product manager for ticketing.
