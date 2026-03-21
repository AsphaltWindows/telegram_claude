# fix-extract-text-from-result-events

## Metadata
- **From**: product_manager
- **To**: task_planner

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

### Design Context

This fixes the #1 user-facing bug: the bot goes silent after the agent uses tools (e.g., reading files). The root cause is that `_extract_text_from_event()` skips `result` events entirely and only extracts from `assistant`/`content_block_delta` events. During tool-use turns in `--print` mode, the post-tool response text may only appear in the `result` event, so it is silently discarded.

The design has been updated to specify extracting from `result` events only (see `artifacts/designer/design.md`, section 'Stream-JSON Protocol / Output parsing / Recommended approach: extract from result events only'). This approach is simpler and correct for both simple and tool-use responses.

Forum topic: `2026-03-21T033300Z-operator-bot-silent-after-agent-tool-use.md`
