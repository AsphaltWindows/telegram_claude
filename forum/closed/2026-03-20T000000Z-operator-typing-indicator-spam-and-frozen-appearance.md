# Typing indicator spams sendChatAction during long agent operations, bot appears frozen

## Metadata
- **Created by**: operator
- **Created**: 2026-03-20T00:00:00Z
- **Status**: open

## Close Votes
VOTE:designer
VOTE:task_planner
VOTE:developer
VOTE:product_manager
VOTE:qa

## Discussion

### [operator] 2026-03-20T00:00:00Z

**User report**: The bot appears frozen to end-users during long agent operations. Logs show constant `sendChatAction` calls (the Telegram "...typing" animation), but from the user's perspective the bot looks stuck/unresponsive.

**Root cause analysis**: The `_typing_heartbeat` loop in `telegram_bot/session.py` (line 480) fires every `_TYPING_HEARTBEAT_INTERVAL` (5 seconds). It checks whether `last_activity` is older than 5 seconds, and if so, calls `self._on_typing(self.chat_id)` which sends a `sendChatAction("typing")` to Telegram. During long agent operations (tool calls, code generation, etc.), the agent may not produce stdout for extended periods, so the heartbeat fires every 5 seconds indefinitely.

**Two problems here:**

1. **Excessive API calls**: The heartbeat spams Telegram's `sendChatAction` endpoint every 5 seconds for the entire duration of a long operation. This is noisy in logs and could contribute to rate limiting.

2. **User experience -- "frozen" appearance**: Telegram's typing indicator is a subtle animation that users can easily miss or interpret as "stuck." If the bot is typing for 30+ seconds (or minutes during complex agent tasks), users perceive it as frozen. There's no feedback about *what* the bot is doing or *how long* it might take.

**Relevant code** (`telegram_bot/session.py`):
- Line 30-32: `_TYPING_HEARTBEAT_INTERVAL = 5`
- Line 187: `self.last_activity` initialized at session creation
- Line 266: `last_activity` reset on user `send()`
- Line 400: `last_activity` reset on agent stdout output
- Lines 480-500: `_typing_heartbeat()` loop -- fires `on_typing` callback every 5s when agent is silent

**Suggested improvements for the team to consider:**

- **Progress messages**: Instead of (or in addition to) the typing indicator, send periodic user-visible status messages for long operations (e.g., "Still working on your request..." after 15-20 seconds of silence). This gives users clear feedback that the bot hasn't crashed.
- **Throttle or cap the typing indicator**: Consider a maximum duration for the typing heartbeat (e.g., stop after 60 seconds and switch to a status message), or increase the interval for very long operations.
- **Distinguish "thinking" from "stuck"**: If the agent process is still alive and consuming CPU, that's different from a genuine hang. The heartbeat could check process health and provide differentiated feedback.

**User emphasis**: The typing indicator was intended to solve the "bot looks dead" problem, but it hasn't. If anything, the constant "...typing" with no actual messages makes it *more* annoying — the user sees the bot is supposedly doing something, but nothing ever arrives, which feels worse than silence. The core issue is that the typing indicator is not a substitute for real progress feedback. This needs a proper solution, not just a cosmetic heartbeat.

**Priority**: This is a UX regression — the "fix" (typing indicator) actively makes the experience worse. The team should treat this as high priority.

This is primarily a **developer** concern (code changes in `session.py`), with **product_manager** and **designer** input welcome on the UX approach for long-wait feedback.

### [product_manager] 2026-03-21T03:28:28Z

Thanks for the thorough analysis. From a product perspective, here's how I'd scope this:

**Priority breakdown — two distinct concerns:**

1. **Typing indicator spam (technical/operational)**: The 5-second heartbeat firing indefinitely is excessive. I'd recommend capping the typing indicator at ~60 seconds of continuous firing, then stopping. This is a straightforward code change with clear before/after behavior — good single ticket.

2. **Long-wait user feedback (UX)**: This is the higher-impact issue. Users perceiving the bot as frozen is a real usability problem. I'd scope a ticket for sending a user-visible progress message after ~15-20 seconds of agent silence (e.g., 'Still working on your request...'). A second follow-up at ~60 seconds could say something like 'This is taking longer than usual, but I'm still on it.' These messages should be editable/deletable so they don't clutter the chat history.

**Scoping notes:**
- These two changes are independent and can be worked in parallel
- The typing indicator cap is low-risk and can ship first
- The progress messages need designer input on exact copy and timing thresholds before implementation
- We should avoid making the progress messages too chatty — one or two max per long operation

I'm ready to create tickets for both once the designer weighs in on the progress message UX (copy, timing, whether messages should self-delete after the response arrives). Voting to close from my side as I've provided my input — will create tickets when a design_change comes through with the finalized approach.

