"""Tests for progress status messages in Session._typing_heartbeat().

Verifies that the 15s and 60s status messages are sent at the correct silence
thresholds, are sent only once per silence period, reset properly when agent
output arrives, and handle errors gracefully.
"""

from __future__ import annotations

import asyncio
import time

import pytest
from mock import AsyncMock, MagicMock, patch

from telegram_bot.session import (
    Session,
    _PROGRESS_15S_THRESHOLD,
    _PROGRESS_60S_THRESHOLD,
    _TYPING_HEARTBEAT_INTERVAL,
)


def _make_session(
    idle_timeout: int = 600,
    chat_id: int = 42,
    agent_name: str = "operator",
    on_typing: AsyncMock | None = None,
    on_response: AsyncMock | None = None,
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
        on_response=on_response or AsyncMock(),
        on_end=AsyncMock(),
        idle_timeout=idle_timeout,
        shutdown_message="/exit",
        cleanup=MagicMock(),
        on_typing=on_typing or AsyncMock(),
    )
    return session


def _run_heartbeat_iterations(session, num_iterations):
    """Return a fake_sleep function that ends the session after N iterations."""
    call_count = 0

    async def fake_sleep(seconds):
        nonlocal call_count
        call_count += 1
        if call_count >= num_iterations:
            session._ended = True

    return fake_sleep


# -------------------------------------------------------------------
# 15-second status message
# -------------------------------------------------------------------


@pytest.mark.asyncio
async def test_15s_status_sent_after_threshold():
    """The 15s status message is sent when silence exceeds the threshold."""
    on_response = AsyncMock()
    session = _make_session(on_response=on_response)

    # Set silence_start to be past the 15s threshold
    session.silence_start = time.monotonic() - _PROGRESS_15S_THRESHOLD - 1
    session.last_activity = time.monotonic() - _PROGRESS_15S_THRESHOLD - 1

    fake_sleep = _run_heartbeat_iterations(session, 2)

    with patch("telegram_bot.session.asyncio.sleep", side_effect=fake_sleep):
        await session._typing_heartbeat()

    # The 15s status message should have been sent
    on_response.assert_any_call(42, "\u23f3 Still working...")


@pytest.mark.asyncio
async def test_15s_status_not_sent_before_threshold():
    """No status message is sent when silence is under 15 seconds."""
    on_response = AsyncMock()
    session = _make_session(on_response=on_response)

    # Set silence_start to be well under the threshold
    session.silence_start = time.monotonic()
    session.last_activity = time.monotonic()

    fake_sleep = _run_heartbeat_iterations(session, 2)

    with patch("telegram_bot.session.asyncio.sleep", side_effect=fake_sleep):
        await session._typing_heartbeat()

    # on_response should NOT have been called for status messages
    on_response.assert_not_called()


@pytest.mark.asyncio
async def test_15s_status_sent_only_once():
    """The 15s status message is sent exactly once, even over multiple iterations."""
    on_response = AsyncMock()
    session = _make_session(on_response=on_response)

    # Silence well past 15s
    session.silence_start = time.monotonic() - _PROGRESS_15S_THRESHOLD - 10
    session.last_activity = time.monotonic() - _PROGRESS_15S_THRESHOLD - 10

    # Run several iterations — but keep silence_elapsed under 60s
    # so we only test the 15s message
    session.silence_start = time.monotonic() - 20  # 20s of silence

    fake_sleep = _run_heartbeat_iterations(session, 4)

    with patch("telegram_bot.session.asyncio.sleep", side_effect=fake_sleep):
        await session._typing_heartbeat()

    # Count calls with the 15s message
    calls_15s = [
        c for c in on_response.call_args_list
        if c == ((42, "\u23f3 Still working..."),)
    ]
    assert len(calls_15s) == 1


# -------------------------------------------------------------------
# 60-second status message
# -------------------------------------------------------------------


