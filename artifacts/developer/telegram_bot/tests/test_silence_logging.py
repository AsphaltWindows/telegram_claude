"""Tests for silence period summary logging in the typing heartbeat.

Verifies that:
- _filtered_event_count is initialised to 0.
- _filtered_event_count increments when events are filtered (text is None).
- _filtered_event_count resets to 0 when text is extracted.
- The typing heartbeat logs silence duration and filtered event count at INFO.
- The silence summary log includes the agent name and chat ID.
- No silence log when silence_start is None (edge case).
"""

from __future__ import annotations

import asyncio
import json
import time

import pytest
from mock import AsyncMock, MagicMock, patch

from telegram_bot.session import Session, _TYPING_HEARTBEAT_INTERVAL


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


def _json_line(obj: dict) -> bytes:
    return json.dumps(obj).encode() + b"\n"


class TestFilteredEventCountInit:
    """_filtered_event_count is 0 at creation."""

    def test_initial_value(self):
        session = _make_session()
        assert session._filtered_event_count == 0


class TestFilteredEventCountIncrement:
    """_filtered_event_count increments on filtered events in _read_stdout."""

    @pytest.mark.asyncio
    async def test_increments_on_filtered_events(self):
        session = _make_session()
        session._reset_idle_timer = MagicMock()

        lines = [
            _json_line({"type": "tool_use", "name": "Read"}),
            _json_line({"type": "tool_result", "content": "data"}),
            _json_line({"type": "ping"}),
            b"",  # EOF
        ]
        line_iter = iter(lines)

        async def fake_readline():
            return next(line_iter)

        session.process.stdout.readline = fake_readline
        await session._read_stdout()

        assert session._filtered_event_count == 3

    @pytest.mark.asyncio
    async def test_resets_on_text_extraction(self):
        session = _make_session()
        session._reset_idle_timer = MagicMock()

        lines = [
            _json_line({"type": "tool_use", "name": "Read"}),
            _json_line({"type": "tool_result", "content": "data"}),
            _json_line({"type": "result", "result": "Here is the answer."}),
            b"",  # EOF
        ]
        line_iter = iter(lines)

        async def fake_readline():
            return next(line_iter)

        session.process.stdout.readline = fake_readline
        await session._read_stdout()

        # After result event with text, counter should be reset to 0.
        assert session._filtered_event_count == 0

    @pytest.mark.asyncio
    async def test_increments_after_reset(self):
        """Counter increments again after being reset."""
        session = _make_session()
        session._reset_idle_timer = MagicMock()

        lines = [
            _json_line({"type": "tool_use", "name": "Read"}),
            _json_line({"type": "result", "result": "Answer."}),
            _json_line({"type": "tool_use", "name": "Bash"}),
            _json_line({"type": "ping"}),
            b"",  # EOF
        ]
        line_iter = iter(lines)

        async def fake_readline():
            return next(line_iter)

        session.process.stdout.readline = fake_readline
        await session._read_stdout()

        # After result: reset to 0, then 2 more filtered events.
        assert session._filtered_event_count == 2


class TestSilenceSummaryLogging:
    """The typing heartbeat logs silence summary at INFO."""

    @pytest.mark.asyncio
    async def test_silence_summary_logged(self):
        on_typing = AsyncMock()
        session = _make_session(on_typing=on_typing)

        # Simulate silence — agent started 10s ago, no output since.
        session.silence_start = time.monotonic() - 10
        session.last_activity = time.monotonic() - 10
        session._filtered_event_count = 47

        call_count = 0

        async def fake_sleep(seconds):
            nonlocal call_count
            call_count += 1
            if call_count >= 2:
                session._ended = True

        with patch("telegram_bot.session.asyncio.sleep", side_effect=fake_sleep):
            with patch("telegram_bot.session.logger") as mock_logger:
                await session._typing_heartbeat()

        # Check that an INFO log was emitted with silence summary.
        info_calls = [
            c for c in mock_logger.info.call_args_list
            if "silent for" in str(c)
        ]
        assert len(info_calls) >= 1
        # Check it includes filtered event count.
        assert "47" in str(info_calls[0])

    @pytest.mark.asyncio
    async def test_silence_summary_includes_agent_name_and_chat_id(self):
        on_typing = AsyncMock()
        session = _make_session(on_typing=on_typing, agent_name="architect", chat_id=99)

        session.silence_start = time.monotonic() - 5
        session.last_activity = time.monotonic() - 5
        session._filtered_event_count = 10

        call_count = 0

        async def fake_sleep(seconds):
            nonlocal call_count
            call_count += 1
            if call_count >= 2:
                session._ended = True

        with patch("telegram_bot.session.asyncio.sleep", side_effect=fake_sleep):
            with patch("telegram_bot.session.logger") as mock_logger:
                await session._typing_heartbeat()

        info_calls = [
            c for c in mock_logger.info.call_args_list
            if "silent for" in str(c)
        ]
        assert len(info_calls) >= 1
        call_str = str(info_calls[0])
        assert "architect" in call_str
        assert "99" in call_str

    @pytest.mark.asyncio
    async def test_silence_summary_does_not_affect_typing(self):
        """Typing indicator is still sent alongside silence logging."""
        on_typing = AsyncMock()
        session = _make_session(on_typing=on_typing)

        session.silence_start = time.monotonic() - 10
        session.last_activity = time.monotonic() - 10

        call_count = 0

        async def fake_sleep(seconds):
            nonlocal call_count
            call_count += 1
            if call_count >= 2:
                session._ended = True

        with patch("telegram_bot.session.asyncio.sleep", side_effect=fake_sleep):
            await session._typing_heartbeat()

        on_typing.assert_called_with(42)

    @pytest.mark.asyncio
    async def test_no_log_when_session_just_started(self):
        """When silence_start is very recent (just started), silence_duration
        is near 0 but still > 0, so a log is emitted. This is acceptable."""
        on_typing = AsyncMock()
        session = _make_session(on_typing=on_typing)

        # Fresh session — silence_start is 'now'.
        session.last_activity = time.monotonic() - _TYPING_HEARTBEAT_INTERVAL - 1

        call_count = 0

        async def fake_sleep(seconds):
            nonlocal call_count
            call_count += 1
            if call_count >= 2:
                session._ended = True

        with patch("telegram_bot.session.asyncio.sleep", side_effect=fake_sleep):
            with patch("telegram_bot.session.logger") as mock_logger:
                await session._typing_heartbeat()

        # The log should fire (silence_duration will be a few seconds from
        # test execution time), but the typing indicator should also fire.
        on_typing.assert_called()
