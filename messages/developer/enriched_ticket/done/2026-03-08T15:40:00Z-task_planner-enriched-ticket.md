# Telegram Bot: Bot Handlers, Authentication & Entry Point

## Metadata
- **From**: task_planner
- **To**: developer
- **Type**: enriched-ticket
- **Created**: 2026-03-08T15:40:00Z

## Requirements

1. Create `telegram_bot/bot.py` as the entry point for the Telegram bot
2. At startup:
   a. Load configuration via `config.py`
   b. Discover source agents via `discovery.py`
   c. Register a dynamic command handler for each discovered agent name (e.g., `/operator`, `/architect`, `/designer`)
   d. Register a handler for `/end`
   e. Register a handler for `/help`
   f. Register a fallback handler for plain text messages (no command prefix)
3. **Authentication**: Before processing any message or command, check that the sender's Telegram user ID is in the `allowed_users` whitelist. Silently ignore (no response) messages from unauthorized users.
4. **`/<agent_name>` handler**:
   a. If user has an active session, respond: "You have an active session with `<current_agent>`. Send `/end` to close it first."
   b. If agent name is invalid, respond: "Unknown agent `<name>`. Available agents: `operator`, `architect`, `designer`." (list actual discovered agents)
   c. Otherwise, start a new session via `SessionManager` and optionally forward the first message if provided
   d. Relay the agent's first response back to the user
5. **`/end` handler**: Trigger graceful shutdown of the active session. If no active session, respond: "No active session."
6. **`/help` handler**: List available agent commands and usage instructions
7. **Plain text handler**: If user has an active session, pipe the message to the agent and relay the response. If no active session, respond: "No active session. Start one with `/<agent_name>`."
8. **Message splitting**: Agent responses exceeding 4096 characters must be split into multiple Telegram messages at sensible boundaries (e.g., newlines or sentence breaks)
9. **Markdown handling**: Send agent responses using Telegram's markdown mode where possible; fall back to plain text if parsing fails
10. The bot must be runnable via `python -m telegram_bot` or a clear entry point

## QA Steps

1. Start the bot; verify it connects to Telegram and registers commands for all source agents discovered from `pipeline.yaml`
2. Send a command from a whitelisted user ID; verify the bot responds
3. Send a command from a non-whitelisted user ID; verify the bot silently ignores it (no response)
4. Send `/<agent_name>` with a valid agent; verify a session starts and the agent's response is relayed
5. Send `/<agent_name> hello` with an initial message; verify the message is forwarded to the agent
6. While a session is active, send `/<other_agent>`; verify the bot responds with the "active session" error message
7. Send `/invalid_agent`; verify the bot responds with the "unknown agent" error and lists available agents
8. During an active session, send a plain text message; verify it reaches the agent and the response comes back
9. With no active session, send a plain text message; verify the "no active session" error response
10. Send `/end` during an active session; verify graceful shutdown occurs and the agent's final response is relayed
11. Send `/help`; verify it lists all available agents with usage instructions
12. Trigger a response longer than 4096 characters; verify it is split into multiple messages without truncation
13. Verify the bot can be started with `python -m telegram_bot` (or documented entry point)

## Technical Context

### Relevant Files

