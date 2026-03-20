"""Tests for telegram_bot.session module."""

from __future__ import annotations

import asyncio
import json
from typing import List, Optional
from unittest.mock import MagicMock, patch

import pytest

from telegram_bot.session import (
    Session,
    SessionManager,
    _extract_text_from_content,
    _extract_text_from_event,
)


# ── Python 3.7-compatible AsyncMock ────────────────────────────────

try:
    from unittest.mock import AsyncMock  # Python 3.8+
except ImportError:

    class AsyncMock(MagicMock):
        """Minimal AsyncMock for Python 3.7."""

        async def __call__(self, *args, **kwargs):
            return super().__call__(*args, **kwargs)

        def assert_awaited_once_with(self, *args, **kwargs):
            self.assert_called_once_with(*args, **kwargs)

        def assert_not_awaited(self):
            self.assert_not_called()

        @property
        def await_count(self):
            return self.call_count


# ── Helpers ────────────────────────────────────────────────────────


def _make_stream_json_line(event: dict) -> bytes:
    """Encode a dict as a stream-json stdout line (JSON + newline)."""
    return json.dumps(event).encode() + b"\n"


def _make_assistant_event(text: str) -> dict:
    """Build an assistant message event with the given text."""
    return {
        "type": "assistant",
        "message": {
            "role": "assistant",
            "content": [{"type": "text", "text": text}],
        },
    }


def _make_mock_process(
    stdout_lines: Optional[List[bytes]] = None,
    stderr_lines: Optional[List[bytes]] = None,
    returncode: int = 0,
    block_stdout: bool = False,
) -> MagicMock:
    """Build a mock ``asyncio.subprocess.Process``.

    ``stdout`` and ``stderr`` are mock streams whose ``readline()`` yields
    the given byte-strings one at a time, then returns ``b""`` to signal EOF.

    If *block_stdout* is ``True``, stdout will hang (``asyncio.sleep(9999)``)
    after delivering all lines instead of returning ``b""``.  This prevents
    the stdout reader from detecting a process exit and triggering crash
    handling during tests that need the session to stay alive.
    """
    process = MagicMock()
    process.pid = 12345
    process.returncode = returncode

    # stdin
    process.stdin = MagicMock()
    process.stdin.write = MagicMock()
    process.stdin.drain = AsyncMock()
    process.stdin.is_closing = MagicMock(return_value=False)

    # stdout
    stdout_data = list(stdout_lines or [])

    async def _stdout_readline(
        _iter=iter(stdout_data), _block=block_stdout
    ):
        try:
            return next(_iter)
        except StopIteration:
            if _block:
                await asyncio.sleep(9999)  # hang forever
            return b""

    process.stdout = MagicMock()
    process.stdout.readline = _stdout_readline

    # stderr
    stderr_data = list(stderr_lines or [])

    async def _stderr_readline(_iter=iter(stderr_data)):
        try:
            return next(_iter)
        except StopIteration:
            return b""

    process.stderr = MagicMock()
    process.stderr.readline = _stderr_readline

    # wait() resolves immediately by default
    process.wait = AsyncMock(return_value=returncode)
    process.kill = MagicMock()

    return process


def _make_session(
    process: Optional[MagicMock] = None,
    chat_id: int = 100,
    agent_name: str = "test-agent",
    on_response: Optional[AsyncMock] = None,
    on_end: Optional[AsyncMock] = None,
    idle_timeout: int = 600,
    shutdown_message: str = "Goodbye.",
    cleanup: Optional[MagicMock] = None,
) -> Session:
    """Build a ``Session`` with sensible defaults."""
    if process is None:
        process = _make_mock_process()
    if on_response is None:
        on_response = AsyncMock()
    if on_end is None:
        on_end = AsyncMock()
    return Session(
        chat_id=chat_id,
        agent_name=agent_name,
        process=process,
        on_response=on_response,
        on_end=on_end,
        idle_timeout=idle_timeout,
        shutdown_message=shutdown_message,
        cleanup=cleanup,
    )


# ── _extract_text_from_event unit tests ───────────────────────────


