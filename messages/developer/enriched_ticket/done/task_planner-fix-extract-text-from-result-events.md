# fix-extract-text-from-result-events

## Metadata
- **From**: task_planner
- **To**: developer

## Content

### Requirements

1. Modify `_extract_text_from_event()` in `telegram_bot/session.py` to extract text **only from `result` events**. The `result` event contains the complete, authoritative turn output in its `content` field (array of content blocks with `type: text`).

2. **Stop extracting text from `assistant` and `content_block_delta` events.** These should be skipped (return `None`) to avoid duplication with the `result` event. They may be logged at DEBUG level.

3. Continue skipping all other event types: `system`, `tool_use`, `tool_result`, `content_block_start`, `content_block_stop`, `message_start`, `message_stop`, `message_delta`, `ping`, `error`.

4. The `result` event text extraction should use the same content-block parsing pattern as the existing `_extract_text_from_content()` helper — iterate over `content[]` blocks, collect those with `type: text`, and join their `text` fields.

5. **Empirical verification step (do first):** Before implementing, run the following command to observe the actual event flow during tool use:
   ```
   echo '{"type":"user","content":"read the contents of session.py"}' | claude --print --output-format stream-json --input-format stream-json --verbose 2>/dev/null
   ```
   Confirm: (a) whether post-tool text appears in streaming events or only in `result`, (b) the exact structure of the `result` event's content field, (c) whether the process exits after emitting `result` or waits for more stdin. Adjust the implementation based on findings.

6. Treat the `result` event as an **end-of-turn signal** — this should reset silence timers and status message state if those features exist.

7. Maintain existing INFO-level logging for high-signal filtered events (`tool_use`, `tool_result`, `error`) and for extracted text (first 80 chars preview). See design doc Diagnostic Logging section.

### QA Steps

1. **Basic tool-use round-trip**: Send the bot a message that triggers tool use (e.g., 'read the contents of session.py'). Verify the bot delivers the final response text to Telegram after tools complete. The bot must NOT go silent after the agent says 'let me look at some files'.

2. **Multi-tool-use chain**: Send a prompt that triggers multiple sequential tool calls (e.g., 'read session.py and config.py and compare them'). Verify all final text is delivered.

3. **Simple response regression check**: Send a basic message that does NOT trigger tool use (e.g., 'Hello, what can you do?'). Verify the response is still delivered normally — the fix must not break the non-tool-use path.

4. **No duplicate text**: For both simple and tool-use responses, verify the response text is delivered exactly once (not duplicated from multiple event sources).

5. **Typing indicator consistency**: While tools are running, the typing indicator should be active. After the final response is delivered, the typing indicator should stop.

6. **Edge case — tool use with no follow-up text**: If the agent's final output after tool use is empty or only contains tool results, the bot should handle gracefully (not hang or crash).

7. **Logging verification**: Check logs at INFO level to confirm: tool_use/tool_result events are logged when filtered, extracted text is logged with preview, and result events are processed.

### Technical Context

#### Relevant Files

- **`telegram_bot/session.py` (PRIMARY — lines 41-109)**: The `_extract_text_from_event()` function (line 41) is the core of this change. Currently extracts text from `assistant` events (lines 79-81) and `content_block_delta` events (lines 84-88), while skipping `result` events (line 92). This logic must be inverted: extract from `result` only, skip `assistant` and `content_block_delta`.

- **`telegram_bot/session.py` (lines 112-137)**: The `_extract_text_from_content()` helper. Already handles the content block parsing pattern needed for `result` events — iterates `content[]` blocks, filters `type: "text"`, joins their `text` fields. Reuse this directly for `result` event extraction.

- **`telegram_bot/session.py` (lines 377-421)**: The `_read_stdout()` method. Calls `_extract_text_from_event()` on line 416 and dispatches to `on_response` on line 419. Also resets silence timers on lines 403-407. No changes needed here — it already handles the flow correctly; the fix is entirely in `_extract_text_from_event()`.