| File | Status | Relevance |
|---|---|---|
| `telegram_bot/bot.py` | **To create** | The main module this ticket implements. Entry point for the bot: handler registration, authentication, message routing. |
| `telegram_bot/__main__.py` | **To create** | Makes `python -m telegram_bot` work. Should import and call the bot's main function from `bot.py`. |
| `telegram_bot/config.py` | Exists (`artifacts/developer/telegram_bot/config.py`) | Provides `load_config() -> BotConfig`. `BotConfig` is a dataclass with fields: `telegram_bot_token` (str), `allowed_users` (list[int]), `idle_timeout` (int, default 600), `shutdown_message` (str). Use `config.telegram_bot_token` to initialize the Telegram bot, `config.allowed_users` for authentication checks. |
| `telegram_bot/discovery.py` | Exists (`artifacts/developer/telegram_bot/discovery.py`) | Provides `discover_source_agents(pipeline_path=None) -> list[str]`. Returns agent names with `type: source`. Currently returns `["operator", "architect", "designer"]`. Use at startup to dynamically register command handlers. |
| `telegram_bot/session.py` | **Dependency (prior ticket)** | Provides `SessionManager` class. Expected API: `start_session(user_id, agent_name, response_callback) -> Session`, `send_message(user_id, text)`, `end_session(user_id)`, `has_active_session(user_id) -> bool`, `get_active_session(user_id) -> Session`. The `Session` holds the `asyncio.subprocess.Process`, agent name, chat ID. |
| `telegram_bot/__init__.py` | Exists (`artifacts/developer/telegram_bot/__init__.py`) | Package init with docstring `"""Telegram bot integration for Claude agent pipeline."""`. |
| `pipeline.yaml` | Exists (project root) | Pipeline config with 7 agents, 3 source agents: `operator`, `architect`, `designer`. |
| `telegram_bot.yaml` | Exists (`artifacts/developer/telegram_bot.yaml`) | Bot config file. Contains `allowed_users`, `idle_timeout`, `shutdown_message`. |
| `artifacts/designer/design.md` | Exists (read-only) | Full design document. Sections on User Interaction Flow, Commands, Authentication, Constraints, Error Cases table. |

### Patterns and Conventions

- **Module style**: Use `from __future__ import annotations` at the top. Modules have a docstring explaining purpose. Functions have full docstrings with Parameters/Returns/Raises sections (see `config.py` and `discovery.py` for examples).
- **Type hints**: All functions are type-annotated. Use `Optional`, `List` from `typing` (Python 3 compat style as established in existing modules).
- **Error handling**: Raise specific exception types (`ValueError`, `FileNotFoundError`) with descriptive messages. Never silently swallow errors in internal logic.
- **Project root resolution**: Existing modules use `Path(__file__).resolve().parent.parent` to find the project root (two levels up from `telegram_bot/module.py`). Follow this pattern.
- **Testing pattern**: Tests use pytest with `tmp_path` fixture, fixtures with `monkeypatch` for env vars. Test classes group related tests. Helper functions for setup. Tests live in `telegram_bot/tests/` or `tests/`.
- **Async library**: The design specifies `python-telegram-bot` (async). Use `from telegram import Update` and `from telegram.ext import Application, CommandHandler, MessageHandler, ContextTypes, filters`. The library's async API uses `async def handler(update: Update, context: ContextTypes.DEFAULT_TYPE)` pattern.

### Dependencies and Integration Points

1. **`python-telegram-bot`** — Primary dependency. Use `Application.builder().token(config.telegram_bot_token).build()` to create the bot. Register handlers with `app.add_handler(CommandHandler(...))` and `app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, ...))`. Start with `app.run_polling()`.

2. **`config.py`** — Call `load_config()` at startup. Use:
   - `config.telegram_bot_token` → pass to `Application.builder().token()`
   - `config.allowed_users` → set used in the auth check
   - `config.idle_timeout` → pass to `SessionManager` construction
   - `config.shutdown_message` → pass to `SessionManager` construction

3. **`discovery.py`** — Call `discover_source_agents()` at startup. Returns `list[str]` of agent names. Loop over these to register one `CommandHandler` per agent name.

4. **`session.py` (SessionManager)** — The bot layer is the glue between Telegram handlers and the session manager. Key interactions:
   - Agent command → `session_manager.start_session(user_id, agent_name, callback)`
   - Plain text → `session_manager.send_message(user_id, text)`
   - `/end` → `session_manager.end_session(user_id)`
   - Check active session → `session_manager.has_active_session(user_id)`
   - Get current agent name → `session_manager.get_active_session(user_id).agent_name`

