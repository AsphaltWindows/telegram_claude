"""Tests for result event handling and post-tool-use text delivery.

Verifies that:
- ``_extract_text_from_result`` handles all known result event shapes.
- ``_extract_text_from_event`` no longer skips result events.
- ``_deduplicate_result_text`` correctly deduplicates against already-delivered
  text and passes through new post-tool-use content.
- ``_read_stdout`` delivers post-tool-use text from result events while
  avoiding duplicates for simple (non-tool-use) responses.
"""

from __future__ import annotations

import asyncio
import json

import pytest
from mock import AsyncMock, MagicMock

from telegram_bot.session import (
    Session,
    _deduplicate_result_text,
    _extract_text_from_event,
    _extract_text_from_result,
)


# -----------------------------------------------------------------------
# Helpers
# -----------------------------------------------------------------------

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
        on_typing=None,
    )
    return session


def _json_line(obj: dict) -> bytes:
    """Encode a dict as a newline-terminated JSON bytes line."""
    return json.dumps(obj).encode() + b"\n"


def _assistant_delta(text: str) -> bytes:
    """Create a content_block_delta event line."""
    return _json_line({
        "type": "content_block_delta",
        "delta": {"type": "text_delta", "text": text},
    })


def _result_event_string(text: str) -> bytes:
    """Create a result event where result is a plain string."""
    return _json_line({"type": "result", "result": text})


def _result_event_content_blocks(text: str) -> bytes:
    """Create a result event where result has content blocks."""
    return _json_line({
        "type": "result",
        "result": {
            "content": [{"type": "text", "text": text}],
        },
    })


def _result_event_message(text: str) -> bytes:
    """Create a result event with a top-level message field."""
    return _json_line({
        "type": "result",
        "message": {
            "content": [{"type": "text", "text": text}],
        },
    })


# -----------------------------------------------------------------------
# _extract_text_from_result
# -----------------------------------------------------------------------

class TestExtractTextFromResult:
    """Unit tests for _extract_text_from_result."""

    def test_result_plain_string(self):
        event = {"type": "result", "result": "Hello, world!"}
        assert _extract_text_from_result(event) == "Hello, world!"

    def test_result_content_blocks(self):
        event = {
            "type": "result",
            "result": {
                "content": [{"type": "text", "text": "Found it."}],
            },
        }
        assert _extract_text_from_result(event) == "Found it."

    def test_result_message_content(self):
        event = {
            "type": "result",
            "message": {
                "content": [{"type": "text", "text": "Analysis complete."}],
            },
        }
        assert _extract_text_from_result(event) == "Analysis complete."

    def test_result_nested_message(self):
        event = {
            "type": "result",
            "result": {
                "message": {
                    "content": [{"type": "text", "text": "Nested text."}],
                },
            },
        }
        assert _extract_text_from_result(event) == "Nested text."

    def test_result_empty_string(self):
        event = {"type": "result", "result": "   "}
        assert _extract_text_from_result(event) is None

    def test_result_no_text(self):
        event = {"type": "result", "result": {"content": []}}
        assert _extract_text_from_result(event) is None

    def test_result_no_result_field(self):
        event = {"type": "result", "session_id": "abc123"}
        assert _extract_text_from_result(event) is None

    def test_result_multiple_text_blocks(self):
        event = {
            "type": "result",
            "result": {
                "content": [
                    {"type": "text", "text": "Part 1. "},
                    {"type": "tool_use", "name": "read"},
                    {"type": "text", "text": "Part 2."},
                ],
            },
        }
        assert _extract_text_from_result(event) == "Part 1. Part 2."


# -----------------------------------------------------------------------
# _extract_text_from_event — result events are no longer skipped
# -----------------------------------------------------------------------

