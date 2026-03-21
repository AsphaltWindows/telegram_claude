"""Tests for idle timer reset on agent stdout output in Session._read_stdout().

Verifies the fix for the bug where the idle timer was only reset on user input
(in send()) but not on agent output, causing sessions to be killed during
long-running agent operations.
"""

from __future__ import annotations

import asyncio
import time

import pytest
from mock import AsyncMock, MagicMock, patch

from telegram_bot.session import Session


def _make_session(
    idle_timeout: int = 600,
    chat_id: int = 42,
    agent_name: str = "operator",
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
    )
    return session


@pytest.mark.asyncio
async def test_read_stdout_resets_last_activity():
    """last_activity is updated when _read_stdout processes a non-empty line."""
    session = _make_session()

    # Simulate one JSON line then EOF.
    json_line = b'{"type":"assistant","message":{"content":"hello"}}\n'
    session.process.stdout.readline = AsyncMock(
        side_effect=[json_line, b""]
    )

    # Record the initial last_activity and artificially age it.
    session.last_activity = time.monotonic() - 100

    old_activity = session.last_activity

    # Stub _reset_idle_timer to avoid creating real tasks.
    session._reset_idle_timer = MagicMock()
    # Prevent _finish / shutdown from running on EOF.
    session._shutting_down = True

    await session._read_stdout()

    assert session.last_activity > old_activity, (
        "last_activity should be updated after receiving agent output"
    )


@pytest.mark.asyncio
async def test_read_stdout_calls_reset_idle_timer():
    """_reset_idle_timer() is called when _read_stdout processes a line."""
    session = _make_session()

    json_line = b'{"type":"assistant","message":{"content":"hi"}}\n'
    session.process.stdout.readline = AsyncMock(
        side_effect=[json_line, b""]
    )

    session._reset_idle_timer = MagicMock()
    session._shutting_down = True

    await session._read_stdout()

    session._reset_idle_timer.assert_called()


@pytest.mark.asyncio
async def test_read_stdout_resets_on_non_text_events():
    """Idle timer resets on non-text events (tool_use, system) too."""
    session = _make_session()

    # A tool_use event produces no text for on_response, but should still
    # reset the idle timer because the agent is actively working.
    tool_line = b'{"type":"tool_use","name":"Read","input":{}}\n'
    session.process.stdout.readline = AsyncMock(
        side_effect=[tool_line, b""]
    )

    session.last_activity = time.monotonic() - 100
    old_activity = session.last_activity

    session._reset_idle_timer = MagicMock()
    session._shutting_down = True

    await session._read_stdout()

    assert session.last_activity > old_activity
    session._reset_idle_timer.assert_called()


@pytest.mark.asyncio
async def test_read_stdout_resets_before_on_response_callback():
    """last_activity is updated before the on_response callback is invoked.

    Even if on_response raises, the timestamp should already be updated.
    """
    session = _make_session()

    import json
    json_line = json.dumps({
        "type": "result",
        "result": "hey",
    }).encode() + b"\n"
    session.process.stdout.readline = AsyncMock(
        side_effect=[json_line, b""]
    )

    callback_activity_time = None

    async def capturing_callback(chat_id, text):
        nonlocal callback_activity_time
        callback_activity_time = session.last_activity

    session._on_response = capturing_callback
    session.last_activity = time.monotonic() - 100
    old_activity = session.last_activity

    session._reset_idle_timer = MagicMock()
    session._shutting_down = True

    await session._read_stdout()

    assert callback_activity_time is not None
    assert callback_activity_time > old_activity, (
        "last_activity should be updated before on_response is called"
    )


@pytest.mark.asyncio
async def test_read_stdout_resets_on_each_line():
    """Idle timer is reset for every non-empty line, not just the first."""
    session = _make_session()

    lines = [
        b'{"type":"assistant","message":{"content":"line1"}}\n',
        b'{"type":"assistant","message":{"content":"line2"}}\n',
        b'{"type":"assistant","message":{"content":"line3"}}\n',
        b"",
    ]
    session.process.stdout.readline = AsyncMock(side_effect=lines)

    session._reset_idle_timer = MagicMock()
    session._shutting_down = True

    await session._read_stdout()

    assert session._reset_idle_timer.call_count == 3, (
        "_reset_idle_timer should be called once per non-empty line"
    )


@pytest.mark.asyncio
async def test_empty_lines_do_not_reset_timer():
    """Blank lines (after stripping) should not reset the idle timer."""
    session = _make_session()

    lines = [
        b"\n",  # empty after rstrip
        b'{"type":"assistant","message":{"content":"hi"}}\n',
        b"",
    ]
    session.process.stdout.readline = AsyncMock(side_effect=lines)

    session._reset_idle_timer = MagicMock()
    session._shutting_down = True

    await session._read_stdout()

    # Only the JSON line should trigger a reset, not the blank line.
    assert session._reset_idle_timer.call_count == 1
