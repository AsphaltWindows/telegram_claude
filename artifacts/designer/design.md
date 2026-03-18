# Telegram Bot Integration for Source Agents

## Overview

A Python Telegram bot that allows the user to interact with source-type agents in the pipeline from their phone. The bot spawns `claude` CLI agent sessions, relays messages bidirectionally between Telegram and the agent, and manages session lifecycle.

## Core Concepts

### Agent Sessions

A **session** is a live, stateful conversation between the user and a single source agent. The bot spawns a `claude` CLI process and pipes messages back and forth.

- Only **one active session** at a time per user
- Sessions are started with `/<agent_name> <optional first message>`
- Sessions are ended with `/end` (graceful shutdown) or by idle timeout
- No mid-session agent switching — user must `/end` before starting a new session

### Eligible Agents

Any agent with `type: source` in `pipeline.yaml` is eligible. The bot should dynamically read `pipeline.yaml` at startup to discover source agents and register their names as valid commands.

Current source agents: `operator`, `architect`, `designer`.

## User Interaction Flow

### Starting a Session

1. User sends `/<agent_name>` or `/<agent_name> <message>` in Telegram
2. Bot checks:
   - User is in the whitelist
   - No active session exists for this user
   - Agent name is a valid source agent
3. Bot spawns the `claude` CLI in **non-interactive print mode** from the project root directory (see "Subprocess Invocation" below)
4. Bot sends an immediate confirmation: "Starting session with `<agent_name>`…"
5. If a first message was provided, it is sent to the agent's stdin
6. Agent's response is relayed back to the user via Telegram

### Mid-Session Messages

1. User sends a plain text message (no command prefix)
2. Bot pipes the message to the active agent process's stdin
3. Agent's response is relayed back to the user via Telegram

### Ending a Session (`/end`)

1. User sends `/end`
2. Bot sends a final message to the agent: "Record the product of this conversation as appropriate for your role and exit."
3. Agent performs its shutdown work (writing artifacts, sending messages, creating forum topics, etc.)
4. Agent's final response is relayed to the user
5. Process is terminated, session is cleaned up

### Idle Timeout (10 minutes)

1. If no message is received from the user for **10 minutes**, the bot initiates the same graceful shutdown as `/end`
2. Bot notifies the user: "Session with `<agent_name>` timed out after 10 minutes of inactivity. Work has been saved."

### Error Cases

| Scenario | Bot Response |
|---|---|
| `/<agent_name>` while session active | "You have an active session with `<current_agent>`. Send `/end` to close it first." |
| `/<agent_name>` with invalid agent | "Unknown agent `<name>`. Available agents: `operator`, `architect`, `designer`." |
| Plain message with no active session | "No active session. Start one with `/<agent_name>`." |
| Agent process crashes/dies unexpectedly | "Session with `<agent_name>` ended unexpectedly: {last stderr lines}". Include the last few lines of stderr in the message to surface errors like "node: command not found" directly to the user. Clean up session state. |
| Agent process fails to spawn | "Failed to start session with `<agent_name>`. Check that `claude` is installed and available." |
| Unauthorized user | Silently ignore (no response). Log at DEBUG level for diagnostics. |

## Commands

| Command | Description |
|---|---|
| `/<agent_name> [message]` | Start a session with the named source agent, optionally with a first message |
| `/end` | Gracefully end the current session (agent saves its work) |
| `/help` | List available agents and usage instructions |

## Authentication

- **Whitelist-based**: Only Telegram user IDs in a configured whitelist may interact with the bot
- Whitelist is defined in a configuration file (see Configuration section)
- Messages from non-whitelisted users are silently ignored

## Configuration

Configuration via environment variables and/or a config file at the project root.

### Environment Variables

| Variable | Required | Description |
|---|---|---|
| `TELEGRAM_BOT_TOKEN` | Yes | Telegram Bot API token from @BotFather |
| `PIPELINE_YAML` | Yes | Absolute path to `pipeline.yaml` for agent discovery |

### Config File: `telegram_bot.yaml`

Located at the project root.

