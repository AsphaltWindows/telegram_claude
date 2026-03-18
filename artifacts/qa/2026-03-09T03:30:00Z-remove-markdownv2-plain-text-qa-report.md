# QA Report: Remove MarkdownV2 attempt from message sending — use plain text only

## Metadata
- **Ticket**: Remove MarkdownV2 attempt from message sending — use plain text only
- **Tested**: 2026-03-09T03:30:00Z
- **Result**: PASS (automated checks only — manual integration steps require live bot)

## Steps

### Step 1: Start a session and send a message that triggers a Claude response
- **Result**: SKIPPED (requires live bot)
- **Notes**: Manual integration test — requires a running Telegram bot connected to Claude.

### Step 2: Verify the response is delivered with no HTTP 400 errors in the logs
- **Result**: SKIPPED (requires live bot)
- **Notes**: Code inspection confirms: `send_long_message()` now calls `bot.send_message(chat_id=chat_id, text=chunk)` with no `parse_mode`, which eliminates the MarkdownV2 attempt that caused HTTP 400 errors. Unit test `test_sends_as_plain_text_no_parse_mode` verifies this.

### Step 3: Verify each message send results in exactly one HTTP request (no MarkdownV2 retry)
- **Result**: PASS (code-level)
- **Notes**: The `send_with_markdown_fallback()` function (which tried MarkdownV2 then fell back to plain text, causing two requests) has been fully removed. `send_long_message()` now makes a single `bot.send_message()` call per chunk. No `parse_mode`, `MarkdownV2`, or `BadRequest` references remain in `bot.py`. Unit test `test_each_chunk_sent_as_plain_text` confirms no `parse_mode` kwarg on any call.

### Step 4: Test with special characters (`.`, `-`, `(`, `)`, `*`, `_`, etc.) delivered without errors
- **Result**: PASS (unit test)
- **Notes**: `test_special_characters_sent_without_error` verifies that a string containing `. ( ) - * _ \`` is passed through directly with no formatting or escaping. Since no `parse_mode` is set, Telegram treats the message as plain text and no escaping is needed.

### Step 5: Test with a response longer than 4096 characters split into multiple messages
- **Result**: PASS (unit test)
- **Notes**: `split_message()` is unchanged and all 9 existing split tests pass. `test_sends_long_message_as_multiple` and `test_each_chunk_sent_as_plain_text` verify multi-chunk sending works correctly.

## Automated Verification

- **All 49 tests pass** (`python -m pytest artifacts/developer/telegram_bot/tests/test_bot.py -v` — 49 passed in 0.55s)
- **No MarkdownV2 remnants** — grep for `MarkdownV2`, `parse_mode`, `BadRequest`, `send_with_markdown` in `bot.py` returns zero matches
- **Import clean** — `from telegram.error import BadRequest` removed
- **Function removed** — `send_with_markdown_fallback()` no longer exists
- **3 new tests added** covering plain-text sending, special characters, and multi-chunk plain-text

## Summary

All automated and code-level checks pass. The implementation cleanly removes the MarkdownV2 code path and replaces it with a direct plain-text send. The change is minimal and surgical — only `send_long_message()` and its helper were modified; all call sites (`on_response`, `on_end`) remain unchanged. Steps 1–2 require manual integration testing with a live bot to fully confirm, but the code-level evidence strongly supports correctness.
