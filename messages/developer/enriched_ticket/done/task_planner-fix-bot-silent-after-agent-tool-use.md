# fix-bot-silent-after-agent-tool-use

## Metadata
- **From**: task_planner
- **To**: developer

## Content

### Requirements

1. **Investigate stream-json event flow during tool use**: Run the claude agent manually with `--output-format stream-json` and a prompt that triggers tool use. Capture the raw event stream to determine whether post-tool-use response text appears in (a) `content_block_delta` events, (b) only the `result` event, or (c) not at all because `--print` mode exits after one turn.

2. **Ensure post-tool-use text is delivered to the user**: Based on investigation findings, modify `_extract_text_from_event()` in `telegram_bot/session.py` so that the agent's response after tool use reaches the Telegram user. The three possible fixes (apply whichever matches the root cause):
   - If the final text only appears in the `result` event: extract text from `result` events instead of skipping them (line 92). Ensure deduplication so text already delivered via `content_block_delta` is not sent twice.
   - If `--print` mode stops producing output after tool use and needs a continuation prompt: detect the `result` event as an end-of-turn signal and auto-send a continuation message on stdin to trigger the next agent turn.
   - If the post-tool `assistant` event has a different content block structure: update `_extract_text_from_content()` to handle mixed content blocks (text + tool_use references).

3. **Do not break non-tool-use responses**: The fix must not cause duplicate messages for simple responses that do not involve tool use. If `result` events are now processed, add logic to avoid re-sending text already delivered via streaming deltas.

4. **Add debug logging**: Log (at DEBUG level) the raw event JSON for `result` events so future debugging of similar issues is easier.

### QA Steps

1. **Tool-use response delivery**: Send the bot a message that triggers agent tool use (e.g., "read the contents of session.py"). Verify the agent's full response (including post-tool analysis) is delivered to the Telegram chat. The bot must not go silent after "Let me look at some files."

2. **Simple response still works**: Send the bot a simple question that does not trigger tool use (e.g., "What is 2+2?"). Verify the response is delivered exactly once — no duplicates.

3. **Multi-tool-use response**: Send a message that triggers multiple tool uses in sequence. Verify all intermediate and final responses are delivered.

4. **Typing indicator stops**: After the full response is delivered, verify the typing indicator stops firing (no zombie typing).

5. **Check logs**: Review DEBUG-level logs to confirm `result` events are now logged with their raw JSON content.

### Technical Context

#### Relevant Files

- **`artifacts/developer/telegram_bot/session.py`** (PRIMARY) — This is the file to modify. Contains `_extract_text_from_event()` (lines 41-109) and `_read_stdout()` (lines 377-421). The developer's working copy.
- **`artifacts/developer/telegram_bot/bot.py`** — Contains the `on_response` callback closure (lines 345-380) which routes extracted text to Telegram via `send_long_message`. May need changes if stdin continuation is needed.
- **`artifacts/developer/telegram_bot/tests/test_session.py`** or **`test_bot.py`** — Existing test files to add regression tests to.
- **`telegram_bot/session.py`** — Production copy (read-only reference).

#### Patterns and Conventions

- **Logger**: Use `logger = logging.getLogger(__name__)` already defined at line 20 of session.py
- **Test mocking**: Tests use `from mock import AsyncMock, MagicMock, patch` (not `unittest.mock`). The `_make_session()` helper creates sessions with mocked process/callbacks. `patch("telegram_bot.session.asyncio.sleep", ...)` controls heartbeat loop iterations.
- **Docstrings**: All functions use NumPy-style docstrings (Parameters/Returns/Raises sections)
- **Type hints**: All function signatures have return type annotations; use `Optional[str]` for nullable returns
- **Event extraction pattern**: `_extract_text_from_event` returns `Optional[str]` — `None` means skip, a string means relay to user

#### Dependencies and Integration Points

- **`_read_stdout` (lines 377-421)**: Calls `_extract_text_from_event()` and relays non-None results to `self._on_response(self.chat_id, text)`. If the fix involves detecting end-of-turn and sending a continuation, this is where stdin write logic would go.
- **`Session.send()` (lines 243-270)**: Writes stream-json user messages to stdin. The envelope format is `{"type": "user", "message": {"role": "user", "content": "<text>"}}`. Reuse this format if auto-continuation is needed.
- **`silence_start` tracking (lines 188, 403-407)**: Already resets on each stdout line. The fix should not interfere with this mechanism.
- **`on_response` callback in bot.py (lines 345-380)**: Receives `(chat_id, text)` and sends via `send_long_message`. Includes circuit breaker logic. No changes needed here unless the fix changes what gets passed.

#### Implementation Notes

1. **Investigation first**: Run `echo '{"type":"user","message":{"role":"user","content":"read the contents of session.py"}}' | claude --print --agent operator --output-format stream-json --input-format stream-json --verbose --permission-mode bypassPermissions 2>/dev/null` and capture the raw output to determine which theory (A, B, or C from the forum topic) is correct.

2. **Most likely fix (Theory A or B)**: The `result` event at line 92 is currently skipped. It likely contains the final text for the turn. The fix should:
   - Parse `result` events and extract text from them
   - Implement deduplication: track text already sent via `content_block_delta` events and only send text from `result` if it contains NEW content not already delivered
   - A simple approach: use a buffer to accumulate delta text, then compare against `result` text

3. **Deduplication strategy**: The simplest correct approach may be to STOP extracting from `content_block_delta` events and ONLY extract from `result` events. This loses real-time streaming but guarantees exactly-once delivery. For a Telegram bot, this tradeoff is acceptable since partial message updates aren't natural in Telegram. The designer recommended this approach.

4. **Alternative — keep streaming + use result as fallback**: Continue extracting from `content_block_delta` for real-time delivery. Also parse `result` events. Use a flag or accumulator to detect whether post-tool text was already delivered via deltas. If not, extract from `result`.

5. **If Theory A (process exits after tool use)**: The `result` event signals end-of-turn. After detecting it in `_read_stdout`, write a continuation prompt to stdin: `{"type": "user", "message": {"role": "user", "content": "continue"}}`. But also extract any text from the `result` event itself.

6. **Gotcha — silence_start reset**: Line 403-407 resets `silence_start` on ANY stdout line, including skipped events. This is correct behavior and should be preserved. But if you add `result` event processing, make sure the text extraction happens BEFORE the early return on line 416-421.

7. **Test approach**: Write unit tests for `_extract_text_from_event` with sample `result` event JSON. Also test the deduplication logic if implemented.

### Design Context

This is the #1 user-facing bug identified by the operator. When the Claude agent uses tools (file reading, code analysis, etc.), the bot delivers the initial "Let me look at some files" text but then goes silent — the agent's actual answer after tool use never reaches the user. The typing indicator continues firing indefinitely, making it appear the bot is stuck.

Root cause is in `telegram_bot/session.py`, specifically `_extract_text_from_event()` (lines 41-109) and `_read_stdout()` (lines 377-421). See forum topic `2026-03-21T033300Z-operator-bot-silent-after-agent-tool-use.md` for detailed analysis of three possible root cause theories (A: --print mode exits after one turn, B: result event carries the only copy of final text, C: post-tool assistant event has different structure). The designer recommends extracting text only from result events as the simplest correct approach.
