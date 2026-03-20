# Fix duplicate message delivery by skipping `result` events in stream-JSON parsing

## Metadata
- **From**: product_manager
- **To**: task_planner
- **Type**: ticket
- **Created**: 2026-03-09T02:50:00Z

## Requirements

1. In `artifacts/developer/telegram_bot/session.py`, modify `_extract_text_from_event()` so that events with type `result` return `None` (no text extracted).
2. The `result` event type must be added to the list of intentionally skipped event types (currently around lines 93-106), OR handled explicitly to return `None` in the result-event branch (currently lines 86-89).
3. The `assistant` event branch (lines 74-76) must continue to work as before — it is the canonical source of response text.
4. After the fix, each agent turn must produce exactly **one** call to `on_response` with the response text, not two.

## QA Steps

1. Start a session with any agent and send a message.
2. Verify the bot sends exactly **one** response message per agent turn (not two identical messages).
3. Enable DEBUG logging and verify that `_extract_text_from_event()` returns `None` for `result` events and returns text for `assistant` events.
4. Verify that the full response text is still delivered (no truncation or missing content).
5. Test with multi-turn conversations to confirm no regressions across turns.

## Design Context

The `result` event in Claude's stream-json output is a turn-level summary that duplicates the content already delivered via the `assistant` event. The design now explicitly states: "Skip `result` events entirely — the `result` event is a turn-level summary that duplicates the content already delivered via the `assistant` event." See `artifacts/designer/design.md`, "Stream-JSON Protocol > Output parsing" section.
