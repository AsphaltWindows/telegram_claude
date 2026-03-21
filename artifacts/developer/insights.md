# Developer Insights

- **pytest sys.path behavior**: When running tests from `artifacts/developer/tests/`, pytest adds `artifacts/developer/` to `sys.path`. This means `from telegram_bot.session import ...` imports from the developer's artifact version, NOT the live `telegram_bot/session.py` in the project root. This is why tests can be written against the new logic even when the live production code hasn't been updated yet.

- **Result-only extraction**: The new `_extract_text_from_event()` extracts text ONLY from `result` events. `assistant` and `content_block_delta` events return `None`. Integration tests that simulate stdout events must use result events (not assistant events) to trigger `on_response` callbacks.