class TestExtractTextFromEventResult:
    """Verify that _extract_text_from_event handles result events."""

    def test_result_event_returns_text(self):
        raw = json.dumps({"type": "result", "result": "The answer is 42."})
        assert _extract_text_from_event(raw) == "The answer is 42."

    def test_result_event_with_content_blocks(self):
        raw = json.dumps({
            "type": "result",
            "result": {
                "content": [{"type": "text", "text": "Hello from result."}],
            },
        })
        assert _extract_text_from_event(raw) == "Hello from result."

    def test_result_event_no_text_returns_none(self):
        raw = json.dumps({"type": "result", "result": {"content": []}})
        assert _extract_text_from_event(raw) is None

    def test_non_result_events_still_skipped(self):
        """Events like tool_use and system should still return None."""
        for event_type in ("tool_use", "tool_result", "system", "ping"):
            raw = json.dumps({"type": event_type})
            assert _extract_text_from_event(raw) is None

    def test_assistant_event_now_skipped(self):
        """assistant events are now skipped — text comes only from result."""
        raw = json.dumps({
            "type": "assistant",
            "message": {"content": [{"type": "text", "text": "Hi!"}]},
        })
        assert _extract_text_from_event(raw) is None

    def test_content_block_delta_now_skipped(self):
        """content_block_delta events are now skipped — text comes only from result."""
        raw = json.dumps({
            "type": "content_block_delta",
            "delta": {"type": "text_delta", "text": "chunk"},
        })
        assert _extract_text_from_event(raw) is None


# -----------------------------------------------------------------------
# _deduplicate_result_text
# -----------------------------------------------------------------------

class TestDeduplicateResultText:
    """Unit tests for _deduplicate_result_text."""

    def test_no_prior_delivery_returns_full_text(self):
        assert _deduplicate_result_text("", "Full response.") == "Full response."

    def test_exact_duplicate_returns_none(self):
        assert _deduplicate_result_text("Hello!", "Hello!") is None

    def test_duplicate_with_whitespace_returns_none(self):
        assert _deduplicate_result_text("Hello! ", " Hello! ") is None

    def test_result_extends_delivered_text(self):
        delivered = "Let me look at some files."
        result = "Let me look at some files. Based on what I found, the answer is 42."
        new = _deduplicate_result_text(delivered, result)
        assert new == "Based on what I found, the answer is 42."

    def test_completely_different_text_returns_full(self):
        delivered = "Thinking..."
        result = "Here is the complete analysis of the codebase."
        new = _deduplicate_result_text(delivered, result)
        assert new == result

    def test_empty_result_returns_none(self):
        assert _deduplicate_result_text("something", "") is None

    def test_whitespace_only_result_returns_none(self):
        assert _deduplicate_result_text("something", "   ") is None

    def test_none_delivered_empty_string(self):
        """When nothing was delivered, full result text is returned."""
        assert _deduplicate_result_text("", "New text here.") == "New text here."


# -----------------------------------------------------------------------
# _read_stdout integration — tool-use scenario
# -----------------------------------------------------------------------