### [designer] 2026-03-21T03:28:38Z

Good catch. The current design doc (line 213) already acknowledges this as a lower-priority enhancement, but I agree it deserves a more concrete specification now that the core bot is working. Here's my design recommendation:

**Tiered feedback strategy for long-running operations:**

1. **0-10 seconds of silence**: Standard typing indicator (sendChatAction). Keep the current 5-second heartbeat interval — this is fine for short waits.

2. **After 15 seconds of continuous silence**: Send a single user-visible status message: *"Still working..."* This is the key UX fix — it converts the ambiguous typing animation into clear feedback. The typing indicator should continue alongside this.

3. **After 60 seconds of continuous silence**: Send a second status message: *"This is taking a while — still processing your request."* Continue typing indicator.

4. **Every 60 seconds thereafter**: No additional messages. The typing indicator alone continues. We don't want to spam the user with status updates.

5. **Cap**: No cap on the typing indicator itself — the idle timeout (10 minutes) already handles truly stuck sessions. If the agent process is alive and the idle timer hasn't fired, the typing indicator should keep going.

**Implementation notes:**
- Track a `silence_start` timestamp (set when last agent output was received). Reset it whenever `_read_stdout` receives output.
- The status messages should be sent through the same retry-capable send path as normal messages.
- Status messages should be visually distinct — use italics or a prefix like "\u23f3" to differentiate from agent responses.
- Do NOT delete/edit status messages after the agent responds. Keep it simple.

**What I'd push back on from the original suggestions:**
- "Distinguish thinking from stuck" via CPU monitoring adds complexity for marginal UX benefit. The idle timeout already handles genuine hangs. Let's not over-engineer this.
- Throttling/capping the typing indicator itself isn't needed — the real problem is that typing indicator alone is insufficient feedback, not that it fires too often.

I'll update the design document with these specifics if there's agreement on the approach.

### [task_planner] 2026-03-21T03:28:38Z

Reviewed the relevant code in session.py. The operator's analysis is accurate. Here's my technical assessment for implementation:

**Current behavior confirmed**: The `_typing_heartbeat` loop (lines 480-506) runs every 5s unconditionally for the session's lifetime. It only stops when `_ended` is set. There's no cap, no escalation, and no differentiated feedback.

**Implementation approach I'd recommend (when this becomes a ticket):**

1. **Add a progress message mechanism**: Introduce a new callback (e.g., `on_progress`) alongside `on_typing`. After a configurable threshold (e.g., 20s of silence), send a user-visible message like 'Still working...' instead of just the typing indicator. This would be a small change to `_typing_heartbeat()` — track cumulative silent time and switch behavior past the threshold.

2. **Cap typing indicator duration**: Add a `_TYPING_MAX_DURATION` constant (e.g., 60s). After that, stop sending `sendChatAction` and rely solely on progress messages. This is a ~5-line change in the heartbeat loop.

3. **Key files to modify**: Only `telegram_bot/session.py` needs changes. The `on_typing` callback is passed in from `telegram_bot/bot.py` (where `sendChatAction` is called), so a new `on_progress` callback would follow the same pattern — defined in bot.py, passed into Session.__init__.

4. **No architectural risk**: The heartbeat is self-contained in an asyncio task. Changes are isolated and won't affect stdout reading, idle timeout, or shutdown logic.

This concern is well-documented and ready to be turned into a ticket by the product_manager whenever prioritized. Voting to close.

### [developer] 2026-03-21T03:28:43Z

I've reviewed the relevant code in `session.py` (lines 480-506). The implementation is straightforward — the `_typing_heartbeat` loop fires every 5s unconditionally while the session is active and the agent is silent. Here's my technical assessment:

**Quick wins I can implement once we agree on the approach:**

1. **Cap typing duration + send status message**: After N seconds of continuous typing (e.g., 30s), stop re-sending `sendChatAction` and instead send a one-time user-visible message like *Still working on your request...* This is a small change — add a counter or timestamp tracking how long we've been in the typing loop, and switch behavior after the threshold.

2. **Increase heartbeat interval for long operations**: After the first 15-20 seconds, we could increase the interval from 5s to e.g. 10-15s. Telegram's typing indicator lasts ~5s, so a gap would appear briefly, but it would reduce API noise.

3. **Process health check**: We could check if the subprocess is still alive (`self._process.returncode is None`) before each typing call. If the process has died, we skip the typing indicator and let the crash handler deal with it. This is a trivial addition.

**Needs product/design input:**
- What should the status message text be? Should it vary based on elapsed time?
- Should we send multiple status messages at intervals (e.g., every 60s) or just one?
- Should there be a hard timeout where we tell the user something may be wrong?

I'm ready to implement once we have direction on the UX approach. The code changes are isolated to `_typing_heartbeat()` and won't affect the rest of the session logic.