class TestExtractTextFromEvent:
    """Tests for the stream-json event parser."""

    def test_assistant_message_event(self) -> None:
        """Assistant message events should return the text content."""
        event = _make_assistant_event("Hello, world!")
        raw = json.dumps(event)
        assert _extract_text_from_event(raw) == "Hello, world!"

    def test_assistant_multi_block_content(self) -> None:
        """Multiple text blocks should be concatenated."""
        event = {
            "type": "assistant",
            "message": {
                "content": [
                    {"type": "text", "text": "Hello "},
                    {"type": "text", "text": "world!"},
                ],
            },
        }
        raw = json.dumps(event)
        assert _extract_text_from_event(raw) == "Hello world!"

    def test_content_block_delta_text(self) -> None:
        """content_block_delta with text_delta should return the text."""
        event = {
            "type": "content_block_delta",
            "delta": {"type": "text_delta", "text": "partial"},
        }
        raw = json.dumps(event)
        assert _extract_text_from_event(raw) == "partial"

    def test_content_block_delta_non_text(self) -> None:
        """content_block_delta with non-text delta should return None."""
        event = {
            "type": "content_block_delta",
            "delta": {"type": "input_json_delta", "partial_json": "{}"},
        }
        raw = json.dumps(event)
        assert _extract_text_from_event(raw) is None

    def test_result_with_text_skipped(self) -> None:
        """Result events with text should be skipped (returns None).

        The result event is a turn-level summary that duplicates content
        already delivered via the assistant event.
        """
        event = {"type": "result", "result": "Task completed."}
        raw = json.dumps(event)
        assert _extract_text_from_event(raw) is None

    def test_result_without_text_skipped(self) -> None:
        """Result events without text should also be skipped."""
        event = {"type": "result", "result": None}
        raw = json.dumps(event)
        assert _extract_text_from_event(raw) is None

    def test_result_with_dict_payload_skipped(self) -> None:
        """Result events with dict payloads should be skipped."""
        event = {"type": "result", "result": {"text": "summary"}}
        raw = json.dumps(event)
        assert _extract_text_from_event(raw) is None

    def test_tool_use_event_skipped(self) -> None:
        """Tool use events should be skipped."""
        event = {"type": "tool_use", "name": "bash", "input": {"cmd": "ls"}}
        raw = json.dumps(event)
        assert _extract_text_from_event(raw) is None

    def test_system_event_skipped(self) -> None:
        """System events should be skipped."""
        event = {"type": "system", "subtype": "init"}
        raw = json.dumps(event)
        assert _extract_text_from_event(raw) is None

    def test_message_start_skipped(self) -> None:
        """message_start events should be skipped."""
        event = {"type": "message_start"}
        raw = json.dumps(event)
        assert _extract_text_from_event(raw) is None

    def test_non_json_passed_through(self) -> None:
        """Non-JSON lines should be passed through as-is."""
        raw = "This is plain text output"
        assert _extract_text_from_event(raw) == raw

    def test_malformed_json_passed_through(self) -> None:
        """Malformed JSON should be passed through as-is."""
        raw = '{"type": "assistant", broken'
        assert _extract_text_from_event(raw) == raw

    def test_unknown_event_type_skipped(self) -> None:
        """Unknown event types should return None."""
        event = {"type": "some_unknown_type", "data": "stuff"}
        raw = json.dumps(event)
        assert _extract_text_from_event(raw) is None

    def test_assistant_with_string_content(self) -> None:
        """Assistant event where content is a plain string (not list)."""
        event = {
            "type": "assistant",
            "message": {"content": "Plain string response"},
        }
        raw = json.dumps(event)
        assert _extract_text_from_event(raw) == "Plain string response"

    def test_assistant_with_no_text_blocks(self) -> None:
        """Assistant event with only non-text content blocks returns None."""
        event = {
            "type": "assistant",
            "message": {
                "content": [{"type": "tool_use", "name": "bash"}],
            },
        }
        raw = json.dumps(event)
        assert _extract_text_from_event(raw) is None


class TestExtractTextFromContent:
    """Tests for the content block text extractor."""

    def test_single_text_block(self) -> None:
        content = [{"type": "text", "text": "Hello"}]
        assert _extract_text_from_content(content) == "Hello"

    def test_multiple_text_blocks(self) -> None:
        content = [
            {"type": "text", "text": "A"},
            {"type": "text", "text": "B"},
        ]
        assert _extract_text_from_content(content) == "AB"

    def test_mixed_blocks(self) -> None:
        content = [
            {"type": "text", "text": "Hello"},
            {"type": "tool_use", "name": "bash"},
            {"type": "text", "text": " world"},
        ]
        assert _extract_text_from_content(content) == "Hello world"

    def test_empty_list(self) -> None:
        assert _extract_text_from_content([]) is None

    def test_string_content(self) -> None:
        assert _extract_text_from_content("Direct string") == "Direct string"

    def test_none_content(self) -> None:
        assert _extract_text_from_content(None) is None


