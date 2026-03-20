"""Telegram bot entry point — handler registration, authentication, message routing.

Wires together configuration, agent discovery, and session management into
a working Telegram bot that proxies user messages to Claude agent subprocesses.
"""

from __future__ import annotations

import asyncio
import functools
import logging
import subprocess
import sys
from typing import List, Optional

from telegram import Update
from telegram.error import BadRequest, Forbidden, NetworkError, RetryAfter, TimedOut
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

from telegram_bot.config import load_config
from telegram_bot.discovery import discover_source_agents
from telegram_bot.session import SessionManager

logger = logging.getLogger(__name__)

# Telegram enforces a maximum message length of 4096 characters.
_MAX_MESSAGE_LENGTH = 4096

# Timeout for the pre-flight ``claude --version`` check, in seconds.
_PREFLIGHT_TIMEOUT = 10


# ------------------------------------------------------------------
# Utilities
# ------------------------------------------------------------------


def _check_claude_cli(command: str = "claude") -> str:
    """Run ``claude --version`` and return the version string.

    Parameters
    ----------
    command:
        Path or name of the claude CLI executable.

    Returns
    -------
    str
        The version string reported by the CLI.

    Raises
    ------
    SystemExit
        If the CLI is not found, returns a non-zero exit code, or times
        out.  Logs a descriptive error before exiting.
    """
    try:
        result = subprocess.run(
            [command, "--version"],
            capture_output=True,
            text=True,
            timeout=_PREFLIGHT_TIMEOUT,
        )
    except FileNotFoundError:
        logger.error(
            "Pre-flight check failed: '%s' not found on PATH. "
            "Is the claude CLI installed? If using nvm, ensure it is "
            "initialized in the bot's environment.",
            command,
        )
        sys.exit(1)
    except subprocess.TimeoutExpired:
        logger.error(
            "Pre-flight check failed: '%s --version' timed out after %ds.",
            command,
            _PREFLIGHT_TIMEOUT,
        )
        sys.exit(1)
    except OSError as exc:
        logger.error(
            "Pre-flight check failed: could not execute '%s': %s",
            command,
            exc,
        )
        sys.exit(1)

    if result.returncode != 0:
        stderr_snippet = (result.stderr or "").strip()[:200]
        logger.error(
            "Pre-flight check failed: '%s --version' exited with code %d. "
            "stderr: %s",
            command,
            result.returncode,
            stderr_snippet or "(empty)",
        )
        sys.exit(1)

    version = (result.stdout or "").strip()
    logger.info("claude CLI version: %s", version)
    return version


def split_message(text: str, max_length: int = _MAX_MESSAGE_LENGTH) -> List[str]:
    """Split *text* into chunks that each fit within *max_length*.

    The function tries to split at sensible boundaries:

    1. Paragraph breaks (``\\n\\n``)
    2. Line breaks (``\\n``)
    3. Hard character-level split as a last resort

    Parameters
    ----------
    text:
        The text to split.
    max_length:
        Maximum length of each chunk.  Defaults to 4096.

    Returns
    -------
    list[str]
        Non-empty list of text chunks, each at most *max_length* characters.
    """
    if not text:
        return [""]

    if len(text) <= max_length:
        return [text]

    chunks: List[str] = []
    remaining = text

    while remaining:
        if len(remaining) <= max_length:
            chunks.append(remaining)
            break

        # Try to find a paragraph break within the limit.
        split_pos = remaining.rfind("\n\n", 0, max_length)
        if split_pos > 0:
            chunks.append(remaining[:split_pos])
            remaining = remaining[split_pos + 2:]  # skip the double newline
            continue

        # Try a line break.
        split_pos = remaining.rfind("\n", 0, max_length)
        if split_pos > 0:
            chunks.append(remaining[:split_pos])
            remaining = remaining[split_pos + 1:]
            continue

        # Hard split at max_length.
        chunks.append(remaining[:max_length])
        remaining = remaining[max_length:]

    return chunks


