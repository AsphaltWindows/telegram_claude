# info-level-event-logging

## Metadata
- **From**: task_planner
- **To**: developer

## Content

### Requirements

1. In `_extract_text_from_event` (session.py), when the function returns `None` for a `tool_use` event, log at INFO level with the event type and tool name (e.g., `INFO: Filtered event: tool_use (tool: Read)`).
2. In `_extract_text_from_event`, when the function returns `None` for a `tool_result` event, log at INFO level with the event type and a brief summary.
3. In `_extract_text_from_event`, when the function returns `None` for an `error` event, log at INFO level with the event type and error content.
4. When `_extract_text_from_event` successfully returns extracted text, log at INFO level with a truncated preview of the first 80 characters (e.g., `INFO: Extracted text (80 chars): "The file contains..."`).
5. All other filtered event types (`ping`, `content_block_start`, `content_block_stop`, `message_start`, `message_stop`, `message_delta`, `system`, `result`) must remain at DEBUG level — do not promote these to INFO.
6. In the `on_response` callback (bot.py), log at INFO level on successful message send (e.g., `INFO: Message sent to chat {chat_id} ({length} chars)`). Currently only failures are logged.
7. All new log lines must use the existing logger instance, not print statements.

### QA Steps

1. Start the bot with default LOG_LEVEL (INFO). Send a message that triggers tool use (e.g., ask the agent to read a file). Verify that the bot log shows INFO-level lines for `tool_use` and `tool_result` events with tool names/summaries.
2. Send a message that triggers a text response from the agent. Verify the log shows an INFO-level line with the truncated text preview (first 80 chars).
3. Verify the log shows an INFO-level line confirming the message was successfully sent to the user (chat ID and character count).
4. Verify that low-signal events (`ping`, `content_block_start`, `content_block_stop`, `message_start`, `message_stop`, `message_delta`) do NOT appear in the log at INFO level.
5. Set LOG_LEVEL=DEBUG and verify that all event types (including low-signal ones) now appear in the log.
6. Verify no duplicate log lines — each event should produce exactly one log entry.

### Technical Context

#### Relevant Files

- **`artifacts/developer/telegram_bot/session.py`** (PRIMARY) — Modify `_extract_text_from_event()` (lines 41-109). The skip list at lines 91-105 needs to be split into high-signal events (tool_use, tool_result, error) logged at INFO, and low-signal events logged at DEBUG.
- **`artifacts/developer/telegram_bot/bot.py`** — Modify `on_response` closure inside `agent_command_handler()` (lines 345-380). Add INFO log after successful send at line 352.
- **`artifacts/developer/telegram_bot/tests/test_session.py`** or equivalent — Add tests verifying correct log levels for different event types.

#### Patterns and Conventions

- **Logger**: Both files use `logger = logging.getLogger(__name__)` — use this for all new log lines.
- **Log format**: Existing log lines use `logger.debug("Skipping %s event from %s", event_type, "agent")` at line 104. Follow this pattern (lazy string formatting, not f-strings in log calls).
- **Event type checking**: The current code uses a single tuple of skipped types at lines 91-103. Split this into two groups.

#### Dependencies and Integration Points

- **Depends on configurable-log-level ticket**: The INFO-level logging is most useful when LOG_LEVEL is configurable. Implement configurable-log-level first, then this ticket. However, they are independent code changes and can be done in any order.
- **`_read_stdout` (lines 391-421)**: Calls `_extract_text_from_event`. The INFO logs go inside the extraction function itself, not in the reader loop.
- **`on_response` callback (bot.py lines 345-380)**: The success log should go after `failure_state["consecutive_failures"] = 0` at line 352, using the `text` parameter for length.
- **May interact with fix-bot-silent-after-agent-tool-use**: If the bug fix changes how `result` events are handled (moving them from the skip list), the INFO/DEBUG log level categorization here needs to account for that. Coordinate: if `result` events are now processed for text extraction, they should NOT also be logged as "filtered."

#### Implementation Notes

1. **Split the skip list**: Replace the single tuple at lines 91-103 with two separate checks:
   ```python
   # High-signal events — log at INFO
   if event_type == "tool_use":
       tool_name = event.get("tool", {}).get("name", event.get("name", "unknown"))
       logger.info("Filtered event: tool_use (tool: %s)", tool_name)
       return None
   if event_type == "tool_result":
       logger.info("Filtered event: tool_result")
       return None
   if event_type == "error":
       logger.info("Filtered event: error — %s", json.dumps(event)[:200])
       return None
   
   # Low-signal events — keep at DEBUG
   if event_type in ("result", "system", "content_block_start", ...):
       logger.debug("Skipping %s event", event_type)
       return None
   ```

2. **Tool name extraction**: The `tool_use` event structure from claude stream-json may vary. Check the event JSON empirically. Common patterns: `event.get("name")` or `event.get("tool", {}).get("name")`. Use a safe fallback like `"unknown"`.

3. **Text extraction logging**: Add after the successful extraction in both the `assistant` and `content_block_delta` branches:
   ```python
   if text:
       logger.info("Extracted text (%d chars): \"%s\"", len(text), text[:80])
       return text
   ```
   But be careful not to double-log — add the log only at the return points, not in helper functions.

4. **on_response success log in bot.py**: At line 352, after `failure_state["consecutive_failures"] = 0`:
   ```python
   logger.info("Message sent to chat %d (%d chars)", cid, len(text))
   ```

5. **Coordinate with bug fix ticket**: If `result` is removed from the skip list by the bug fix, it should NOT appear in either the INFO or DEBUG skip lists here. Check the final state of `_extract_text_from_event` after the bug fix.

### Design Context

The operator identified a critical observability gap: during long agent operations, the bot has zero visibility at INFO level into what the agent subprocess is doing. All stdout parsing happens at DEBUG level, which is invisible in normal operation. This makes it impossible to diagnose why the bot appears frozen. These changes promote the most diagnostic-relevant events (tool_use, tool_result, error, extracted text, send success) to INFO level while keeping noise-prone events at DEBUG. See artifacts/designer/design.md, "INFO-Level Event Logging" subsection under "Diagnostic Logging".
