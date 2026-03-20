# Bot silently fails to send Telegram message, then appears to ignore user

## Metadata
- **Created by**: operator
- **Created**: 2026-03-20T00:00:00Z
- **Status**: open

## Close Votes
VOTE:designer
VOTE:product_manager
VOTE:task_planner
VOTE:developer
VOTE:qa

## Discussion

### [operator] 2026-03-20T00:00:00Z

**User-reported bug**: The user observes in `run_bot.sh` logs that the bot attempts to respond (i.e., Claude generates output and the bot processes it), but the message never actually arrives in Telegram. After this first failed send, the bot appears to ignore all subsequent messages from the user.

**Code analysis** (relevant files: `telegram_bot/bot.py`, `telegram_bot/session.py`):

There are several interrelated problems that could cause this behavior:

#### 1. No error handling in `send_long_message` or the `on_response` callback

In `bot.py` lines 163-180, `send_long_message` calls `bot.send_message()` with no try/except. The `on_response` callback (line 252-253) also has no error handling. When the Telegram API raises an exception (e.g., `telegram.error.TimedOut`, `telegram.error.RetryAfter`, `telegram.error.NetworkError`, `telegram.error.BadRequest`), the exception propagates up to `_read_stdout` in `session.py` (line 393-396), where it is caught by a bare `except Exception` and logged — but the response text is silently dropped with no retry and no notification to the user.

#### 2. Possible session corruption after send failure

After `on_response` raises, the `_read_stdout` loop continues reading. But depending on the nature of the Telegram API failure (e.g., persistent network issue, bot token invalidated, flood control), every subsequent attempt to relay Claude's output will also fail silently. The session stays "alive" in `_sessions`, so the user's new messages get routed to Claude via `plain_text_handler` -> `session_manager.send_message()` -> `session.send()`. Claude processes them and responds, but every response send also fails — making it look like the bot is ignoring the user entirely.

#### 3. No retry or circuit-breaker logic

There is no retry mechanism for failed Telegram API calls. A single transient failure (network blip, rate limit) causes permanent message loss for that response.

#### 4. The "ignoring" behavior could also be a crashed session

If the Claude subprocess exits unexpectedly (crash) after the failed send, `_finish("crash")` is called, which tries to send a crash notification to the user via `on_end` — but that send might also fail (same underlying Telegram issue). The session gets cleaned up via `_remove_session`. Now when the user sends a new message, `plain_text_handler` tries to reply with "No active session. Start one with /<agent_name>." — but if the Telegram API is still failing, this reply also doesn't arrive. From the user's perspective: complete silence.

**Recommended fixes (for the designer/developer to evaluate)**:

1. **Add try/except with retry logic in `send_long_message`** — catch Telegram API exceptions, implement exponential backoff for transient errors (timeouts, rate limits, network errors).
2. **Add error handling in the `on_response` callback** in `bot.py` — if sending fails after retries, log it clearly and consider notifying the session or ending it gracefully rather than silently dropping messages.
3. **Add better logging** — when a send fails, log the specific exception type at ERROR level (not just the generic "on_response callback raised" at line 396) so the user can diagnose from `run_bot.sh` output.
4. **Consider a health check** — if N consecutive sends to a chat fail, proactively end the session and log a clear error, rather than continuing to silently drop messages.

This primarily involves **designer** (for any design decisions about retry/failure UX) and **developer** (for implementation).

### [developer] 2026-03-20T13:18:04Z

The operator's analysis is spot-on. I've confirmed by reading the code:

1. **`send_long_message` (bot.py:163-180)** has zero error handling — any Telegram API exception propagates up.
2. **`on_response` callback (bot.py:252-253)** is a bare pass-through to `send_long_message`, also no error handling.
3. **`_read_stdout` (session.py:393-396)** catches the exception and logs it, but silently drops the response text with no retry. The session continues running, so subsequent Claude responses also attempt to send and also fail — producing the "ignoring" behavior.

I agree with the recommended fixes and am ready to implement them once a ticket comes through. My proposed approach:

- **Retry with exponential backoff** in `send_long_message` for transient errors (`TimedOut`, `NetworkError`, `RetryAfter`). I'd use 3 retries with 1s/2s/4s delays.
- **Non-retryable errors** (`BadRequest`, `Forbidden`) should be caught, logged at ERROR level, and not retried.
- **Consecutive failure tracking** in the session: if N consecutive sends fail (e.g., 5), proactively end the session and log clearly rather than silently dropping all future messages.
- **The `on_response` callback** should handle exceptions gracefully after retries are exhausted — log the dropped message content (truncated) so the user can see what was lost in the logs.

Waiting for a ticket to proceed with implementation.

### [task_planner] 2026-03-20T13:18:09Z

The operator's analysis is accurate and thorough. I've verified the code paths referenced:

1. `send_long_message` (bot.py:163-180) has zero error handling — any `telegram.error.*` exception propagates directly.
2. `on_response` callback (bot.py:252-253) is a thin wrapper with no try/except.
3. `_read_stdout` (session.py:393-396) catches the exception with a bare `except Exception` and logs it, but silently drops the response text with no retry or user notification.

This chain means a single transient Telegram API failure (timeout, rate limit, network blip) causes permanent message loss, and if the failure persists, the session appears completely unresponsive.

From a technical planning perspective, the fix should be scoped to two areas:
- **`send_long_message` in bot.py**: Add retry with exponential backoff for transient errors (`TimedOut`, `NetworkError`, `RetryAfter`). Non-retryable errors (`BadRequest`, `Forbidden`) should raise immediately.
- **`_read_stdout` in session.py**: After retry exhaustion, the failure should be handled gracefully — either queue the message for later delivery, notify the session of degraded state, or end the session cleanly with logging, rather than silently continuing.

This is ready for a ticket to be created by the product manager. I have no blocking concerns.

### [qa] 2026-03-20T13:18:11Z

From a QA perspective, this is a significant reliability issue. When a fix is implemented, the following QA verification steps should be included in the ticket:

1. **Transient failure recovery**: Simulate a temporary network error during message send (e.g., brief disconnect). Verify the bot retries and the message eventually arrives.
2. **Rate limit handling**: Trigger a Telegram RetryAfter response. Verify the bot respects the backoff period and resends successfully.
3. **Persistent failure behavior**: Simulate a sustained send failure. Verify the bot does NOT silently drop messages indefinitely — it should either notify the user (when possible) or cleanly end the session with clear logging.
4. **Post-failure session integrity**: After a transient send failure recovers, verify subsequent user messages are processed normally (no stuck/corrupted session state).
5. **Logging verification**: Confirm that all send failures are logged at ERROR level with the specific exception type, not swallowed silently.

I'll be ready to run QA on the fix once a ticket comes through.

### [product_manager] 2026-03-20T13:18:12Z

From a ticket scoping perspective, I see this breaking into 3 discrete tickets once the designer provides a design change:

**Ticket 1: Add retry logic with exponential backoff to send_long_message** — This is the core fix. Wrap Telegram API calls in try/except, classify errors as transient (timeout, network, rate limit) vs permanent (bad request, unauthorized), and retry transient errors with exponential backoff. This is independently implementable and addresses root causes #1 and #3.

**Ticket 2: Add error handling and graceful degradation in on_response callback** — If sending fails after all retries, log at ERROR level with the specific exception type, and either notify the session to end gracefully or queue a user-visible error message for the next successful send. This addresses root causes #2 and #4 (session corruption / silent ignoring). Depends on Ticket 1.

**Ticket 3: Add circuit-breaker / health-check for consecutive send failures** — If N consecutive sends to a chat fail, proactively end the session and log a clear diagnostic error. This is a safeguard layer on top of the retry logic. Depends on Tickets 1 and 2.

I agree with the operator's analysis. This is well-scoped enough for the designer to make UX decisions (e.g., what does the user see on failure? how many retries? what's the circuit-breaker threshold?) and produce a design change. Once that arrives, I will create the formal tickets.

### [designer] 2026-03-20T13:19:18Z

Good analysis from both operator and developer. Here are my design requirements for the error handling and failure UX:

**1. Retry Strategy (agree with developer's proposal)**
- 3 retries with exponential backoff (1s/2s/4s) for transient errors (TimedOut, NetworkError, RetryAfter)
- For RetryAfter specifically, respect the server-provided retry_after value rather than using our own backoff timing
- Non-retryable errors (BadRequest, Forbidden) should fail immediately with no retry

**2. User-Facing Behavior When Retries Are Exhausted**
- Do NOT silently drop messages. If a response from Claude cannot be delivered after retries, the bot should log the full message content at ERROR level so it's recoverable from logs
- The bot should NOT attempt to send a "message delivery failed" notification to the user (since the Telegram API is likely still broken) — just log it clearly

**3. Consecutive Failure Circuit Breaker**
- After 5 consecutive send failures within a session, end the session gracefully
- Log a clear ERROR message: "Session ended: {N} consecutive Telegram send failures for chat {chat_id}"
- When the session ends this way, attempt one final notification to the user ("Session ended due to repeated message delivery failures. Please start a new session.") — but don't block or retry endlessly if that also fails

**4. Post-Failure Message Routing**
- After a session is ended due to send failures, new messages from the user should trigger the normal "no active session" flow
- If THAT message also fails to send, just log it — don't enter any retry loop for the no-session notification

**5. Logging Requirements**
- All send failures should log: exception type, chat_id, message length, and retry attempt number
- Truncated message content (first 200 chars) should be logged at ERROR level when a message is permanently dropped

I'll update the design document with an error handling section. The developer's proposed approach aligns well with these requirements.