- **`telegram_bot/session.py` (lines 186-189)**: Silence tracking state (`silence_start`, `_sent_15s_status`, `_sent_60s_status`). These are already reset in `_read_stdout` on any stdout activity (line 403-407), so `result` events will naturally reset them. No additional work needed.

- **`telegram_bot/bot.py`**: The bot layer that registers handlers and dispatches to `SessionManager`. Contains `on_response` callback that sends text to Telegram. No changes needed — it receives text from `session.py` via the callback.

- **`artifacts/designer/design.md` (lines 178-212)**: The updated design spec describing the "extract from result events only" approach and the empirical verification command.

#### Patterns and Conventions

- **Docstring style**: Module uses NumPy-style docstrings with `Parameters`, `Returns` sections. Update the `_extract_text_from_event` docstring to reflect the new extraction logic.
- **Logging convention**: Use `logger.debug()` for skipped events, `logger.info()` for high-signal events (tool_use, tool_result, error) and extracted text. The existing code uses `logger.debug` for skips on line 104.
- **Type hints**: Function signatures use `Optional[str]` return type. Maintain this.
- **JSON parsing**: Already handled at top of function (lines 66-71). The `result` event parsing just needs to access the right field path.

#### Dependencies and Integration Points

- **`_extract_text_from_content()` (line 112)**: Reuse this helper for extracting text from the `result` event's content field. The `result` event structure should be: `{"type": "result", "content": [{"type": "text", "text": "..."}], ...}` — but verify empirically.
- **`_read_stdout()` (line 377)**: The caller of `_extract_text_from_event()`. No changes needed — it already handles `None` returns (skips) and non-None returns (relays to callback).
- **`bot.py` on_response callback**: Receives extracted text and sends to Telegram. No changes needed.
- **No external dependencies**: This is a pure logic change within `session.py`.

#### Implementation Notes

1. **Do the empirical verification first** (Requirement 5). Run the suggested command to see the actual stream-json output during tool use. This confirms the `result` event structure and whether `--print` mode exits or waits after `result`. The exact field path in the `result` event (e.g., `event["content"]` vs `event["result"]["content"]` vs `event["message"]["content"]`) must be determined empirically.

2. **The code change is small and localized**. In `_extract_text_from_event()`:
   - Move `"result"` out of the skip list (line 92)
   - Add a new handler block for `event_type == "result"` that calls `_extract_text_from_content()` on the appropriate content field
   - Move `"assistant"` and `"content_block_delta"` into the skip list (or add them as new skip cases with DEBUG logging)
   - Add INFO-level logging for `tool_use`, `tool_result`, and `error` events (currently all at DEBUG)

3. **Update the docstring** (lines 42-64) to reflect that `result` events are now the source of text, and `assistant`/`content_block_delta` are skipped.

4. **Gotcha — `result` event field path**: The `result` event may nest content under `"content"`, `"result"`, or `"message"`. The empirical step will clarify. Write the extraction defensively — check multiple possible paths if uncertain.

5. **Gotcha — empty result content**: If the `result` event has no text blocks (e.g., tool-only turn), `_extract_text_from_content()` already returns `None`, so this is handled.

6. **No test files exist yet** — there are no tests in the project. The QA steps are manual verification against a running bot.

### Design Context

This fixes the #1 user-facing bug: the bot goes silent after the agent uses tools (e.g., reading files). The root cause is that `_extract_text_from_event()` skips `result` events entirely and only extracts from `assistant`/`content_block_delta` events. During tool-use turns in `--print` mode, the post-tool response text may only appear in the `result` event, so it is silently discarded.

The design has been updated to specify extracting from `result` events only (see `artifacts/designer/design.md`, section 'Stream-JSON Protocol / Output parsing / Recommended approach: extract from result events only'). This approach is simpler and correct for both simple and tool-use responses.

Forum topic: `2026-03-21T033300Z-operator-bot-silent-after-agent-tool-use.md`
