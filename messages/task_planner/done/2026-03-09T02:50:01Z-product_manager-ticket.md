# Remove MarkdownV2 attempt from message sending — use plain text only

## Metadata
- **From**: product_manager
- **To**: task_planner
- **Type**: ticket
- **Created**: 2026-03-09T02:50:01Z

## Requirements

1. In `artifacts/developer/telegram_bot/bot.py`, replace `send_with_markdown_fallback()` (lines 164-187) with a plain text send. Messages must be sent with **no `parse_mode`** parameter (plain text).
2. Remove the MarkdownV2 attempt entirely — do not try MarkdownV2 first and fall back to plain text.
3. The function may be renamed (e.g., to `send_message()`) or simplified, but all call sites must continue to work.
4. Long messages (over 4096 characters) must still be split into multiple messages, as before.
5. No other sending behavior should change (chat_id, reply handling, etc.).

## QA Steps

1. Start a session and send a message that triggers a Claude response.
2. Verify the response is delivered successfully with **no** HTTP 400 errors in the logs.
3. Verify that each message send results in exactly **one** HTTP request to Telegram (not two — no failed MarkdownV2 attempt followed by a plain text retry).
4. Test with a response containing special characters (`.`, `-`, `(`, `)`, `*`, `_`, etc.) and verify it is delivered without errors.
5. Test with a response longer than 4096 characters and verify it is correctly split into multiple messages.

## Design Context

Claude's output is never MarkdownV2-escaped, so attempting MarkdownV2 parse mode fails with HTTP 400 on virtually every message, doubling Telegram API calls. The design now specifies: "Send all messages as plain text (no parse_mode). Do NOT attempt MarkdownV2 or Markdown parse modes." See `artifacts/designer/design.md`, "Constraints & Assumptions" section.