class TestReadStdoutToolUse:
    """Integration tests for _read_stdout with tool-use result events."""

    @pytest.mark.asyncio
    async def test_tool_use_delivers_result_text(self):
        """Text is extracted from the result event only — deltas are skipped.
        The full result text is delivered in a single call."""
        session = _make_session()
        session._reset_idle_timer = MagicMock()

        full_result_text = "Let me look at some files. Based on my analysis, the answer is 42."

        lines = [
            _assistant_delta("Let me look at some files."),  # skipped
            _json_line({"type": "tool_use", "name": "read_file"}),
            _json_line({"type": "tool_result", "content": "file contents"}),
            _result_event_string(full_result_text),
            b"",  # EOF
        ]
        line_iter = iter(lines)

        async def fake_readline():
            return next(line_iter)

        session.process.stdout.readline = fake_readline
        await session._read_stdout()

        calls = session._on_response.call_args_list
        # Only one call — from the result event (deltas are now skipped).
        assert len(calls) == 1
        assert calls[0].args == (42, full_result_text)

    @pytest.mark.asyncio
    async def test_simple_response_delivered_from_result(self):
        """For a simple response, text is delivered from the result event
        (delta events are skipped)."""
        session = _make_session()
        session._reset_idle_timer = MagicMock()

        text = "The answer is 42."
        lines = [
            _assistant_delta(text),  # skipped
            _result_event_string(text),
            b"",  # EOF
        ]
        line_iter = iter(lines)

        async def fake_readline():
            return next(line_iter)

        session.process.stdout.readline = fake_readline
        await session._read_stdout()

        calls = session._on_response.call_args_list
        # Only one call — from the result event.
        assert len(calls) == 1
        assert calls[0].args == (42, text)

    @pytest.mark.asyncio
    async def test_result_only_no_deltas(self):
        """When no deltas are emitted and the result carries all text,
        the full result text is delivered."""
        session = _make_session()
        session._reset_idle_timer = MagicMock()

        text = "Here is the full analysis."
        lines = [
            _result_event_string(text),
            b"",  # EOF
        ]
        line_iter = iter(lines)

        async def fake_readline():
            return next(line_iter)

        session.process.stdout.readline = fake_readline
        await session._read_stdout()

        calls = session._on_response.call_args_list
        assert len(calls) == 1
        assert calls[0].args == (42, text)

    @pytest.mark.asyncio
    async def test_result_event_resets_buffer_for_next_turn(self):
        """After a result event, the turn buffer is cleared so a second
        turn starts fresh."""
        session = _make_session()
        session._reset_idle_timer = MagicMock()

        lines = [
            _result_event_string("Turn 1 text."),
            # Second turn
            _result_event_string("Turn 2 text."),
            b"",  # EOF
        ]
        line_iter = iter(lines)

        async def fake_readline():
            return next(line_iter)

        session.process.stdout.readline = fake_readline
        await session._read_stdout()

        calls = session._on_response.call_args_list
        # Two result deliveries — one per turn.
        assert len(calls) == 2
        assert calls[0].args == (42, "Turn 1 text.")
        assert calls[1].args == (42, "Turn 2 text.")

    @pytest.mark.asyncio
    async def test_result_no_text_resets_buffer(self):
        """A result event with no text still resets the turn buffer."""
        session = _make_session()
        session._reset_idle_timer = MagicMock()

        lines = [
            _json_line({"type": "result", "result": {"content": []}}),
            b"",  # EOF
        ]
        line_iter = iter(lines)

        async def fake_readline():
            return next(line_iter)

        session.process.stdout.readline = fake_readline
        await session._read_stdout()

        # No text in result — no delivery.
        calls = session._on_response.call_args_list
        assert len(calls) == 0
        # Buffer was reset.
        assert session._turn_delivered_text == ""

    @pytest.mark.asyncio
    async def test_turn_delivered_text_initialized_empty(self):
        """A new session starts with an empty turn buffer."""
        session = _make_session()
        assert session._turn_delivered_text == ""

    @pytest.mark.asyncio
    async def test_multi_tool_use_chain(self):
        """Multiple tool uses in a single turn — full text delivered from result."""
        session = _make_session()
        session._reset_idle_timer = MagicMock()

        full_text = (
            "Let me check both files. "
            "File A contains X and File B contains Y."
        )

        lines = [
            _assistant_delta("Let me check both files."),  # skipped
            _json_line({"type": "tool_use", "name": "read_file"}),
            _json_line({"type": "tool_result", "content": "contents1"}),
            _json_line({"type": "tool_use", "name": "read_file"}),
            _json_line({"type": "tool_result", "content": "contents2"}),
            _result_event_string(full_text),
            b"",  # EOF
        ]
        line_iter = iter(lines)

        async def fake_readline():
            return next(line_iter)

        session.process.stdout.readline = fake_readline
        await session._read_stdout()

        calls = session._on_response.call_args_list
        # Only one call — from the result event.
        assert len(calls) == 1
        assert calls[0].args == (42, full_text)
