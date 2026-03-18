# Remove MarkdownV2 attempt from message sending — use plain text only

## Metadata
- **From**: developer
- **To**: qa
- **Type**: task-complete
- **Created**: 2026-03-09T03:15:00Z

## Summary of Changes

Removed the `send_with_markdown_fallback()` function from `bot.py` and inlined a plain-text `bot.send_message()` call directly into `send_long_message()`. Messages are now sent with no `parse_mode` parameter, eliminating the MarkdownV2 attempt that was causing HTTP 400 errors and doubling API calls. The `BadRequest` import was also removed as it is no longer needed.

## Files Changed

- `artifacts/developer/telegram_bot/bot.py` — Removed `send_with_markdown_fallback()` function (was lines 164-187), removed `from telegram.error import BadRequest` import, updated `send_long_message()` to call `bot.send_message(chat_id=chat_id, text=chunk)` directly with no `parse_mode`.
- `artifacts/developer/telegram_bot/tests/test_bot.py` — Removed `send_with_markdown_fallback` import, removed `TestSendWithMarkdownFallback` test class, added three new tests to `TestSendLongMessage`: `test_sends_as_plain_text_no_parse_mode`, `test_special_characters_sent_without_error`, and `test_each_chunk_sent_as_plain_text`.

## Requirements Addressed

1. **Replace `send_with_markdown_fallback()` with plain text send** — Done. Function removed; `send_long_message()` now calls `bot.send_message()` directly with no `parse_mode`.
2. **Remove the MarkdownV2 attempt entirely** — Done. No MarkdownV2 code path remains.
3. **All call sites continue to work** — Done. `send_long_message()` signature and behavior unchanged; both `on_response` and `on_end` call sites are unaffected.
4. **Long messages still split at 4096 characters** — Done. `split_message()` is unchanged and still used by `send_long_message()`.
5. **No other sending behavior changes** — Done. `chat_id`, reply handling, and all other parameters remain the same.

## QA Steps

1. Start a session and send a message that triggers a Claude response.
2. Verify the response is delivered successfully with **no** HTTP 400 errors in the logs.
3. Verify that each message send results in exactly **one** HTTP request to Telegram (not two — no failed MarkdownV2 attempt followed by a plain text retry).
4. Test with a response containing special characters (`.`, `-`, `(`, `)`, `*`, `_`, etc.) and verify it is delivered without errors.
5. Test with a response longer than 4096 characters and verify it is correctly split into multiple messages.

## Test Coverage

All 49 tests pass (`python -m pytest telegram_bot/tests/test_bot.py -v`).

New tests added to `TestSendLongMessage`:
- `test_sends_as_plain_text_no_parse_mode` — Verifies a single message is sent with exactly `chat_id` and `text` kwargs (no `parse_mode`).
- `test_special_characters_sent_without_error` — Verifies that MarkdownV2-breaking characters (`.`, `-`, `(`, `)`, `*`, `_`, `` ` ``) are sent without issue.
- `test_each_chunk_sent_as_plain_text` — Verifies that when a long message is split, every chunk is sent without a `parse_mode` keyword argument.

Removed tests:
- `TestSendWithMarkdownFallback` (2 tests) — No longer applicable since the function was removed.

## Notes

- The inline approach was chosen per the enriched ticket's recommendation, since the helper function would have been a single-line pass-through.
- The `BadRequest` import was confirmed to have no other usages in the codebase before removal.