# ── Session: spawning & reading ────────────────────────────────────


class TestSessionReading:
    """Tests for stdout/stderr reading tasks."""

    @pytest.mark.asyncio
    async def test_stdout_json_events_invoke_on_response(self) -> None:
        """Assistant JSON events on stdout should be relayed via on_response."""
        on_response = AsyncMock()
        process = _make_mock_process(
            stdout_lines=[
                _make_stream_json_line(_make_assistant_event("Hello")),
                _make_stream_json_line(_make_assistant_event("World")),
            ],
        )
        session = _make_session(process=process, on_response=on_response)
        session.start()

        # Let the event loop run the reader tasks.
        await asyncio.sleep(0.05)

        assert on_response.call_count == 2
        on_response.assert_any_call(100, "Hello")
        on_response.assert_any_call(100, "World")

    @pytest.mark.asyncio
    async def test_stdout_skips_non_text_events(self) -> None:
        """Non-text events (system, tool_use) should NOT trigger on_response."""
        on_response = AsyncMock()
        process = _make_mock_process(
            stdout_lines=[
                _make_stream_json_line({"type": "system", "subtype": "init"}),
                _make_stream_json_line(_make_assistant_event("Hello")),
                _make_stream_json_line({"type": "tool_use", "name": "bash"}),
            ],
        )
        session = _make_session(process=process, on_response=on_response)
        session.start()

        await asyncio.sleep(0.05)

        # Only the assistant event should trigger on_response.
        assert on_response.call_count == 1
        on_response.assert_called_with(100, "Hello")

    @pytest.mark.asyncio
    async def test_stdout_handles_plain_text_fallback(self) -> None:
        """Non-JSON stdout lines should be passed through as-is."""
        on_response = AsyncMock()
        process = _make_mock_process(
            stdout_lines=[b"Plain text output\n"],
        )
        session = _make_session(process=process, on_response=on_response)
        session.start()

        await asyncio.sleep(0.05)

        on_response.assert_called_once_with(100, "Plain text output")

    @pytest.mark.asyncio
    async def test_stderr_is_logged_not_relayed(self) -> None:
        """Agent stderr should be logged but NOT passed to on_response."""
        on_response = AsyncMock()
        process = _make_mock_process(
            stderr_lines=[b"debug info\n"],
        )
        session = _make_session(process=process, on_response=on_response)
        session.start()

        await asyncio.sleep(0.05)

        # on_response should not have been called for stderr content.
        for call_args in on_response.call_args_list:
            assert "debug info" not in str(call_args)

    @pytest.mark.asyncio
    async def test_stderr_logged_at_warning_level(self) -> None:
        """Agent stderr should be logged at WARNING level."""
        on_response = AsyncMock()
        process = _make_mock_process(
            stderr_lines=[b"something went wrong\n"],
            block_stdout=True,
        )
        session = _make_session(process=process, on_response=on_response)

        with patch("telegram_bot.session.logger") as mock_logger:
            session.start()
            await asyncio.sleep(0.05)

            mock_logger.warning.assert_called_once_with(
                "Agent %s stderr: %s",
                session.agent_name,
                "something went wrong",
            )
            # Ensure it was NOT logged at debug level.
            for call_args in mock_logger.debug.call_args_list:
                assert "something went wrong" not in str(call_args)

    @pytest.mark.asyncio
    async def test_stdout_reader_logs_lifecycle(self) -> None:
        """The stdout reader should log start and end events."""
        process = _make_mock_process(
            stdout_lines=[
                _make_stream_json_line(_make_assistant_event("Hi")),
            ],
        )
        session = _make_session(process=process)

        with patch("telegram_bot.session.logger") as mock_logger:
            session.start()
            await asyncio.sleep(0.05)

            # Check that info was called with "started" and "ended" messages.
            info_messages = [
                str(call) for call in mock_logger.info.call_args_list
            ]
            assert any("stdout reader started" in msg for msg in info_messages)
            assert any("stdout reader ended" in msg for msg in info_messages)


# ── Session: sending messages ──────────────────────────────────────


