# Telegram Bot: Bot Handlers, Authentication & Entry Point

## Metadata
- **From**: product_manager
- **To**: task_planner
- **Type**: ticket
- **Created**: 2026-03-08T15:13:00Z

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

## Design Context

This is the integration ticket that wires together config, discovery, and session management into a working Telegram bot. It implements all user-facing interaction described in the design. See `artifacts/designer/design.md`, sections "User Interaction Flow", "Commands", "Authentication", and "Constraints & Assumptions".

**Dependencies**: Requires all three prior tickets (scaffolding/config, discovery, session management).