```yaml
# Telegram user IDs allowed to interact with the bot
allowed_users:
  - 123456789
  - 987654321

# Idle timeout in seconds before auto-ending a session
idle_timeout: 600

# Graceful shutdown message sent to agent on /end or timeout
shutdown_message: "Record the product of this conversation as appropriate for your role and exit."

# Optional: full path to the claude binary. Use this when claude is installed
# via nvm/npm and the bot runs in a context where nvm is not initialized
# (e.g. systemd service, cron job). If omitted, "claude" is resolved from PATH.
# claude_path: /home/user/.nvm/versions/node/v22.0.0/bin/claude
```

## Technical Design

### Technology Stack

- **Language**: Python 3
- **Telegram library**: `python-telegram-bot` (async)
- **Process management**: `asyncio.subprocess` for spawning and communicating with `claude` CLI

### Pre-flight Environment Check

At startup (during `main()` or `build_application()`), the bot must validate that the `claude` CLI is available and functional:

1. Run `claude --version` (using the configured `claude_path` if set, otherwise bare `claude`)
2. If the command fails (not found, non-zero exit, or timeout), **fail fast** with a clear error message, e.g.: `"Fatal: 'claude' is not available or returned an error. Ensure claude is installed and on PATH, or set 'claude_path' in telegram_bot.yaml. Output: {stderr}"`
3. Log the detected version at INFO level on success

This catches environment issues (missing Node.js, wrong nvm version, binary not on PATH) at bot startup rather than failing silently per-session.

### Subprocess Environment

The `claude` CLI is installed via npm and depends on Node.js. When the bot runs in a non-login context (systemd service, cron, etc.), nvm may not be initialized and `node`/`claude` may not be on PATH.

The `run_bot.sh` launcher script should source nvm initialization if `$NVM_DIR` exists, ensuring the subprocess environment has the correct Node.js version. This is in addition to the `claude_path` config option which allows the user to bypass PATH resolution entirely.

### Process Management

Each session holds:
- The `asyncio.subprocess.Process` handle
- The user's Telegram chat ID
- The agent name
- A timestamp of the last user message (for idle timeout)
- An asyncio task reading the agent's stdout

Communication with the `claude` process uses the **stream-json protocol**:
- **stdin**: User messages are written as JSON objects per the `stream-json` input protocol (one JSON object per line)
- **stdout**: Agent responses arrive as newline-delimited JSON objects (one event per line), parsed by the bot to extract assistant text content
- **stderr**: Logged at WARNING level for visibility, not sent to user

### Subprocess Invocation

**Critical:** The `claude` CLI must be invoked in **non-interactive print mode** with structured I/O. The default interactive/TUI mode will NOT work when stdin/stdout are pipes — `readline()` will block forever.

The required invocation is:
```
claude --agent <agent_name> -p --output-format stream-json --input-format stream-json
```

Flags:
- `-p` / `--print`: Non-interactive mode — writes output to stdout instead of rendering a TUI. Required for piped usage.
- `--output-format stream-json`: Emits newline-delimited JSON objects to stdout in real-time (one event per line), which `readline()` can consume.
- `--input-format stream-json`: Accepts JSON messages on stdin for multi-turn conversation, allowing the bot to stream multiple user messages over the session lifetime.

**Permission handling:** Since this is a headless subprocess with no TTY, the developer should determine whether a permission bypass flag (e.g. `--permission-mode bypassPermissions` or similar) is needed to prevent the process from hanging on permission prompts.

### Stream-JSON Protocol

#### Output parsing (`_read_stdout`)

Each line from stdout is a JSON object with a type/role field. The bot must:
1. Parse each line as JSON
2. Extract text **only** from `assistant` message events (which contain `content` blocks with `type: "text"`)
3. **Skip `result` events entirely** — the `result` event is a turn-level summary that duplicates the content already delivered via the `assistant` event. Extracting text from both causes duplicate messages to be sent to the user.
4. Optionally extract text from `content_block_delta` events (for real-time streaming), but ensure this does not cause duplication with the `assistant` event. The simplest correct approach: extract from `assistant` events only.
5. Skip all other event types: `system`, `tool_use`, `tool_result`, `content_block_start`, `content_block_stop`, `message_start`, `message_stop`, `message_delta`, `ping`, `error`

The developer should determine the exact JSON structure empirically by testing:
```
echo '{"type":"user","content":"hello"}' | claude --print --output-format stream-json 2>/dev/null
```

#### Input formatting (`send`)

User messages sent to stdin must be formatted as JSON objects per the `stream-json` input protocol, not raw text. The developer should determine the exact input format from the CLI documentation or empirical testing.