class TestSessionSend:
    """Tests for sending messages to the agent's stdin."""

    @pytest.mark.asyncio
    async def test_send_writes_json_to_stdin(self) -> None:
        """User messages should be written as stream-json to process stdin."""
        process = _make_mock_process(block_stdout=True)
        session = _make_session(process=process)
        session.start()

        await session.send("Hello agent")

        expected = json.dumps({"type": "user", "message": {"role": "user", "content": "Hello agent"}})
        process.stdin.write.assert_called_with(expected.encode() + b"\n")
        process.stdin.drain.assert_called()

    @pytest.mark.asyncio
    async def test_send_updates_last_activity(self) -> None:
        """Sending a message should update last_activity."""
        process = _make_mock_process(block_stdout=True)
        session = _make_session(process=process)
        session.start()
        old_activity = session.last_activity

        # Small sleep so monotonic() advances.
        await asyncio.sleep(0.01)
        await session.send("ping")

        assert session.last_activity > old_activity

    @pytest.mark.asyncio
    async def test_send_raises_after_shutdown(self) -> None:
        """Sending after shutdown should raise RuntimeError."""
        process = _make_mock_process(block_stdout=True)
        session = _make_session(process=process)
        session.start()
        await session.shutdown()

        with pytest.raises(RuntimeError, match="no longer active"):
            await session.send("too late")


# ── Session: graceful shutdown ─────────────────────────────────────


class TestSessionShutdown:
    """Tests for graceful session shutdown."""

    @pytest.mark.asyncio
    async def test_shutdown_sends_json_shutdown_message(self) -> None:
        """Shutdown should send the shutdown_message as stream-json to stdin."""
        process = _make_mock_process(block_stdout=True)
        session = _make_session(
            process=process, shutdown_message="Please exit."
        )
        session.start()

        await session.shutdown()

        expected = json.dumps({"type": "user", "message": {"role": "user", "content": "Please exit."}})
        process.stdin.write.assert_called_with(expected.encode() + b"\n")

    @pytest.mark.asyncio
    async def test_shutdown_invokes_on_end_with_reason(self) -> None:
        """on_end should be called with the correct reason."""
        on_end = AsyncMock()
        process = _make_mock_process(block_stdout=True)
        session = _make_session(process=process, on_end=on_end)
        session.start()

        await session.shutdown(reason="shutdown")

        on_end.assert_called_once_with(100, "test-agent", "shutdown", stderr_tail="")

    @pytest.mark.asyncio
    async def test_shutdown_cleans_up_via_callback(self) -> None:
        """The cleanup callback should be invoked on shutdown."""
        cleanup = MagicMock()
        process = _make_mock_process(block_stdout=True)
        session = _make_session(process=process, cleanup=cleanup)
        session.start()

        await session.shutdown()

        cleanup.assert_called_once_with(100)

    @pytest.mark.asyncio
    async def test_shutdown_force_kills_on_timeout(self) -> None:
        """If the process doesn't exit within the timeout, kill it."""
        process = _make_mock_process(block_stdout=True)

        # Make wait() hang forever the first time, then resolve after kill.
        wait_call_count = 0

        async def slow_wait():
            nonlocal wait_call_count
            wait_call_count += 1
            if wait_call_count <= 1:
                # Hang until cancelled by wait_for timeout.
                await asyncio.sleep(9999)
            return 0

        # Replace process.wait with a real coroutine function.
        process.wait = slow_wait

        session = _make_session(process=process)
        session.start()

        # Patch _SHUTDOWN_TIMEOUT to a very short value for the test.
        with patch("telegram_bot.session._SHUTDOWN_TIMEOUT", 0.1):
            await session.shutdown()

        process.kill.assert_called_once()

    @pytest.mark.asyncio
    async def test_double_shutdown_is_safe(self) -> None:
        """Calling shutdown twice should not error or double-invoke on_end."""
        on_end = AsyncMock()
        process = _make_mock_process(block_stdout=True)
        session = _make_session(process=process, on_end=on_end)
        session.start()

        await session.shutdown()
        await session.shutdown()

        assert on_end.call_count == 1


# ── Session: idle timeout ──────────────────────────────────────────


