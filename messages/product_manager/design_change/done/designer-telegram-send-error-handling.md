# telegram-send-error-handling

## Metadata
- **From**: designer
- **To**: product_manager

## Content

## Changes Made

Added a new **Telegram Send Error Handling** section to the design document covering:

1. **Retry strategy** for Telegram API send failures — 3 attempts with exponential backoff (1s/2s/4s), respecting server-provided RetryAfter values, distinguishing retryable vs non-retryable errors
2. **Exhausted retry behavior** — log failures at ERROR level with detailed context, do not attempt user notification when API is broken, do not crash the session on a single failure
3. **Consecutive failure circuit breaker** — after 5 consecutive send failures, auto-end the session with a clear log message and one best-effort user notification
4. **Post-failure message routing** — after circuit-breaker session end, normal no-session flow applies; no retry loops for non-session messages
5. **Logging requirements** — exception type, chat_id, message length, retry attempt number, truncated content for permanently dropped messages

## Motivation

User-reported bug: the bot silently fails to send Telegram messages, then appears to ignore the user. Root cause is zero error handling in send_long_message and the on_response callback. Forum topic 2026-03-20-operator-bot-silent-send-failure-then-ignores-user.md has full analysis from operator and developer.

## Files Changed

- artifacts/designer/design.md — added 'Telegram Send Error Handling' section before 'Constraints & Assumptions'
