"""Tests for event-level logging in _extract_text_from_event and on_response.

Verifies that:
- tool_use, tool_result, and error events are logged at INFO level.
- assistant, content_block_delta, and low-signal events are logged at DEBUG.
- Extracted text from result events is logged at INFO with a preview.
- Result events with no text are logged at DEBUG.
- Successful message sends are logged at INFO in on_response.
"""

from __future__ import annotations

import json
import logging

import pytest
from mock import AsyncMock, MagicMock, patch

from telegram_bot.session import _extract_text_from_event


class TestHighSignalEventLogging:
    """tool_use, tool_result, and error events log at INFO."""

    def test_tool_use_logged_at_info(self):
        raw = json.dumps({"type": "tool_use", "name": "Read"})
        with patch("telegram_bot.session.logger") as mock_logger:
            result = _extract_text_from_event(raw)
        assert result is None
        mock_logger.info.assert_called_once()
        msg = mock_logger.info.call_args[0][0]
        assert "tool_use" in msg

    def test_tool_use_includes_tool_name(self):
        raw = json.dumps({"type": "tool_use", "name": "Bash"})
        with patch("telegram_bot.session.logger") as mock_logger:
            _extract_text_from_event(raw)
        call_args = mock_logger.info.call_args[0]
        assert "Bash" in str(call_args)

    def test_tool_use_unknown_name(self):
        raw = json.dumps({"type": "tool_use"})
        with patch("telegram_bot.session.logger") as mock_logger:
            _extract_text_from_event(raw)
        call_args = mock_logger.info.call_args[0]
        assert "unknown" in str(call_args)

    def test_tool_result_logged_at_info(self):
        raw = json.dumps({"type": "tool_result", "content": "file data"})
        with patch("telegram_bot.session.logger") as mock_logger:
            result = _extract_text_from_event(raw)
        assert result is None
        mock_logger.info.assert_called_once()
        msg = mock_logger.info.call_args[0][0]
        assert "tool_result" in msg

    def test_error_logged_at_info(self):
        raw = json.dumps({"type": "error", "error": "something went wrong"})
        with patch("telegram_bot.session.logger") as mock_logger:
            result = _extract_text_from_event(raw)
        assert result is None
        mock_logger.info.assert_called_once()
        msg = mock_logger.info.call_args[0][0]
        assert "error" in msg


class TestLowSignalEventLogging:
    """assistant, content_block_delta, and other events log at DEBUG."""

    def test_assistant_logged_at_debug(self):
        raw = json.dumps({
            "type": "assistant",
            "message": {"content": [{"type": "text", "text": "Hi"}]},
        })
        with patch("telegram_bot.session.logger") as mock_logger:
            result = _extract_text_from_event(raw)
        assert result is None
        mock_logger.debug.assert_called()
        mock_logger.info.assert_not_called()

    def test_content_block_delta_logged_at_debug(self):
        raw = json.dumps({
            "type": "content_block_delta",
            "delta": {"type": "text_delta", "text": "chunk"},
        })
        with patch("telegram_bot.session.logger") as mock_logger:
            result = _extract_text_from_event(raw)
        assert result is None
        mock_logger.debug.assert_called()
        mock_logger.info.assert_not_called()

    @pytest.mark.parametrize("event_type", [
        "ping", "system", "content_block_start", "content_block_stop",
        "message_start", "message_stop", "message_delta",
    ])
    def test_low_signal_events_logged_at_debug(self, event_type):
        raw = json.dumps({"type": event_type})
        with patch("telegram_bot.session.logger") as mock_logger:
            result = _extract_text_from_event(raw)
        assert result is None
        mock_logger.debug.assert_called()
        mock_logger.info.assert_not_called()