@pytest.mark.asyncio
async def test_60s_status_sent_after_threshold():
    """The 60s status message is sent when silence exceeds 60 seconds."""
    on_response = AsyncMock()
    session = _make_session(on_response=on_response)

    # Set silence_start to be past the 60s threshold
    session.silence_start = time.monotonic() - _PROGRESS_60S_THRESHOLD - 1
    session.last_activity = time.monotonic() - _PROGRESS_60S_THRESHOLD - 1

    fake_sleep = _run_heartbeat_iterations(session, 2)

    with patch("telegram_bot.session.asyncio.sleep", side_effect=fake_sleep):
        await session._typing_heartbeat()

    # Both 15s and 60s should have been sent
    on_response.assert_any_call(42, "\u23f3 Still working...")
    on_response.assert_any_call(
        42, "\u23f3 This is taking a while \u2014 still processing your request."
    )


@pytest.mark.asyncio
async def test_60s_status_not_sent_before_threshold():
    """The 60s message is NOT sent if silence is between 15s and 60s."""
    on_response = AsyncMock()
    session = _make_session(on_response=on_response)

    # 30 seconds of silence — past 15s but not 60s
    session.silence_start = time.monotonic() - 30
    session.last_activity = time.monotonic() - 30

    fake_sleep = _run_heartbeat_iterations(session, 2)

    with patch("telegram_bot.session.asyncio.sleep", side_effect=fake_sleep):
        await session._typing_heartbeat()

    # 15s message should be sent, but NOT the 60s message
    on_response.assert_any_call(42, "\u23f3 Still working...")
    calls_60s = [
        c for c in on_response.call_args_list
        if c == ((42, "\u23f3 This is taking a while \u2014 still processing your request."),)
    ]
    assert len(calls_60s) == 0


@pytest.mark.asyncio
async def test_60s_status_sent_only_once():
    """The 60s status message is sent exactly once."""
    on_response = AsyncMock()
    session = _make_session(on_response=on_response)

    # Well past 60s
    session.silence_start = time.monotonic() - 120
    session.last_activity = time.monotonic() - 120

    fake_sleep = _run_heartbeat_iterations(session, 4)

    with patch("telegram_bot.session.asyncio.sleep", side_effect=fake_sleep):
        await session._typing_heartbeat()

    # Count 60s message calls
    calls_60s = [
        c for c in on_response.call_args_list
        if c == ((42, "\u23f3 This is taking a while \u2014 still processing your request."),)
    ]
    assert len(calls_60s) == 1


@pytest.mark.asyncio
async def test_no_additional_messages_after_60s():
    """No status messages beyond the 60s message, even after long silence."""
    on_response = AsyncMock()
    session = _make_session(on_response=on_response)

    # 300 seconds of silence
    session.silence_start = time.monotonic() - 300
    session.last_activity = time.monotonic() - 300

    fake_sleep = _run_heartbeat_iterations(session, 5)

    with patch("telegram_bot.session.asyncio.sleep", side_effect=fake_sleep):
        await session._typing_heartbeat()

    # Exactly 2 status messages total: the 15s and 60s
    assert on_response.call_count == 2


# -------------------------------------------------------------------
# Reset behavior
# -------------------------------------------------------------------


@pytest.mark.asyncio
async def test_status_messages_fire_again_after_reset():
    """After flags are reset (simulating agent output), messages fire again."""
    on_response = AsyncMock()
    session = _make_session(on_response=on_response)

    # Start with 20s of silence — 15s message should fire
    session.silence_start = time.monotonic() - 20
    session.last_activity = time.monotonic() - 20

    call_count = 0

    async def fake_sleep(seconds):
        nonlocal call_count
        call_count += 1
        if call_count == 2:
            # Simulate agent output resetting flags and silence_start
            session.silence_start = time.monotonic() - 20  # new silence period, already at 20s
            session._sent_15s_status = False
            session._sent_60s_status = False
        elif call_count >= 4:
            session._ended = True

    with patch("telegram_bot.session.asyncio.sleep", side_effect=fake_sleep):
        await session._typing_heartbeat()

    # 15s message should have been sent twice (once per silence period)
    calls_15s = [
        c for c in on_response.call_args_list
        if c == ((42, "\u23f3 Still working..."),)
    ]
    assert len(calls_15s) == 2