class TestSessionIdleTimeout:
    """Tests for the idle timeout mechanism."""

    @pytest.mark.asyncio
    async def test_idle_timeout_triggers_shutdown(self) -> None:
        """After idle_timeout seconds of inactivity, shutdown is triggered."""
        on_end = AsyncMock()
        process = _make_mock_process(block_stdout=True)
        session = _make_session(
            process=process,
            on_end=on_end,
            idle_timeout=1,  # 1 second for fast test
        )
        session.start()

        # Wait for the idle timeout to fire.
        await asyncio.sleep(1.5)

        on_end.assert_called_once_with(100, "test-agent", "timeout", stderr_tail="")

    @pytest.mark.asyncio
    async def test_idle_timeout_does_not_raise_cancelled_error(self) -> None:
        """Idle timeout should not cause CancelledError in the on_end callback.

        Regression test for the bug where _finish() unconditionally cancelled
        all background tasks — including the currently executing _idle_task —
        causing a CancelledError to fire during the on_end callback.
        """
        on_end_called_successfully = False
        on_end_error = None

        async def on_end_callback(chat_id, agent_name, reason, **kwargs):
            nonlocal on_end_called_successfully, on_end_error
            try:
                # Simulate an async operation (like sending a Telegram message)
                # that would be interrupted by CancelledError if the fix is
                # not in place.
                await asyncio.sleep(0.01)
                on_end_called_successfully = True
            except asyncio.CancelledError:
                on_end_error = "CancelledError during on_end"
                raise

        process = _make_mock_process(block_stdout=True)
        session = _make_session(
            process=process,
            on_end=on_end_callback,
            idle_timeout=1,
        )
        session.start()

        # Wait for idle timeout to fire.
        await asyncio.sleep(1.5)

        assert on_end_error is None, f"on_end raised: {on_end_error}"
        assert on_end_called_successfully, "on_end was not called successfully"

    @pytest.mark.asyncio
    async def test_finish_skips_cancelling_current_task(self) -> None:
        """_finish() should not cancel the task it is running inside of."""
        on_end = AsyncMock()
        process = _make_mock_process(block_stdout=True)
        session = _make_session(process=process, on_end=on_end)
        session.start()

        # Directly call _finish from within a known task context and verify
        # the current task is not cancelled.
        current = asyncio.current_task()

        # Pretend one of the background tasks IS the current task.
        session._idle_task = current

        await session._finish("test")

        # The current task should still be alive (not cancelled).
        assert not current.cancelled()
        on_end.assert_called_once_with(100, "test-agent", "test", stderr_tail="")

    @pytest.mark.asyncio
    async def test_stdout_output_resets_idle_timer(self) -> None:
        """Agent stdout output should reset the idle timer, preventing timeout.

        This is the core test for the fix: _read_stdout() must call
        self.last_activity = time.monotonic() and self._reset_idle_timer()
        for every non-empty stdout line.
        """
        on_end = AsyncMock()

        # We'll feed stdout lines at timed intervals using a custom readline.
        # The idle timeout is 1s. We send a stdout line at 0.7s, which should
        # reset the timer. Without the fix, the session would die at 1s.
        lines_delivered = 0

        async def _timed_stdout_readline():
            nonlocal lines_delivered
            if lines_delivered == 0:
                # First line delivered after 0.7s
                await asyncio.sleep(0.7)
                lines_delivered += 1
                event = {"type": "tool_use", "name": "bash", "input": {"cmd": "ls"}}
                return json.dumps(event).encode() + b"\n"
            else:
                # Then hang forever (no more output)
                await asyncio.sleep(9999)
                return b""

        process = _make_mock_process(block_stdout=True)
        process.stdout.readline = _timed_stdout_readline

        session = _make_session(
            process=process,
            on_end=on_end,
            idle_timeout=1,
        )
        session.start()

        # At 1.0s the session should NOT have timed out (timer reset at 0.7s).
        await asyncio.sleep(1.0)
        on_end.assert_not_called()

        # At ~1.8s (0.7 + 1.0 + buffer) it should have timed out.
        await asyncio.sleep(0.9)
        on_end.assert_called_once_with(100, "test-agent", "timeout", stderr_tail="")

    @pytest.mark.asyncio
    async def test_stdout_updates_last_activity(self) -> None:
        """Assistant text events on stdout should also reset the idle timer.

        This complements test_stdout_output_resets_idle_timer (which uses
        tool_use events) by verifying that text-producing assistant events
        also reset the timer.
        """
        on_end = AsyncMock()
        lines_delivered = 0

        async def _timed_stdout_readline():
            nonlocal lines_delivered
            if lines_delivered == 0:
                await asyncio.sleep(0.7)
                lines_delivered += 1
                event = _make_assistant_event("Hello from agent")
                return json.dumps(event).encode() + b"\n"
            else:
                await asyncio.sleep(9999)
                return b""

        process = _make_mock_process(block_stdout=True)
        process.stdout.readline = _timed_stdout_readline

        session = _make_session(
            process=process,
            on_end=on_end,
            idle_timeout=1,
        )
        session.start()

        # At 1.0s: stdout event at 0.7s should have reset the timer.
        # Without the fix, timeout would fire at 1.0s.
        await asyncio.sleep(1.0)
        on_end.assert_not_called()

        # At ~1.9s (0.7 + 1.0 + buffer) it should have timed out.
        await asyncio.sleep(0.9)
        on_end.assert_called_once_with(100, "test-agent", "timeout", stderr_tail="")

    @pytest.mark.asyncio
    async def test_non_text_stdout_events_reset_idle_timer(self) -> None:
        """Non-text events (tool_use, system) should also reset the idle timer.

        The fix resets the timer for ALL non-empty stdout lines, not just
        those that produce user-visible text.  Uses a single tool_use event
        (no user-visible text) to verify the timer resets.
        """
        on_end = AsyncMock()
        lines_delivered = 0

        async def _timed_stdout_readline():
            nonlocal lines_delivered
            if lines_delivered == 0:
                await asyncio.sleep(0.7)
                lines_delivered += 1
                # tool_use event — produces no user-visible text
                event = {"type": "tool_use", "name": "Read", "input": {"path": "/tmp/x"}}
                return json.dumps(event).encode() + b"\n"
            else:
                await asyncio.sleep(9999)
                return b""

        process = _make_mock_process(block_stdout=True)
        process.stdout.readline = _timed_stdout_readline

        session = _make_session(
            process=process,
            on_end=on_end,
            idle_timeout=1,
        )
        session.start()

        # At 1.0s: timer was reset at 0.7s by tool_use event, should not have timed out
        await asyncio.sleep(1.0)
        on_end.assert_not_called()

        # At ~1.9s: 0.7 + 1.0 + buffer → should have timed out
        await asyncio.sleep(0.9)
        on_end.assert_called_once_with(100, "test-agent", "timeout", stderr_tail="")

    @pytest.mark.asyncio
    async def test_activity_resets_idle_timer(self) -> None:
        """Sending a message should reset the idle timer."""
        on_end = AsyncMock()
        process = _make_mock_process(block_stdout=True)
        session = _make_session(
            process=process,
            on_end=on_end,
            idle_timeout=1,
        )
        session.start()

        # Send a message just before timeout would fire.
        await asyncio.sleep(0.7)
        await session.send("still here")
        await asyncio.sleep(0.7)

        # Should NOT have timed out yet (total ~1.4s, but reset at 0.7s).
        on_end.assert_not_called()

        # Now wait for it to actually time out.
        await asyncio.sleep(0.5)
        on_end.assert_called_once_with(100, "test-agent", "timeout", stderr_tail="")


