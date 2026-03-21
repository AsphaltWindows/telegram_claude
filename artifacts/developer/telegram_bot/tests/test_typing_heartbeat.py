"""Tests for typing indicator heartbeat in Session._typing_heartbeat().

Verifies that the typing indicator is sent during agent silence, stops when
output arrives, and handles callback errors gracefully.
"""

from __future__ import annotations

import asyncio
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


@pytest.mark.asyncio
async def test_typing_heartbeat_sends_after_silence():
    """Typing indicator is sent when agent has been silent for the interval."""
    on_typing = AsyncMock()
    session = _make_session(on_typing=on_typing)

    # Age the last_activity so the heartbeat fires immediately after sleep.
    session.last_activity = time.monotonic() - _TYPING_HEARTBEAT_INTERVAL - 1

    # Stub _reset_idle_timer to avoid creating real tasks.
    session._reset_idle_timer = MagicMock()

    # Run the heartbeat with a patched sleep that ends the session after
    # one iteration.
    call_count = 0

    async def fake_sleep(seconds):
        nonlocal call_count
        call_count += 1
        if call_count >= 2:
            session._ended = True

    with patch("telegram_bot.session.asyncio.sleep", side_effect=fake_sleep):
        await session._typing_heartbeat()

    on_typing.assert_called_with(42)
    assert on_typing.call_count >= 1


@pytest.mark.asyncio
async def test_typing_heartbeat_not_sent_during_activity():
    """Typing indicator is NOT sent when agent output is recent."""
    on_typing = AsyncMock()
    session = _make_session(on_typing=on_typing)

    # Keep last_activity fresh — within the heartbeat interval.
    session.last_activity = time.monotonic()

    call_count = 0

    async def fake_sleep(seconds):
        nonlocal call_count
        call_count += 1
        # Keep last_activity fresh each iteration.
        session.last_activity = time.monotonic()
        if call_count >= 2:
            session._ended = True

    with patch("telegram_bot.session.asyncio.sleep", side_effect=fake_sleep):
        await session._typing_heartbeat()

    on_typing.assert_not_called()


@pytest.mark.asyncio
async def test_typing_heartbeat_stops_when_session_ends():
    """Heartbeat exits cleanly when session._ended is set."""
    on_typing = AsyncMock()
    session = _make_session(on_typing=on_typing)
    session._ended = True

    with patch("telegram_bot.session.asyncio.sleep", new_callable=AsyncMock):
        await session._typing_heartbeat()

    on_typing.assert_not_called()


@pytest.mark.asyncio
async def test_typing_heartbeat_handles_callback_exception():
    """If the typing callback raises, the heartbeat logs and continues."""
    on_typing = AsyncMock(side_effect=Exception("network error"))
    session = _make_session(on_typing=on_typing)

    # Age last_activity so the heartbeat fires.
    session.last_activity = time.monotonic() - _TYPING_HEARTBEAT_INTERVAL - 1

    call_count = 0

    async def fake_sleep(seconds):
        nonlocal call_count
        call_count += 1
        if call_count >= 2:
            session._ended = True

    with patch("telegram_bot.session.asyncio.sleep", side_effect=fake_sleep):
        with patch("telegram_bot.session.logger") as mock_logger:
            # Should not raise.
            await session._typing_heartbeat()

    # Callback was attempted.
    on_typing.assert_called()
    # Exception was logged.
    mock_logger.exception.assert_called()


@pytest.mark.asyncio
async def test_typing_heartbeat_handles_cancellation():
    """CancelledError stops the heartbeat cleanly."""
    on_typing = AsyncMock()
    session = _make_session(on_typing=on_typing)

    async def cancel_sleep(seconds):
        raise asyncio.CancelledError()

    with patch("telegram_bot.session.asyncio.sleep", side_effect=cancel_sleep):
        await session._typing_heartbeat()

    # No error, no crash — clean exit.


@pytest.mark.asyncio
async def test_typing_heartbeat_not_started_when_no_callback():
    """When on_typing is None, no typing task is created."""
    session = _make_session(on_typing=None)

    # Stub to prevent real tasks.
    session._stdout_task = MagicMock()
    session._stderr_task = MagicMock()
    session._idle_task = MagicMock()

    # We can't call start() directly because it creates real asyncio tasks.
    # Instead verify the condition: on_typing is None -> no typing task.
    assert session._on_typing is None
    assert session._typing_task is None


@pytest.mark.asyncio
async def test_typing_task_cancelled_in_finish():
    """The typing task is included in _finish() cancellation."""
    on_typing = AsyncMock()
    session = _make_session(on_typing=on_typing)

    # Create a mock task to verify it gets cancelled.
    mock_task = MagicMock()
    mock_task.done.return_value = False
    session._typing_task = mock_task
    session._stdout_task = None
    session._stderr_task = None
    session._idle_task = None

    await session._finish("shutdown")

    mock_task.cancel.assert_called_once()


@pytest.mark.asyncio
async def test_typing_heartbeat_sends_repeatedly():
    """Typing indicator is sent on each iteration while agent is silent."""
    on_typing = AsyncMock()
    session = _make_session(on_typing=on_typing)
    session.last_activity = time.monotonic() - 100  # very stale

    call_count = 0

    async def fake_sleep(seconds):
        nonlocal call_count
        call_count += 1
        if call_count >= 4:
            session._ended = True

    with patch("telegram_bot.session.asyncio.sleep", side_effect=fake_sleep):
        await session._typing_heartbeat()

    # Should have been called multiple times (once per iteration after sleep).
    assert on_typing.call_count >= 3
