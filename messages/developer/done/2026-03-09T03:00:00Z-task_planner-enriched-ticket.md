# Remove MarkdownV2 attempt from message sending — use plain text only

## Metadata
- **From**: task_planner
- **To**: developer
- **Type**: enriched-ticket
- **Created**: 2026-03-09T03:00:00Z

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

## Technical Context

### Relevant Files

| File | Path | Relevance |
|------|------|-----------|
| **bot.py** | `artifacts/developer/telegram_bot/bot.py` | Primary file to modify. Contains `send_with_markdown_fallback()` (lines 164-187), `send_long_message()` (lines 190-207), and the `BadRequest` import (line 16). |
| **test_bot.py** | `artifacts/developer/telegram_bot/tests/test_bot.py` | Contains tests that must be updated: `TestSendWithMarkdownFallback` (lines 145-172) and `TestSendLongMessage` (lines 180-200). Also imports `send_with_markdown_fallback` at line 19. |

### Patterns and Conventions

- Functions use Google-style docstrings with `Parameters` / `Returns` / `Raises` sections in NumPy format (see existing functions in bot.py).
- Async functions use `async def` with `await`.
- Test classes are named `TestXxx` and use `@pytest.mark.asyncio` for async tests.
- Bot mock pattern in tests: `bot = MagicMock()` with `bot.send_message = AsyncMock()`.

### Dependencies and Integration Points

1. **`send_long_message()`** (line 206-207) is the only caller of `send_with_markdown_fallback()`. It iterates over chunks from `split_message()` and calls `send_with_markdown_fallback(bot, chat_id, chunk)` for each.
2. **`send_long_message()`** is called from two places:
   - `on_response` callback (line 280): `await send_long_message(bot, cid, text)` — sends Claude responses to user.
   - `on_end` callback (line 294): `await send_long_message(bot, cid, msg)` — sends session-end messages.
3. **`BadRequest` import** (line 16): `from telegram.error import BadRequest` — can be removed once `send_with_markdown_fallback` is removed.
4. **Test imports** (test_bot.py line 18-19): Both `send_long_message` and `send_with_markdown_fallback` are imported. The import and the `TestSendWithMarkdownFallback` class need updating.

### Implementation Notes

1. **Simplest approach**: Replace `send_with_markdown_fallback()` with a simple `send_plain_message()` (or inline it). The replacement is just:
   ```python
   async def send_plain_message(bot, chat_id: int, text: str) -> None:
       await bot.send_message(chat_id=chat_id, text=text)
   ```
   Alternatively, inline the `bot.send_message()` call directly in `send_long_message()` and remove the helper entirely.

2. **Recommended: inline approach** — Since the helper becomes a single-line pass-through, the cleanest solution is to inline it into `send_long_message()`:
   ```python
   async def send_long_message(bot, chat_id: int, text: str) -> None:
       for chunk in split_message(text):
           await bot.send_message(chat_id=chat_id, text=text)  # no parse_mode
   ```
   Wait — note the variable must be `chunk`, not `text`:
   ```python
       for chunk in split_message(text):
           await bot.send_message(chat_id=chat_id, text=chunk)
   ```

3. **Cleanup to perform**:
   - Remove the `send_with_markdown_fallback()` function (lines 164-187).
   - Remove `from telegram.error import BadRequest` (line 16) — grep first to confirm no other usage.
   - Update `send_long_message()` to call `bot.send_message()` directly.
   - Update test_bot.py: remove the `TestSendWithMarkdownFallback` class, remove the import of `send_with_markdown_fallback`, and update `TestSendLongMessage` assertions (they currently check `bot.send_message.call_count` which will still work since `send_long_message` will now call `bot.send_message` directly instead of going through the markdown helper).

4. **Test impact**: The `TestSendLongMessage` tests mock `bot.send_message` as `AsyncMock()` and check `call_count`. Currently each chunk goes through `send_with_markdown_fallback` which calls `bot.send_message` with `parse_mode="MarkdownV2"`. After the change, each chunk calls `bot.send_message` directly with no `parse_mode`. The `call_count` assertions remain valid. You may want to add an assertion that `parse_mode` is NOT passed.

5. **Order of operations**:
   1. Remove `send_with_markdown_fallback()` function from bot.py.
   2. Update `send_long_message()` to call `bot.send_message()` directly.
   3. Remove `BadRequest` import.
   4. Update test imports — remove `send_with_markdown_fallback`.
   5. Replace `TestSendWithMarkdownFallback` test class with a test that verifies plain text sending (no `parse_mode`).
   6. Run tests to verify: `cd artifacts/developer && python -m pytest telegram_bot/tests/test_bot.py -v`

## Design Context

Claude's output is never MarkdownV2-escaped, so attempting MarkdownV2 parse mode fails with HTTP 400 on virtually every message, doubling Telegram API calls. The design now specifies: "Send all messages as plain text (no parse_mode). Do NOT attempt MarkdownV2 or Markdown parse modes." See `artifacts/designer/design.md`, "Constraints & Assumptions" section.