# ── Session: crash detection ───────────────────────────────────────


class TestSessionCrashDetection:
    """Tests for unexpected process exit (crash) detection."""

    @pytest.mark.asyncio
    async def test_unexpected_exit_fires_crash_callback(self) -> None:
        """If the agent exits without a shutdown, on_end('crash') fires."""
        on_end = AsyncMock()
        # Stdout returns empty immediately → process exited.
        process = _make_mock_process(returncode=1)
        session = _make_session(process=process, on_end=on_end)
        session.start()

        await asyncio.sleep(0.05)

        on_end.assert_called_once_with(
            100, "test-agent", "crash", stderr_tail=""
        )

    @pytest.mark.asyncio
    async def test_crash_cleans_up_session(self) -> None:
        """Crash should invoke the cleanup callback."""
        cleanup = MagicMock()
        process = _make_mock_process(returncode=1)
        session = _make_session(process=process, cleanup=cleanup)
        session.start()

        await asyncio.sleep(0.05)

        cleanup.assert_called_once_with(100)


# ── SessionManager ─────────────────────────────────────────────────


class TestSessionManagerStart:
    """Tests for SessionManager.start_session."""

    @pytest.mark.asyncio
    async def test_start_session_spawns_process_with_stream_json_flags(self) -> None:
        """start_session should spawn claude with --print and stream-json flags."""
        mgr = SessionManager(
            idle_timeout=600,
            shutdown_message="Goodbye.",
        )
        mock_process = _make_mock_process()

        with patch(
            "telegram_bot.session.asyncio.create_subprocess_exec",
            new=AsyncMock(return_value=mock_process),
        ) as mock_exec:
            session = await mgr.start_session(
                chat_id=100,
                agent_name="designer",
                on_response=AsyncMock(),
                on_end=AsyncMock(),
            )

            mock_exec.assert_called_once()
            args = mock_exec.call_args
            positional = args[0]
            assert positional[:3] == ("claude", "--agent", "designer")
            assert "--print" in positional
            assert "--verbose" in positional
            assert "--output-format" in positional
            assert "stream-json" in positional
            assert "--input-format" in positional
            assert "--permission-mode" in positional
            assert "bypassPermissions" in positional
            assert session.chat_id == 100
            assert session.agent_name == "designer"

    @pytest.mark.asyncio
    async def test_start_session_uses_custom_claude_command(self) -> None:
        """start_session should use the configured claude_command."""
        mgr = SessionManager(
            idle_timeout=600,
            shutdown_message="Goodbye.",
            claude_command="/opt/bin/claude",
        )
        mock_process = _make_mock_process()

        with patch(
            "telegram_bot.session.asyncio.create_subprocess_exec",
            new=AsyncMock(return_value=mock_process),
        ) as mock_exec:
            await mgr.start_session(
                chat_id=100,
                agent_name="designer",
                on_response=AsyncMock(),
                on_end=AsyncMock(),
            )

            mock_exec.assert_called_once()
            args = mock_exec.call_args
            positional = args[0]
            assert positional[0] == "/opt/bin/claude"
            assert positional[1:3] == ("--agent", "designer")

    @pytest.mark.asyncio
    async def test_start_session_defaults_to_claude(self) -> None:
        """Without claude_command, 'claude' should be the default executable."""
        mgr = SessionManager(
            idle_timeout=600,
            shutdown_message="Goodbye.",
        )
        mock_process = _make_mock_process()

        with patch(
            "telegram_bot.session.asyncio.create_subprocess_exec",
            new=AsyncMock(return_value=mock_process),
        ) as mock_exec:
            await mgr.start_session(
                chat_id=100,
                agent_name="designer",
                on_response=AsyncMock(),
                on_end=AsyncMock(),
            )

            positional = mock_exec.call_args[0]
            assert positional[0] == "claude"

    @pytest.mark.asyncio
    async def test_start_session_rejects_duplicate(self) -> None:
        """Starting a second session for the same user should raise."""
        mgr = SessionManager(
            idle_timeout=600,
            shutdown_message="Goodbye.",
        )
        mock_process = _make_mock_process()

        with patch(
            "telegram_bot.session.asyncio.create_subprocess_exec",
            new=AsyncMock(return_value=mock_process),
        ):
            await mgr.start_session(
                chat_id=100,
                agent_name="designer",
                on_response=AsyncMock(),
                on_end=AsyncMock(),
            )

            with pytest.raises(ValueError, match="already has an active session"):
                await mgr.start_session(
                    chat_id=100,
                    agent_name="developer",
                    on_response=AsyncMock(),
                    on_end=AsyncMock(),
                )


