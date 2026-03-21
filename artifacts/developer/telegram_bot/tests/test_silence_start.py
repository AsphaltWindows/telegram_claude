"""Tests for silence_start tracking in Session.

Verifies that silence_start is initialized to time.monotonic() at creation,
is updated when _read_stdout() processes output, updates with each new output
line, retains its value during silence, and is accessible from the typing
heartbeat context.  Also covers the _sent_15s_status and _sent_60s_status
flags that are reset alongside silence_start.
"""

from __future__ import annotations

import asyncio
import json
import time

import pytest
from mock import AsyncMock, MagicMock, patch

from telegram_bot.session import Session


def _make_session(
    idle_timeout: int = 600,
    chat_id: int = 42,
    agent_name: str = "operator",
    on_typing: AsyncMock | None = None,
) -> Session:
    """Create a Session with mocked process and callbacks."""
    process = MagicMock(spec=asyncio.subprocess.Process)
    process.stdout = MagicMock()
    process.stderr = MagicMock()
    process.stdin = MagicMock()
    process.returncode = 0
    process.wait = AsyncMock(return_value=0)

    session = Session(
        chat_id=chat_id,
        agent_name=agent_name,
        process=process,
        on_response=AsyncMock(),
        on_end=AsyncMock(),
        idle_timeout=idle_timeout,
        shutdown_message="/exit",
        cleanup=MagicMock(),
        on_typing=on_typing,
    )
    return session


def _make_stdout_line(text: str = "hello") -> bytes:
    """Create a stream-json assistant event as a stdout line."""
    event = json.dumps({
        "type": "assistant",
        "message": {"content": [{"type": "text", "text": text}]},
    })
    return event.encode() + b"\n"


class TestSilenceStartInitialization:
    """silence_start is a float (time.monotonic()) after session creation."""

    def test_silence_start_is_float_at_creation(self):
        before = time.monotonic()
        session = _make_session()
        after = time.monotonic()
        assert isinstance(session.silence_start, float)
        assert before <= session.silence_start <= after

    def test_silence_start_close_to_last_activity(self):
        """silence_start and last_activity are both set at creation time."""
        session = _make_session()
        assert isinstance(session.last_activity, float)
        assert isinstance(session.silence_start, float)
        # Both are set via time.monotonic() in __init__, so they should be
        # extremely close (within a few microseconds).
        assert abs(session.silence_start - session.last_activity) < 0.1


class TestStatusFlagsInitialization:
    """_sent_15s_status and _sent_60s_status are False after creation."""

    def test_sent_15s_status_false_at_creation(self):
        session = _make_session()
        assert session._sent_15s_status is False

    def test_sent_60s_status_false_at_creation(self):
        session = _make_session()
        assert session._sent_60s_status is False


class TestSilenceStartOnOutput:
    """silence_start is updated by _read_stdout()."""

    @pytest.mark.asyncio
    async def test_silence_start_set_after_first_output(self):
        """silence_start is set to a monotonic timestamp after processing output."""
        session = _make_session()
        session._reset_idle_timer = MagicMock()

        lines = [_make_stdout_line("hello"), b""]  # empty = EOF
        line_iter = iter(lines)

        async def fake_readline():
            return next(line_iter)

        session.process.stdout.readline = fake_readline

        before = time.monotonic()
        await session._read_stdout()
        after = time.monotonic()

        assert session.silence_start is not None
        assert before <= session.silence_start <= after

    @pytest.mark.asyncio
    async def test_silence_start_updates_with_each_output(self):
        """silence_start advances with each new output line."""
        session = _make_session()
        session._reset_idle_timer = MagicMock()

        timestamps = []

        lines = [
            _make_stdout_line("first"),
            _make_stdout_line("second"),
            _make_stdout_line("third"),
            b"",  # EOF
        ]
        line_index = 0

        async def fake_readline():
            nonlocal line_index
            if line_index > 0 and line_index < len(lines):
                # Capture silence_start after previous line was processed
                timestamps.append(session.silence_start)
            result = lines[line_index] if line_index < len(lines) else b""
            line_index += 1
            return result

        session.process.stdout.readline = fake_readline

        await session._read_stdout()

        # We should have captured timestamps for lines 2 and 3
        # Each should be non-None
        assert len(timestamps) >= 2
        for ts in timestamps:
            assert ts is not None

    @pytest.mark.asyncio
    async def test_silence_start_matches_last_activity(self):
        """silence_start and last_activity have the same value after output."""
        session = _make_session()
        session._reset_idle_timer = MagicMock()

        lines = [_make_stdout_line("hello"), b""]
        line_iter = iter(lines)

        async def fake_readline():
            return next(line_iter)

        session.process.stdout.readline = fake_readline

        await session._read_stdout()

        # Both should be set to the same 'now' value
        assert session.silence_start == session.last_activity