# -------------------------------------------------------------------
# Error handling
# -------------------------------------------------------------------


@pytest.mark.asyncio
async def test_15s_status_send_failure_logged_and_swallowed():
    """If sending the 15s status message fails, the error is logged and the session continues."""
    on_response = AsyncMock(side_effect=Exception("Telegram API error"))
    on_typing = AsyncMock()  # typing should still work
    session = _make_session(on_response=on_response, on_typing=on_typing)

    session.silence_start = time.monotonic() - _PROGRESS_15S_THRESHOLD - 1
    session.last_activity = time.monotonic() - _PROGRESS_15S_THRESHOLD - 1

    fake_sleep = _run_heartbeat_iterations(session, 2)

    with patch("telegram_bot.session.asyncio.sleep", side_effect=fake_sleep):
        with patch("telegram_bot.session.logger") as mock_logger:
            # Should NOT raise
            await session._typing_heartbeat()

    # The attempt was made
    on_response.assert_called()
    # Error was logged
    mock_logger.exception.assert_called()
    # The flag is still set (so it won't retry)
    assert session._sent_15s_status is True


@pytest.mark.asyncio
async def test_60s_status_send_failure_logged_and_swallowed():
    """If sending the 60s status message fails, the error is logged and the session continues."""
    call_count = 0

    async def selective_fail(chat_id, text):
        nonlocal call_count
        call_count += 1
        if "\u2014" in text:  # 60s message contains em dash
            raise Exception("Telegram API error")

    on_response = AsyncMock(side_effect=selective_fail)
    session = _make_session(on_response=on_response)

    session.silence_start = time.monotonic() - _PROGRESS_60S_THRESHOLD - 1
    session.last_activity = time.monotonic() - _PROGRESS_60S_THRESHOLD - 1

    fake_sleep = _run_heartbeat_iterations(session, 2)

    with patch("telegram_bot.session.asyncio.sleep", side_effect=fake_sleep):
        with patch("telegram_bot.session.logger") as mock_logger:
            await session._typing_heartbeat()

    mock_logger.exception.assert_called()
    assert session._sent_60s_status is True


# -------------------------------------------------------------------
# Typing indicator independence
# -------------------------------------------------------------------


@pytest.mark.asyncio
async def test_typing_indicator_continues_alongside_status_messages():
    """Typing indicator fires even when status messages are also being sent."""
    on_typing = AsyncMock()
    on_response = AsyncMock()
    session = _make_session(on_typing=on_typing, on_response=on_response)

    # Silence well past both thresholds
    session.silence_start = time.monotonic() - 100
    session.last_activity = time.monotonic() - 100

    fake_sleep = _run_heartbeat_iterations(session, 3)

    with patch("telegram_bot.session.asyncio.sleep", side_effect=fake_sleep):
        await session._typing_heartbeat()

    # Typing indicator should have been called
    assert on_typing.call_count >= 2
    # Status messages should also have been sent
    assert on_response.call_count >= 1


# -------------------------------------------------------------------
# Constants
# -------------------------------------------------------------------


def test_threshold_constants():
    """Threshold constants have the expected values."""
    assert _PROGRESS_15S_THRESHOLD == 15
    assert _PROGRESS_60S_THRESHOLD == 60


def test_15s_threshold_less_than_60s():
    """15s threshold is strictly less than 60s threshold."""
    assert _PROGRESS_15S_THRESHOLD < _PROGRESS_60S_THRESHOLD


# -------------------------------------------------------------------
# Edge case: silence_start is None
# -------------------------------------------------------------------


@pytest.mark.asyncio
async def test_no_status_when_silence_start_is_none():
    """If silence_start is None for any reason, no status messages are sent."""
    on_response = AsyncMock()
    session = _make_session(on_response=on_response)

    session.silence_start = None  # type: ignore[assignment]
    session.last_activity = time.monotonic() - 100

    fake_sleep = _run_heartbeat_iterations(session, 2)

    with patch("telegram_bot.session.asyncio.sleep", side_effect=fake_sleep):
        await session._typing_heartbeat()

    on_response.assert_not_called()
