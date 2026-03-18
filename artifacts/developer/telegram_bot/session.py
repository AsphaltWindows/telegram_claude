"""Session management for Claude agent subprocesses.

Manages the lifecycle of ``claude --agent <name>`` processes, including
spawning, stdin/stdout communication, idle timeouts, and graceful shutdown.

The subprocess is invoked in non-interactive (print) mode with stream-json
I/O, enabling structured communication over stdin/stdout pipes.
"""

from __future__ import annotations

import asyncio
import collections
import json
import logging
import time
from pathlib import Path
from typing import Any, Callable, Deque, Dict, List, Optional

logger = logging.getLogger(__name__)

# Project root — inherited from the process working directory.
# The launcher script (run_bot.sh) is expected to cd to the project root
# before starting the bot, making Path.cwd() the correct value.
_PROJECT_ROOT = Path.cwd()

# Timeout in seconds before force-killing the process during graceful shutdown.
_SHUTDOWN_TIMEOUT = 60

# Maximum number of stderr lines to buffer for crash diagnostics.
_STDERR_BUFFER_LINES = 10

# Maximum characters of stderr to include in crash messages.
_STDERR_MAX_CHARS = 500


def _extract_text_from_event(raw: str) -> Optional[str]:
    """Parse a stream-json line and return assistant text content, if any.

    The function handles several known event shapes emitted by ``claude``
    in ``--output-format stream-json`` mode:

    * **assistant message** — ``{"type": "assistant", "message": {"content":
      [{"type": "text", "text": "..."}]}}``
    * **content_block_delta** — ``{"type": "content_block_delta", "delta":
      {"type": "text_delta", "text": "..."}}``
    Events that do not carry displayable text (tool-use, system, result, etc.)
    return ``None``.  The ``result`` event is a turn-level summary that
    duplicates content already delivered via the ``assistant`` event and is
    therefore skipped.

    Parameters
    ----------
    raw:
        A single line of text from the subprocess stdout.

    Returns
    -------
    str or None
        The extracted text, or ``None`` if the event is not relevant.
    """
    try:
        event: Dict[str, Any] = json.loads(raw)
    except (json.JSONDecodeError, ValueError):
        # Not valid JSON — could be a plain-text fallback or debug line.
        logger.debug("Non-JSON stdout line (passing through): %s", raw[:200])
        return raw  # Pass through as-is so non-JSON output is still relayed.

    if not isinstance(event, dict):
        return None

    event_type = event.get("type", "")

    # --- assistant message with content blocks ---
    if event_type == "assistant":
        message = event.get("message", event)
        return _extract_text_from_content(message.get("content", []))

    # --- streaming content_block_delta ---
    if event_type == "content_block_delta":
        delta = event.get("delta", {})
        if isinstance(delta, dict) and delta.get("type") == "text_delta":
            return delta.get("text")
        return None

    # --- events we intentionally skip ---
    if event_type in (
        "result",
        "system",
        "tool_use",
        "tool_result",
        "content_block_start",
        "content_block_stop",
        "message_start",
        "message_stop",
        "message_delta",
        "ping",
        "error",
    ):
        logger.debug("Skipping %s event from %s", event_type, "agent")
        return None

    # Unknown event type — log and skip.
    logger.debug("Unknown stream-json event type '%s': %s", event_type, raw[:200])
    return None


def _extract_text_from_content(content: Any) -> Optional[str]:
    """Extract concatenated text from a ``content`` block list.

    Parameters
    ----------
    content:
        A list of content blocks, e.g.
        ``[{"type": "text", "text": "Hello"}, ...]``.

    Returns
    -------
    str or None
        Concatenated text from text blocks, or ``None`` if none found.
    """
    if not isinstance(content, list):
        if isinstance(content, str) and content.strip():
            return content
        return None

    parts: List[str] = []
    for block in content:
        if isinstance(block, dict) and block.get("type") == "text":
            text = block.get("text", "")
            if text:
                parts.append(text)
    return "".join(parts) if parts else None


