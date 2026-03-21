# fix-bot-silent-after-agent-tool-use

## Metadata
- **From**: product_manager
- **To**: task_planner

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

### Design Context

This is the #1 user-facing bug identified by the operator. When the Claude agent uses tools (file reading, code analysis, etc.), the bot delivers the initial "Let me look at some files" text but then goes silent — the agent's actual answer after tool use never reaches the user. The typing indicator continues firing indefinitely, making it appear the bot is stuck.

Root cause is in `telegram_bot/session.py`, specifically `_extract_text_from_event()` (lines 41-109) and `_read_stdout()` (lines 377-421). See forum topic `2026-03-21T033300Z-operator-bot-silent-after-agent-tool-use.md` for detailed analysis of three possible root cause theories.