5. **Telegram API constraints**:
   - Max message length: 4096 characters
   - Markdown mode: Use `parse_mode="MarkdownV2"` or `parse_mode="Markdown"`. MarkdownV2 is stricter; consider trying MarkdownV2 first, falling back to plain text on `telegram.error.BadRequest`.

### Implementation Notes

1. **File creation order**: Create `telegram_bot/bot.py` first, then `telegram_bot/__main__.py`.

2. **Authentication decorator/middleware**: Implement auth as a helper that wraps all handlers. Suggested approach:
   ```python
   def auth_required(func):
       async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
           if update.effective_user.id not in allowed_users:
               return  # Silently ignore
           return await func(update, context)
       return wrapper
   ```
   Apply this to every handler. Store `allowed_users` as a `set[int]` for O(1) lookup.

3. **Dynamic command registration**: Loop over discovered agents and register a handler for each:
   ```python
   for agent_name in agents:
       app.add_handler(CommandHandler(agent_name, agent_command_handler))
   ```
   Inside the handler, extract the agent name from `update.message.text.split()[0][1:]` (strip the `/` prefix), or use `context.args` to get the rest of the message after the command.

4. **Message splitting**: Implement a `split_message(text: str, max_length: int = 4096) -> list[str]` utility. Strategy:
   - Try to split at `\n\n` (paragraph breaks) first
   - Fall back to `\n` (line breaks)
   - Fall back to character-level split as last resort
   - Never split in the middle of a markdown code block if possible

5. **Markdown fallback**: Wrap message sending in a try/except:
   ```python
   try:
       await update.message.reply_text(text, parse_mode="MarkdownV2")
   except telegram.error.BadRequest:
       await update.message.reply_text(text)
   ```

6. **Response callback wiring**: The `SessionManager` takes a response callback when starting a session. This callback needs access to the Telegram chat to send messages. A common pattern is a closure or partial:
   ```python
   async def on_response(text: str):
       for chunk in split_message(text):
           await send_with_markdown_fallback(context.bot, chat_id, chunk)
   ```
   Pass this to `session_manager.start_session()`.

7. **`/help` handler**: Dynamically build the help text from the discovered agents list:
   ```
   Available commands:
   /<agent1> [message] — Start a session with <agent1>
   /<agent2> [message] — Start a session with <agent2>
   ...
   /end — End the current session
   /help — Show this help message
   ```

8. **`__main__.py`**: Keep it minimal:
   ```python
   """Allow running the bot with ``python -m telegram_bot``."""
   from telegram_bot.bot import main
   main()
   ```

9. **Bot startup function**: Structure `main()` as:
   ```python
   def main():
       config = load_config()
       agents = discover_source_agents()
       # Build application
       app = Application.builder().token(config.telegram_bot_token).build()
       # Store shared state in app context (bot_data)
       app.bot_data["config"] = config
       app.bot_data["agents"] = agents
       app.bot_data["session_manager"] = SessionManager(config)
       # Register handlers
       ...
       app.run_polling()
   ```
   Using `app.bot_data` or `context.bot_data` is the idiomatic `python-telegram-bot` way to share state across handlers.

10. **Testing considerations**: For unit tests, mock `telegram.ext.Application`, the `Update` and `Context` objects. The `python-telegram-bot` library provides test utilities, but manual mocking with `unittest.mock` or `pytest-mock` is the most common approach. Focus tests on:
    - Auth rejection (unauthorized user ID → no response)
    - Agent command routing (valid agent → session start, invalid → error message)
    - Active session conflict (second agent command → error message)
    - `/end` with and without active session
    - Message splitting logic (pure function, easy to unit test)
    - Plain text routing (with/without active session)

## Design Context

This is the integration ticket that wires together config, discovery, and session management into a working Telegram bot. It implements all user-facing interaction described in the design. See `artifacts/designer/design.md`, sections "User Interaction Flow", "Commands", "Authentication", and "Constraints & Assumptions".

**Dependencies**: Requires all three prior tickets (scaffolding/config, discovery, session management).
