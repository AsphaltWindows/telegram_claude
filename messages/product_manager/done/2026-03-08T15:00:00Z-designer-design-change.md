# Design Change: Telegram Bot Integration for Source Agents

## Metadata
- **From**: designer
- **To**: product_manager
- **Type**: design-change
- **Created**: 2026-03-08T15:00:00Z

## Changes Made

Created the initial design document for a Telegram bot integration. This is a new feature covering:

- **Bot architecture**: Python Telegram bot using `python-telegram-bot` and `asyncio.subprocess` to spawn and manage `claude --agent <agent_name>` processes
- **Session lifecycle**: Start with `/<agent_name>`, converse freely, end with `/end` or 10-minute idle timeout. Graceful shutdown instructs the agent to save its work before exiting.
- **Agent discovery**: Bot reads `pipeline.yaml` at startup to find all `type: source` agents and registers them as Telegram commands
- **Authentication**: Whitelist of Telegram user IDs in `telegram_bot.yaml`
- **Configuration**: `TELEGRAM_BOT_TOKEN` env var + `telegram_bot.yaml` config file
- **Error handling**: No mid-session agent switching, unauthorized users silently ignored, long messages split at 4096 chars
- **File structure**: `telegram_bot/` package with `bot.py`, `session.py`, `config.py`, `discovery.py`

## Motivation

The user needs to interact with source agents (operator, architect, designer) from their phone via Telegram, rather than only through the local terminal. This enables mobile, asynchronous communication with the agent pipeline.

## Files Changed

- `artifacts/designer/design.md` — created initial design document