class TestResultEventLogging:
    """Result events log extracted text at INFO, empty results at DEBUG."""

    def test_result_with_text_logged_at_info(self):
        raw = json.dumps({"type": "result", "result": "The answer is 42."})
        with patch("telegram_bot.session.logger") as mock_logger:
            result = _extract_text_from_event(raw)
        assert result == "The answer is 42."
        mock_logger.info.assert_called_once()
        msg = mock_logger.info.call_args[0][0]
        assert "Extracted text" in msg

    def test_result_text_preview_truncated_to_80_chars(self):
        long_text = "A" * 200
        raw = json.dumps({"type": "result", "result": long_text})
        with patch("telegram_bot.session.logger") as mock_logger:
            _extract_text_from_event(raw)
        # The preview in the log should be truncated
        call_args = mock_logger.info.call_args[0]
        # Third positional arg is the truncated text preview
        preview = call_args[2]
        assert len(preview) == 80

    def test_result_no_text_logged_at_debug(self):
        raw = json.dumps({"type": "result", "result": {"content": []}})
        with patch("telegram_bot.session.logger") as mock_logger:
            result = _extract_text_from_event(raw)
        assert result is None
        mock_logger.debug.assert_called()
        mock_logger.info.assert_not_called()


class TestOnResponseSuccessLogging:
    """Successful message send is logged at INFO in on_response."""

    @pytest.mark.asyncio
    async def test_on_response_logs_success(self):
        """on_response logs chat_id and char count on successful send."""
        from telegram_bot.bot import agent_command_handler

        update = MagicMock()
        update.effective_user = MagicMock()
        update.effective_user.id = 100
        update.effective_chat = MagicMock()
        update.effective_chat.id = 100
        update.message = MagicMock()
        update.message.text = "/operator"
        update.message.reply_text = AsyncMock()

        sm = MagicMock()
        sm.has_session = MagicMock(return_value=False)
        mock_session = MagicMock()
        mock_session.send = AsyncMock()
        sm.start_session = AsyncMock(return_value=mock_session)

        bot = MagicMock()
        bot.send_message = AsyncMock()

        context = MagicMock()
        context.bot_data = {
            "agents": ["operator"],
            "allowed_users": {100},
            "session_manager": sm,
        }
        context.bot = bot

        await agent_command_handler(update, context)

        # Extract the on_response callback that was passed to start_session
        call_kwargs = sm.start_session.call_args
        on_response = call_kwargs.kwargs.get("on_response") or call_kwargs[1].get("on_response")
        if on_response is None:
            # positional args
            on_response = call_kwargs[0][2] if len(call_kwargs[0]) > 2 else sm.start_session.call_args.kwargs["on_response"]

        # Simulate a successful send
        with patch("telegram_bot.bot.send_long_message", new_callable=AsyncMock, return_value=True):
            with patch("telegram_bot.bot.logger") as mock_logger:
                await on_response(100, "Hello world!")
                # Verify INFO log was called with chat_id and length
                mock_logger.info.assert_called()
                info_calls = [
                    c for c in mock_logger.info.call_args_list
                    if "Message sent" in str(c)
                ]
                assert len(info_calls) == 1

    @pytest.mark.asyncio
    async def test_on_response_no_log_on_failure(self):
        """on_response does NOT log success when send fails."""
        from telegram_bot.bot import agent_command_handler

        update = MagicMock()
        update.effective_user = MagicMock()
        update.effective_user.id = 100
        update.effective_chat = MagicMock()
        update.effective_chat.id = 100
        update.message = MagicMock()
        update.message.text = "/operator"
        update.message.reply_text = AsyncMock()

        sm = MagicMock()
        sm.has_session = MagicMock(return_value=False)
        mock_session = MagicMock()
        mock_session.send = AsyncMock()
        sm.start_session = AsyncMock(return_value=mock_session)
        sm.end_session = AsyncMock()

        bot = MagicMock()
        bot.send_message = AsyncMock()

        context = MagicMock()
        context.bot_data = {
            "agents": ["operator"],
            "allowed_users": {100},
            "session_manager": sm,
        }
        context.bot = bot

        await agent_command_handler(update, context)

        call_kwargs = sm.start_session.call_args
        on_response = call_kwargs.kwargs.get("on_response") or call_kwargs[1].get("on_response")
        if on_response is None:
            on_response = call_kwargs[0][2] if len(call_kwargs[0]) > 2 else sm.start_session.call_args.kwargs["on_response"]

        # Simulate a failed send
        with patch("telegram_bot.bot.send_long_message", new_callable=AsyncMock, return_value=False):
            with patch("telegram_bot.bot.logger") as mock_logger:
                await on_response(100, "Hello world!")
                info_calls = [
                    c for c in mock_logger.info.call_args_list
                    if "Message sent" in str(c)
                ]
                assert len(info_calls) == 0