async def retry_send_message(
    bot,
    chat_id: int,
    text: str,
    max_attempts: int = 3,
) -> bool:
    """Send a message via *bot* with retry logic for transient failures.

    Parameters
    ----------
    bot:
        The ``telegram.Bot`` instance.
    chat_id:
        Target chat ID.
    text:
        Message text to send (must fit within Telegram limits).
    max_attempts:
        Maximum number of send attempts (1 initial + retries).

    Returns
    -------
    bool
        ``True`` if the message was sent successfully, ``False`` if all
        attempts failed or a non-retryable error occurred.
    """
    _NON_RETRYABLE = (BadRequest, Forbidden)
    _RETRYABLE = (TimedOut, NetworkError, RetryAfter)

    for attempt in range(max_attempts):
        try:
            await bot.send_message(chat_id=chat_id, text=text)
            return True
        except _NON_RETRYABLE as exc:
            logger.error(
                "Non-retryable send failure (attempt %d/%d) "
                "chat_id=%d msg_len=%d: %s: %s",
                attempt + 1,
                max_attempts,
                chat_id,
                len(text),
                type(exc).__name__,
                exc,
            )
            return False
        except _RETRYABLE as exc:
            logger.error(
                "Retryable send failure (attempt %d/%d) "
                "chat_id=%d msg_len=%d: %s: %s",
                attempt + 1,
                max_attempts,
                chat_id,
                len(text),
                type(exc).__name__,
                exc,
            )
            # Last attempt — no more retries.
            if attempt + 1 >= max_attempts:
                break
            # Determine backoff delay.
            if isinstance(exc, RetryAfter):
                delay = exc.retry_after
            else:
                delay = 2 ** attempt  # 1, 2, 4, …
            await asyncio.sleep(delay)

    # All retries exhausted — log truncated message content.
    truncated = text[:200]
    logger.error(
        "All %d send attempts exhausted for chat_id=%d msg_len=%d. "
        "Message dropped. Content (first 200 chars): %s",
        max_attempts,
        chat_id,
        len(text),
        truncated,
    )
    return False


async def send_long_message(
    bot,
    chat_id: int,
    text: str,
) -> bool:
    """Split *text* if necessary and send each chunk with retry logic.

    Parameters
    ----------
    bot:
        The ``telegram.Bot`` instance.
    chat_id:
        Target chat ID.
    text:
        Message text (may exceed 4096 characters).

    Returns
    -------
    bool
        ``True`` if all chunks were sent successfully, ``False`` if any
        chunk failed.
    """
    all_ok = True
    for chunk in split_message(text):
        if not await retry_send_message(bot, chat_id, chunk):
            all_ok = False
    return all_ok


# ------------------------------------------------------------------
# Authentication decorator
# ------------------------------------------------------------------


def auth_required(func):
    """Decorator that silently drops updates from unauthorised users.

    The set of allowed user IDs is read from ``context.bot_data["allowed_users"]``.
    """

    @functools.wraps(func)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
        allowed: set = context.bot_data["allowed_users"]
        if update.effective_user is None or update.effective_user.id not in allowed:
            user_id = update.effective_user.id if update.effective_user else "unknown"
            logger.debug("Rejected message from unauthorized user %s", user_id)
            return  # Silently ignore
        return await func(update, context)

    return wrapper


# ------------------------------------------------------------------
# Handlers
# ------------------------------------------------------------------