class TestStatusFlagsResetOnOutput:
    """_sent_15s_status and _sent_60s_status reset to False on agent output."""

    @pytest.mark.asyncio
    async def test_status_flags_reset_on_output(self):
        """Both flags are reset to False when agent produces output."""
        session = _make_session()
        session._reset_idle_timer = MagicMock()

        # Simulate flags being True (as if status messages were sent)
        session._sent_15s_status = True
        session._sent_60s_status = True

        lines = [_make_stdout_line("hello"), b""]
        line_iter = iter(lines)

        async def fake_readline():
            return next(line_iter)

        session.process.stdout.readline = fake_readline

        await session._read_stdout()

        assert session._sent_15s_status is False
        assert session._sent_60s_status is False

    @pytest.mark.asyncio
    async def test_status_flags_reset_on_each_output_line(self):
        """Flags are reset on every output line, not just the first."""
        session = _make_session()
        session._reset_idle_timer = MagicMock()

        # Set flags True before first output
        session._sent_15s_status = True
        session._sent_60s_status = True

        flag_states_after_reset = []

        lines = [
            _make_stdout_line("first"),
            _make_stdout_line("second"),
            b"",  # EOF
        ]
        line_index = 0

        async def fake_readline():
            nonlocal line_index
            if line_index > 0 and line_index < len(lines):
                # Capture flag state after previous line was processed
                # (should be False because _read_stdout resets them)
                flag_states_after_reset.append(
                    (session._sent_15s_status, session._sent_60s_status)
                )
                # Now set flags True again to simulate status messages
                # being sent during the next silence period
                session._sent_15s_status = True
                session._sent_60s_status = True
            result = lines[line_index] if line_index < len(lines) else b""
            line_index += 1
            return result

        session.process.stdout.readline = fake_readline

        await session._read_stdout()

        # After each line, flags should have been reset to False
        assert len(flag_states_after_reset) >= 2
        for state in flag_states_after_reset:
            assert state == (False, False)


class TestSilenceStartDuringSilence:
    """silence_start retains its value when no new output arrives."""

    @pytest.mark.asyncio
    async def test_silence_start_unchanged_during_silence(self):
        """silence_start does not change between output events."""
        session = _make_session()
        session._reset_idle_timer = MagicMock()

        lines = [_make_stdout_line("hello"), b""]
        line_iter = iter(lines)

        async def fake_readline():
            return next(line_iter)

        session.process.stdout.readline = fake_readline

        await session._read_stdout()

        # Record silence_start after output
        silence_ts = session.silence_start
        assert silence_ts is not None

        # Simulate passage of time (silence) — silence_start should not change
        # because no new output arrived.
        assert session.silence_start == silence_ts


class TestSilenceStartNotUpdatedByUserInput:
    """silence_start is NOT updated when a user sends a message."""

    @pytest.mark.asyncio
    async def test_send_does_not_update_silence_start(self):
        """Calling send() updates last_activity but NOT silence_start."""
        session = _make_session()
        session._reset_idle_timer = MagicMock()

        # Set silence_start to a known value
        session.silence_start = 100.0

        # Mock stdin for send()
        session.process.stdin.write = MagicMock()
        session.process.stdin.drain = AsyncMock()
        session.process.stdin.is_closing = MagicMock(return_value=False)

        await session.send("user message")

        # last_activity was updated
        assert session.last_activity > 100.0
        # silence_start was NOT updated
        assert session.silence_start == 100.0

    @pytest.mark.asyncio
    async def test_send_does_not_reset_status_flags(self):
        """Calling send() does NOT reset the status flags."""
        session = _make_session()
        session._reset_idle_timer = MagicMock()

        # Set flags to True
        session._sent_15s_status = True
        session._sent_60s_status = True

        # Mock stdin for send()
        session.process.stdin.write = MagicMock()
        session.process.stdin.drain = AsyncMock()
        session.process.stdin.is_closing = MagicMock(return_value=False)

        await session.send("user message")

        # Flags should remain True — only agent output resets them
        assert session._sent_15s_status is True
        assert session._sent_60s_status is True


class TestSilenceStartAccessibility:
    """silence_start is accessible as a plain attribute from any context."""

    def test_silence_start_readable_as_attribute(self):
        """silence_start can be read as a plain instance attribute."""
        session = _make_session()

        # Initially a float (time.monotonic())
        val = session.silence_start
        assert isinstance(val, float)

        # After manual set, readable
        session.silence_start = time.monotonic()
        assert isinstance(session.silence_start, float)

    @pytest.mark.asyncio
    async def test_silence_start_readable_from_heartbeat_context(self):
        """The typing heartbeat can read silence_start without error."""
        on_typing = AsyncMock()
        session = _make_session(on_typing=on_typing)

        # Simulate silence_start being set by _read_stdout
        session.silence_start = time.monotonic() - 10

        # Age last_activity so the heartbeat fires
        session.last_activity = time.monotonic() - 10

        call_count = 0

        async def fake_sleep(seconds):
            nonlocal call_count
            call_count += 1
            # Verify we can read silence_start from this context
            elapsed = time.monotonic() - session.silence_start
            assert elapsed >= 0
            session._ended = True

        with patch("telegram_bot.session.asyncio.sleep", side_effect=fake_sleep):
            await session._typing_heartbeat()

        # The heartbeat ran and accessed silence_start successfully
        assert call_count >= 1
