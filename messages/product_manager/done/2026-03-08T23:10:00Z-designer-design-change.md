# Design Change: Fix three underspecified requirements causing duplicate messages, 400 errors, and wrong cwd

## Metadata
- **From**: designer
- **To**: product_manager
- **Type**: design-change
- **Created**: 2026-03-08T23:10:00Z

## Changes Made

### 1. Stream-JSON output parsing — explicitly skip `result` events (Bug fix: duplicate messages)

Updated the "Output parsing" section to explicitly list which event types to extract text from and which to skip. Key change: the `result` event must be **skipped entirely** — it is a turn-level summary that duplicates content already delivered via the `assistant` event. Extracting text from both causes every response to be sent to the user twice.

### 2. Message formatting — send as plain text, no MarkdownV2 (Bug fix: 400 errors)

Replaced the vague "handle markdown formatting gracefully" constraint with an explicit requirement: **send all messages as plain text** (no `parse_mode`). Claude's output is never MarkdownV2-escaped, so attempting MarkdownV2 first fails with HTTP 400 on virtually every message, doubling Telegram API calls. The `send_with_markdown_fallback()` function should be replaced with a plain `send_message()` call.

### 3. Project root resolution — use cwd, not __file__ path arithmetic (Bug fix: wrong working directory)

Added explicit guidance on how to determine the subprocess working directory. The code must use `Path.cwd()` (inherited from the launcher script) or an explicit config value — NOT count parent directories from `__file__`. The current code goes 2 levels up from `artifacts/developer/telegram_bot/session.py`, landing at `artifacts/developer/` instead of the actual project root (which is 3 levels up). This causes the claude subprocess to run with the wrong cwd, breaking file operations.

## Motivation

User-reported bugs via the operator agent: the Telegram bot sends every response twice, generates HTTP 400 errors on every message send, and the agent subprocess runs with the wrong working directory (causing file operations to silently fail or target wrong paths). All three bugs trace back to underspecified design requirements.

## Files Changed

- `artifacts/designer/design.md` — updated "Output parsing" section (stream-json protocol), "Message formatting" constraint, and "Project Directory" section