class TestSessionManagerSend:
    """Tests for SessionManager.send_message."""

    @pytest.mark.asyncio
    async def test_send_message_forwards_json_to_session(self) -> None:
        """send_message should write JSON to the correct session's stdin."""
        mgr = SessionManager(
            idle_timeout=600,
            shutdown_message="Goodbye.",
        )
        mock_process = _make_mock_process()

        with patch(
            "telegram_bot.session.asyncio.create_subprocess_exec",
            new=AsyncMock(return_value=mock_process),
        ):
            await mgr.start_session(
                chat_id=100,
                agent_name="designer",
                on_response=AsyncMock(),
                on_end=AsyncMock(),
            )

            await mgr.send_message(100, "Hello")

            expected = json.dumps({"type": "user", "message": {"role": "user", "content": "Hello"}})
            mock_process.stdin.write.assert_called_with(
                expected.encode() + b"\n"
            )

    @pytest.mark.asyncio
    async def test_send_message_no_session_raises(self) -> None:
        """send_message should raise if there's no active session."""
        mgr = SessionManager(
            idle_timeout=600,
            shutdown_message="Goodbye.",
        )

        with pytest.raises(ValueError, match="No active session"):
            await mgr.send_message(999, "Hello")


class TestSessionManagerEnd:
    """Tests for SessionManager.end_session."""

    @pytest.mark.asyncio
    async def test_end_session_shuts_down_and_removes(self) -> None:
        """end_session should gracefully shut down and remove the session."""
        mgr = SessionManager(
            idle_timeout=600,
            shutdown_message="Goodbye.",
        )
        mock_process = _make_mock_process()

        with patch(
            "telegram_bot.session.asyncio.create_subprocess_exec",
            new=AsyncMock(return_value=mock_process),
        ):
            await mgr.start_session(
                chat_id=100,
                agent_name="designer",
                on_response=AsyncMock(),
                on_end=AsyncMock(),
            )

            assert mgr.has_session(100)
            await mgr.end_session(100)
            assert not mgr.has_session(100)

    @pytest.mark.asyncio
    async def test_end_nonexistent_session_is_noop(self) -> None:
        """Ending a session that doesn't exist should not error."""
        mgr = SessionManager(
            idle_timeout=600,
            shutdown_message="Goodbye.",
        )
        await mgr.end_session(999)  # Should not raise.