class Session:
    """Manages a single Claude agent subprocess.

    Parameters
    ----------
    chat_id:
        Telegram chat ID for the user that owns this session.
    agent_name:
        Name of the agent (passed to ``claude --agent``).
    process:
        The spawned ``asyncio.subprocess.Process``.
    on_response:
        Async callback invoked with ``(chat_id, text)`` for each line
        the agent writes to stdout.
    on_end:
        Async callback invoked with ``(chat_id, agent_name, reason)``
        when the session ends.  ``reason`` is one of ``"shutdown"``,
        ``"timeout"``, or ``"crash"``.
    idle_timeout:
        Seconds of inactivity before the session is automatically ended.
    shutdown_message:
        Message sent to the agent's stdin to request a graceful exit.
    cleanup:
        Callable invoked with ``(chat_id,)`` to remove the session from
        the ``SessionManager``'s internal map.  May be ``None`` for
        standalone usage.
    """

    def __init__(
        self,
        chat_id: int,
        agent_name: str,
        process: asyncio.subprocess.Process,
        on_response: Callable,
        on_end: Callable,
        idle_timeout: int,
        shutdown_message: str,
        cleanup: Optional[Callable] = None,
    ) -> None:
        self.chat_id = chat_id
        self.agent_name = agent_name
        self.process = process
        self.last_activity: float = time.monotonic()

        self._on_response = on_response
        self._on_end = on_end
        self._idle_timeout = idle_timeout
        self._shutdown_message = shutdown_message
        self._cleanup = cleanup

        self._shutting_down = False
        self._ended = False

        # Circular buffer of the most recent stderr lines for crash diagnostics.
        self._stderr_lines: Deque[str] = collections.deque(
            maxlen=_STDERR_BUFFER_LINES
        )

        # Background tasks — started via ``start()``.
        self._stdout_task: Optional[asyncio.Task] = None
        self._stderr_task: Optional[asyncio.Task] = None
        self._idle_task: Optional[asyncio.Task] = None

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    @property
    def stderr_tail(self) -> str:
        """Return the last few stderr lines, truncated to a safe length.

        Returns
        -------
        str
            The most recent stderr output joined by newlines, truncated
            to ``_STDERR_MAX_CHARS`` characters.  Empty string if no
            stderr was captured.
        """
        if not self._stderr_lines:
            return ""
        joined = "\n".join(self._stderr_lines)
        if len(joined) > _STDERR_MAX_CHARS:
            return joined[-_STDERR_MAX_CHARS:]
        return joined

    def start(self) -> None:
        """Start the background reader and idle-timer tasks."""
        self._stdout_task = asyncio.create_task(self._read_stdout())
        self._stderr_task = asyncio.create_task(self._read_stderr())
        self._idle_task = asyncio.create_task(self._idle_timer())

    async def send(self, text: str) -> None:
        """Write a user message to the agent's stdin.

        The message is formatted as a stream-json event::

            {"type": "user", "message": {"role": "user", "content": "<text>"}}

        Parameters
        ----------
        text:
            The message to send.

        Raises
        ------
        RuntimeError
            If the session has already ended or is shutting down.
        """
        if self._ended or self._shutting_down:
            raise RuntimeError("Session is no longer active.")
        assert self.process.stdin is not None
        envelope = json.dumps({
            "type": "user",
            "message": {"role": "user", "content": text},
        })
        self.process.stdin.write(envelope.encode() + b"\n")
        await self.process.stdin.drain()
        self.last_activity = time.monotonic()
        self._reset_idle_timer()

    async def shutdown(self, reason: str = "shutdown") -> None:
        """Gracefully shut down the session.

        Sends the configured shutdown message to the agent, waits for
        the process to exit (with a timeout), and cleans up resources.

        Parameters
        ----------
        reason:
            Why the session is ending (``"shutdown"``, ``"timeout"``).
        """
        if self._ended:
            return
        if self._shutting_down:
            # Already in progress — just wait for the process to finish.
            await self._wait_for_process()
            return

        self._shutting_down = True

        # Cancel the idle timer — but only if we're not running inside it.
        current_task = asyncio.current_task() if hasattr(asyncio, 'current_task') else asyncio.Task.current_task()
        if (
            self._idle_task
            and not self._idle_task.done()
            and self._idle_task is not current_task
        ):
            self._idle_task.cancel()

        # Send shutdown message to the agent as a stream-json event.
        try:
            if self.process.stdin and not self.process.stdin.is_closing():
                envelope = json.dumps({
                    "type": "user",
                    "message": {"role": "user", "content": self._shutdown_message},
                })
                self.process.stdin.write(envelope.encode() + b"\n")
                await self.process.stdin.drain()
        except (BrokenPipeError, ConnectionResetError, OSError):
            logger.debug("Could not write shutdown message — pipe broken.")

        # Wait for the process to exit (stdout reader will invoke on_end).
        await self._wait_for_process()

        # If the stdout reader hasn't already triggered the end callback,
        # do it now.
        await self._finish(reason)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    async def _wait_for_process(self) -> None:
        """Wait for the subprocess to exit, force-killing on timeout."""
        try:
            await asyncio.wait_for(
                self.process.wait(), timeout=_SHUTDOWN_TIMEOUT
            )
        except asyncio.TimeoutError:
            logger.warning(
                "Agent %s (chat %d) did not exit within %ds — killing.",
                self.agent_name,
                self.chat_id,
                _SHUTDOWN_TIMEOUT,
            )
            self.process.kill()
            await self.process.wait()

    async def _finish(self, reason: str) -> None:
        """Invoke end callback and clean up, exactly once."""
        if self._ended:
            return
        self._ended = True

        # If the process has exited (crash or otherwise), give the stderr
        # reader a moment to drain remaining output before we cancel it.
        # This ensures stderr_tail captures diagnostic lines on crash.
        if self._stderr_task and not self._stderr_task.done():
            try:
                await asyncio.wait_for(
                    asyncio.shield(self._stderr_task), timeout=0.5
                )
            except (asyncio.TimeoutError, asyncio.CancelledError):
                pass

        # Cancel remaining background tasks — but not the currently executing
        # task, to avoid a spurious CancelledError during the on_end callback.
        current = asyncio.current_task() if hasattr(asyncio, 'current_task') else asyncio.Task.current_task()
        for task in (self._stdout_task, self._stderr_task, self._idle_task):
            if task and not task.done() and task is not current:
                task.cancel()

        # Notify the SessionManager to remove us.
        if self._cleanup:
            self._cleanup(self.chat_id)

        # Notify the bot layer.
        try:
            await self._on_end(
                self.chat_id, self.agent_name, reason,
                stderr_tail=self.stderr_tail,
            )
        except Exception:
            logger.exception("on_end callback raised an exception.")

    async def _read_stdout(self) -> None:
        """Continuously read stdout, parse stream-json events, and relay text.

        Each line from the subprocess is expected to be a newline-delimited
        JSON object (stream-json format).  Assistant text content is extracted
        and relayed via the ``on_response`` callback.  Non-text events (tool
        use, system messages, etc.) are logged at DEBUG level and skipped.
        """
        assert self.process.stdout is not None
        logger.info(
            "stdout reader started for agent %s (chat %d)",
            self.agent_name,
            self.chat_id,
        )
        try:
            while True:
                line = await self.process.stdout.readline()
                if not line:
                    # Process closed stdout.
                    break
                raw = line.decode(errors="replace").rstrip("\n")
                if not raw:
                    continue

                logger.debug(
                    "stdout line from %s: %s",
                    self.agent_name,
                    raw[:200],
                )

                text = _extract_text_from_event(raw)
                if text:
                    try:
                        await self._on_response(self.chat_id, text)
                    except Exception:
                        logger.exception("on_response callback raised.")
        except asyncio.CancelledError:
            logger.info(
                "stdout reader cancelled for agent %s (chat %d)",
                self.agent_name,
                self.chat_id,
            )
            return

        logger.info(
            "stdout reader ended for agent %s (chat %d)",
            self.agent_name,
            self.chat_id,
        )

        # Determine reason for exit.
        await self.process.wait()
        if not self._shutting_down:
            # Unexpected exit → crash.
            logger.warning(
                "Agent %s (chat %d) exited unexpectedly (rc=%s).",
                self.agent_name,
                self.chat_id,
                self.process.returncode,
            )
            await self._finish("crash")

    async def _read_stderr(self) -> None:
        """Continuously read stderr, log it, and buffer recent lines.

        The last ``_STDERR_BUFFER_LINES`` lines are kept in a circular
        buffer so they can be surfaced to the user on crash via
        ``stderr_tail``.
        """
        assert self.process.stderr is not None
        try:
            while True:
                line = await self.process.stderr.readline()
                if not line:
                    break
                text = line.decode(errors="replace").rstrip("\n")
                if text:
                    self._stderr_lines.append(text)
                    logger.warning(
                        "Agent %s stderr: %s", self.agent_name, text
                    )
        except asyncio.CancelledError:
            return

    async def _idle_timer(self) -> None:
        """Sleep until the idle timeout fires, then trigger shutdown."""
        try:
            while True:
                await asyncio.sleep(self._idle_timeout)
                elapsed = time.monotonic() - self.last_activity
                if elapsed >= self._idle_timeout:
                    logger.info(
                        "Session for chat %d timed out after %ds of inactivity.",
                        self.chat_id,
                        self._idle_timeout,
                    )
                    await self.shutdown(reason="timeout")
                    return
        except asyncio.CancelledError:
            return

    def _reset_idle_timer(self) -> None:
        """Cancel and restart the idle timer task."""
        if self._idle_task and not self._idle_task.done():
            self._idle_task.cancel()
        self._idle_task = asyncio.create_task(self._idle_timer())


