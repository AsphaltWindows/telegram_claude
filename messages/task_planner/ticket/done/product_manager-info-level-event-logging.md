# info-level-event-logging

## Metadata
- **From**: product_manager
- **To**: task_planner

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

### Design Context

The operator identified a critical observability gap: during long agent operations, the bot has zero visibility at INFO level into what the agent subprocess is doing. All stdout parsing happens at DEBUG level, which is invisible in normal operation. This makes it impossible to diagnose why the bot appears frozen. These changes promote the most diagnostic-relevant events (tool_use, tool_result, error, extracted text, send success) to INFO level while keeping noise-prone events at DEBUG. See artifacts/designer/design.md, "INFO-Level Event Logging" subsection under "Diagnostic Logging".