class TestSessionManagerHasSession:
    """Tests for SessionManager.has_session."""

    @pytest.mark.asyncio
    async def test_has_session_reflects_state(self) -> None:
        """has_session should reflect whether a session exists."""
        mgr = SessionManager(
            idle_timeout=600,
            shutdown_message="Goodbye.",
        )
        assert not mgr.has_session(100)

        mock_process = _make_mock_process()
        with patch(
            "telegram_bot.session.asyncio.create_subprocess_exec",
            new=AsyncMock(return_value=mock_process),
        ):
            await mgr.start_session(
                chat_id=100,
                agent_name="designer",
                on_response=AsyncMock(),
                on_end=AsyncMock(),
            )

        assert mgr.has_session(100)


# ── Session: stderr buffering ──────────────────────────────────────


class TestSessionStderrBuffering:
    """Tests for stderr line buffering and the stderr_tail property."""

    def test_stderr_tail_empty_when_no_stderr(self) -> None:
        """stderr_tail returns empty string when no stderr was captured."""
        session = _make_session(process=_make_mock_process())
        assert session.stderr_tail == ""

    @pytest.mark.asyncio
    async def test_stderr_lines_buffered(self) -> None:
        """stderr lines should be buffered in the session."""
        process = _make_mock_process(
            stderr_lines=[b"line 1\n", b"line 2\n", b"line 3\n"],
            block_stdout=True,
        )
        session = _make_session(process=process)
        session.start()

        await asyncio.sleep(0.05)

        assert session.stderr_tail == "line 1\nline 2\nline 3"

    @pytest.mark.asyncio
    async def test_stderr_buffer_bounded_to_last_n_lines(self) -> None:
        """Only the last _STDERR_BUFFER_LINES lines should be kept."""
        lines = [f"line {i}\n".encode() for i in range(20)]
        process = _make_mock_process(
            stderr_lines=lines,
            block_stdout=True,
        )
        session = _make_session(process=process)
        session.start()

        await asyncio.sleep(0.05)

        tail = session.stderr_tail
        # Should only contain the last 10 lines.
        assert "line 10" in tail
        assert "line 19" in tail
        assert "line 0" not in tail
        assert "line 9" not in tail

    @pytest.mark.asyncio
    async def test_stderr_tail_truncated_to_max_chars(self) -> None:
        """stderr_tail should be truncated to _STDERR_MAX_CHARS."""
        # Each line is ~100 chars; 10 lines = ~1000 chars > 500 limit
        lines = [(f"{'x' * 95} {i}\n").encode() for i in range(10)]
        process = _make_mock_process(
            stderr_lines=lines,
            block_stdout=True,
        )
        session = _make_session(process=process)
        session.start()

        await asyncio.sleep(0.05)

        tail = session.stderr_tail
        assert len(tail) <= 500

    @pytest.mark.asyncio
    async def test_crash_passes_stderr_tail_to_on_end(self) -> None:
        """On crash, on_end should receive the buffered stderr content.

        Uses a stdout that delivers one line before EOF so the stderr
        reader has time to consume its lines first.
        """
        on_end = AsyncMock()
        # Provide a stdout line so the stdout reader doesn't finish
        # instantly — this gives the stderr reader time to buffer.
        process = _make_mock_process(
            stdout_lines=[
                _make_stream_json_line({"type": "system", "subtype": "init"}),
            ],
            stderr_lines=[b"error: node not found\n", b"fatal crash\n"],
            returncode=1,
        )
        session = _make_session(process=process, on_end=on_end)
        session.start()

        await asyncio.sleep(0.15)

        on_end.assert_called_once()
        # Python 3.7: call_args is (args, kwargs) tuple
        _, kwargs = on_end.call_args
        assert kwargs["stderr_tail"] == "error: node not found\nfatal crash"

    @pytest.mark.asyncio
    async def test_crash_with_empty_stderr_passes_empty_string(self) -> None:
        """On crash with no stderr, on_end receives empty stderr_tail."""
        on_end = AsyncMock()
        process = _make_mock_process(returncode=1)
        session = _make_session(process=process, on_end=on_end)
        session.start()

        await asyncio.sleep(0.05)

        on_end.assert_called_once_with(
            100, "test-agent", "crash", stderr_tail=""
        )