@auth_required
async def agent_command_handler(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Handle ``/<agent_name>`` commands — start a session with the agent.

    If the user already has an active session, an error message is returned.
    If the agent name is not recognised, lists the available agents.
    Otherwise a new session is started and an optional first message is
    forwarded to the agent.
    """
    agents: List[str] = context.bot_data["agents"]
    session_manager: SessionManager = context.bot_data["session_manager"]
    chat_id: int = update.effective_chat.id

    # Extract agent name from the command (e.g. "/operator" -> "operator").
    command_text = update.message.text or ""
    parts = command_text.split(maxsplit=1)
    agent_name = parts[0].lstrip("/").split("@")[0]  # handle @botname suffix
    first_message: Optional[str] = parts[1] if len(parts) > 1 else None

    # Check for active session.
    if session_manager.has_session(chat_id):
        current_session = session_manager._sessions[chat_id]
        await update.message.reply_text(
            f"You have an active session with {current_session.agent_name}. "
            f"Send /end to close it first."
        )
        return

    # Validate agent name.
    if agent_name not in agents:
        agent_list = ", ".join(agents)
        await update.message.reply_text(
            f"Unknown agent {agent_name}. Available agents: {agent_list}."
        )
        return

    # Build the response callback for this chat.
    bot = context.bot

    # Circuit breaker state — shared by the on_response closure.
    _CIRCUIT_BREAKER_THRESHOLD = 5
    failure_state = {"consecutive_failures": 0, "circuit_broken": False}

    async def on_response(cid: int, text: str) -> None:
        # If the circuit breaker already tripped, don't attempt further sends.
        if failure_state["circuit_broken"]:
            return

        success = await send_long_message(bot, cid, text)
        if success:
            failure_state["consecutive_failures"] = 0
        else:
            failure_state["consecutive_failures"] += 1
            if failure_state["consecutive_failures"] >= _CIRCUIT_BREAKER_THRESHOLD:
                failure_state["circuit_broken"] = True
                count = failure_state["consecutive_failures"]
                logger.error(
                    "Session ended: %d consecutive Telegram send failures "
                    "for chat %d",
                    count,
                    cid,
                )
                # Attempt a final notification to the user.
                try:
                    await retry_send_message(
                        bot,
                        cid,
                        "Session ended due to repeated message delivery "
                        "failures. Please start a new session.",
                    )
                except Exception:
                    logger.exception(
                        "Failed to send circuit breaker notification "
                        "to chat %d.",
                        cid,
                    )
                # End the session via the session manager.
                await session_manager.end_session(cid)

    async def on_end(
        cid: int, aname: str, reason: str, *, stderr_tail: str = ""
    ) -> None:
        reason_messages = {
            "shutdown": f"Session with {aname} ended.",
            "timeout": f"Session with {aname} timed out due to inactivity.",
            "crash": f"Session with {aname} ended unexpectedly.",
        }
        msg = reason_messages.get(reason, f"Session with {aname} ended ({reason}).")
        if reason == "crash" and stderr_tail:
            msg += f"\n\nDiagnostics:\n```\n{stderr_tail}\n```"
        try:
            await send_long_message(bot, cid, msg)
        except Exception:
            logger.exception("Failed to send session-end message to chat %d.", cid)

    # Start the session.
    try:
        session = await session_manager.start_session(
            chat_id=chat_id,
            agent_name=agent_name,
            on_response=on_response,
            on_end=on_end,
        )
    except (FileNotFoundError, OSError) as exc:
        logger.error(
            "Failed to start session with agent '%s' for chat %d: %s",
            agent_name, chat_id, exc,
        )
        await update.message.reply_text(
            f"Failed to start session with `{agent_name}`. "
            f"Check that `claude` is installed and available."
        )
        return
    except Exception as exc:
        logger.exception(
            "Unexpected error starting session with agent '%s' for chat %d.",
            agent_name, chat_id,
        )
        await update.message.reply_text(
            f"Failed to start session with `{agent_name}`. "
            f"Check that `claude` is installed and available."
        )
        return

    # Send confirmation to user.
    await update.message.reply_text(
        f"Starting session with `{agent_name}`\u2026"
    )

    # Forward the first message if provided.
    if first_message:
        await session.send(first_message)


@auth_required
async def end_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle ``/end`` — gracefully shut down the active session."""
    session_manager: SessionManager = context.bot_data["session_manager"]
    chat_id: int = update.effective_chat.id

    if not session_manager.has_session(chat_id):
        await update.message.reply_text("No active session.")
        return

    await session_manager.end_session(chat_id)


@auth_required
async def help_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle ``/help`` — list available agent commands and usage."""
    agents: List[str] = context.bot_data["agents"]

    lines = ["Available commands:\n"]
    for agent_name in agents:
        lines.append(f"/{agent_name} [message] — Start a session with {agent_name}")
    lines.append("/end — End the current session")
    lines.append("/help — Show this help message")

    await update.message.reply_text("\n".join(lines))


@auth_required
async def plain_text_handler(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Handle plain text messages — pipe to the active session or show an error."""
    session_manager: SessionManager = context.bot_data["session_manager"]
    chat_id: int = update.effective_chat.id

    if not session_manager.has_session(chat_id):
        await update.message.reply_text(
            "No active session. Start one with /<agent_name>."
        )
        return

    text = update.message.text or ""
    if text.strip():
        await session_manager.send_message(chat_id, text)


# ------------------------------------------------------------------
# Application builder
# ------------------------------------------------------------------


def build_application(config=None) -> Application:
    """Create and configure the Telegram bot ``Application``.

    Loads configuration, discovers source agents, registers all handlers,
    and returns the ready-to-run ``Application`` instance.

    Parameters
    ----------
    config:
        Optional pre-loaded ``BotConfig``.  If ``None``, configuration
        is loaded from the environment and YAML file.

    Returns
    -------
    Application
        Fully configured application (call ``.run_polling()`` to start).
    """
    if config is None:
        config = load_config()
    agents = discover_source_agents(pipeline_path=config.pipeline_yaml)

    app = Application.builder().token(config.telegram_bot_token).build()

    # Store shared state in bot_data.
    app.bot_data["config"] = config
    app.bot_data["agents"] = agents
    app.bot_data["allowed_users"] = set(config.allowed_users)
    app.bot_data["session_manager"] = SessionManager(
        idle_timeout=config.idle_timeout,
        shutdown_message=config.shutdown_message,
        project_root=config.project_root,
        claude_command=config.claude_path or "claude",
    )

    # Register a command handler for each discovered agent.
    for agent_name in agents:
        app.add_handler(CommandHandler(agent_name, agent_command_handler))

    # Built-in commands.
    app.add_handler(CommandHandler("end", end_handler))
    app.add_handler(CommandHandler("help", help_handler))

    # Fallback for plain text (non-command) messages.
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, plain_text_handler))

    logger.info(
        "Bot configured with agents: %s",
        ", ".join(agents) if agents else "(none)",
    )

    return app


def main() -> None:
    """Entry point — build the application and start polling.

    Runs a pre-flight check to verify that the ``claude`` CLI is
    available and functional before starting the Telegram polling loop.
    """
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    # Load config early so we can use claude_path for the pre-flight check.
    config = load_config()

    # Pre-flight: verify the claude CLI is available.
    claude_command = config.claude_path or "claude"
    _check_claude_cli(claude_command)

    app = build_application(config=config)
    logger.info("Starting bot…")
    app.run_polling()