class SessionManager:
    """Enforces one active session per user and manages session lifecycle.

    Parameters
    ----------
    idle_timeout:
        Seconds of inactivity before a session is automatically ended.
    shutdown_message:
        Message sent to the agent's stdin to request a graceful exit.
    project_root:
        Working directory for spawned agent processes.  Defaults to the
        detected project root.
    claude_command:
        Path or name of the ``claude`` CLI executable.  Defaults to
        ``"claude"`` (resolved via PATH).
    """

    def __init__(
        self,
        idle_timeout: int,
        shutdown_message: str,
        project_root: Optional[Path] = None,
        claude_command: str = "claude",
    ) -> None:
        self._idle_timeout = idle_timeout
        self._shutdown_message = shutdown_message
        self._project_root = project_root or _PROJECT_ROOT
        self._claude_command = claude_command
        self._sessions: Dict[int, Session] = {}

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def start_session(
        self,
        chat_id: int,
        agent_name: str,
        on_response: Callable,
        on_end: Callable,
    ) -> Session:
        """Spawn a new agent session for a user.

        Parameters
        ----------
        chat_id:
            Telegram chat ID.
        agent_name:
            Agent name (passed to ``claude --agent``).
        on_response:
            Async callback ``(chat_id, text)`` for agent output.
        on_end:
            Async callback ``(chat_id, agent_name, reason)`` on session end.

        Returns
        -------
        Session
            The newly created session.

        Raises
        ------
        ValueError
            If the user already has an active session.
        """
        if chat_id in self._sessions:
            raise ValueError(
                f"User {chat_id} already has an active session."
            )

        process = await asyncio.create_subprocess_exec(
            self._claude_command,
            "--agent",
            agent_name,
            "--print",
            "--verbose",
            "--output-format",
            "stream-json",
            "--input-format",
            "stream-json",
            "--permission-mode",
            "bypassPermissions",
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=str(self._project_root),
        )

        session = Session(
            chat_id=chat_id,
            agent_name=agent_name,
            process=process,
            on_response=on_response,
            on_end=on_end,
            idle_timeout=self._idle_timeout,
            shutdown_message=self._shutdown_message,
            cleanup=self._remove_session,
        )
        self._sessions[chat_id] = session
        session.start()

        logger.info(
            "Started session for chat %d with agent '%s' (pid=%d).",
            chat_id,
            agent_name,
            process.pid,
        )
        return session

    async def send_message(self, chat_id: int, text: str) -> None:
        """Send a message to the user's active session.

        Parameters
        ----------
        chat_id:
            Telegram chat ID.
        text:
            The message text.

        Raises
        ------
        ValueError
            If the user has no active session.
        """
        session = self._sessions.get(chat_id)
        if session is None:
            raise ValueError(f"No active session for user {chat_id}.")
        await session.send(text)

    async def end_session(self, chat_id: int) -> None:
        """Gracefully end the user's active session.

        Parameters
        ----------
        chat_id:
            Telegram chat ID.
        """
        session = self._sessions.get(chat_id)
        if session is None:
            return
        await session.shutdown(reason="shutdown")

    def has_session(self, chat_id: int) -> bool:
        """Return ``True`` if the user has an active session."""
        return chat_id in self._sessions

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _remove_session(self, chat_id: int) -> None:
        """Remove a session from the internal map (called by Session)."""
        self._sessions.pop(chat_id, None)