### Diagnostic Logging

The stdout reader (`_read_stdout`) must include diagnostic logging to aid debugging of the output relay path:
- **On start**: Log that the reader has started (INFO level), including agent name and chat ID
- **On each line**: Log the first 100 characters of each received line (DEBUG level)
- **On exit**: Log that the reader has ended (INFO level), including the reason (EOF, cancellation, error)

### Idle Timeout Implementation

- Each user message resets a per-session timer
- An asyncio task checks the timer; if 10 minutes elapse with no user message, it triggers graceful shutdown
- Uses the same shutdown path as `/end`

### Agent Discovery

At startup, the bot reads the pipeline config file specified by the `PIPELINE_YAML` environment variable and extracts all agents with `type: source`. These become the valid `/<agent_name>` commands. Agents with `scheduled: false` are still eligible (e.g., `operator`).

### Project Directory

The bot must be launched from (or configured to use) the project root directory, since `claude --agent <agent_name>` must run from there.

**Working directory resolution**: The subprocess working directory (`cwd`) should be determined by one of the following, in priority order:
1. An explicit `project_root` configuration value (if provided)
2. The process's current working directory (`Path.cwd()`) — this is the expected case when using the `run_bot.sh` launcher, which `cd`s to the project root before starting the bot

**Do NOT** derive the project root by counting parent directories from `__file__`. This is fragile — the code may be relocated (e.g., from `telegram_bot/` to `artifacts/developer/telegram_bot/`) and the parent-count becomes silently wrong. Currently the code lives at `artifacts/developer/telegram_bot/session.py`, which is 3 levels below the project root, but the existing code only goes 2 levels up, landing at `artifacts/developer/` instead.

### File Structure

```
telegram_bot/
  __init__.py
  bot.py          # Entry point, Telegram bot setup and handlers
  session.py      # Session management, process lifecycle
  config.py       # Configuration loading (yaml, env vars)
  discovery.py    # Agent discovery from pipeline.yaml
```

Plus at project root:
```
telegram_bot.yaml  # Bot configuration
run_bot.sh         # Launcher script (user fills in bot token here)
requirements.txt   # Python dependencies (or added to existing)
```

### Launcher Script: `run_bot.sh`

A shell script at the project root that serves as the single entry point for running the bot. The user edits this script to paste in their Telegram bot token.

Requirements:
- Has a clearly marked placeholder variable at the top: `BOT_TOKEN="YOUR_TOKEN_HERE"`
- Has a `PIPELINE_YAML` variable pointing to the pipeline config file (default: `pipeline.yaml` relative to the project root). This is resolved to an absolute path before export.
- Exports `TELEGRAM_BOT_TOKEN` from the bot token variable
- Exports `PIPELINE_YAML` so the bot knows where to find the pipeline configuration for agent discovery
- **Sources nvm if available**: If `$NVM_DIR/nvm.sh` exists, source it so that `node` and npm-installed binaries (including `claude`) are available on PATH. This is critical when the script is invoked from a non-login context (systemd, cron).
- `cd`s to the project root directory (derived from the script's own location) so `claude` agent commands resolve correctly
- Runs `python -m telegram_bot`
- Should refuse to start if the token is still the placeholder value
- Should refuse to start if the `PIPELINE_YAML` file does not exist
- Should be executable (`chmod +x`)

## Constraints & Assumptions

- The bot runs on the **same machine** as the agent pipeline (needs filesystem access to the project)
- `claude` CLI is installed and available on PATH
- The bot process has the same filesystem permissions as a normal user running `claude`
- Telegram messages have a 4096-character limit; long agent responses must be split into multiple messages
- **Message formatting**: Send all messages as **plain text** (no `parse_mode`). Do NOT attempt MarkdownV2 or Markdown parse modes — Claude's output is never pre-escaped for Telegram's MarkdownV2 syntax, so attempting MarkdownV2 first will fail with a 400 on virtually every message, doubling API calls. If Telegram markdown support is desired in the future, it must include a proper escaping/conversion step before sending.

## Out of Scope (for now)

- Multi-session support (multiple agents simultaneously)
- File/image sharing via Telegram
- Inline keyboards or rich Telegram UI
- Bot deployment automation (systemd, Docker, etc.)
- Rate limiting beyond the whitelist
