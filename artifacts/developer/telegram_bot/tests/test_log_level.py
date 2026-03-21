"""Tests for configurable LOG_LEVEL in bot.main().

Verifies that:
- Default log level is INFO when LOG_LEVEL is not set.
- LOG_LEVEL env var is respected for valid values.
- Case-insensitive handling (e.g., 'debug' -> DEBUG).
- Invalid LOG_LEVEL falls back to INFO with a warning.
- The active log level is logged at startup.
"""

from __future__ import annotations

import logging
import os

import pytest
from mock import MagicMock, patch

from telegram_bot.bot import main


class TestConfigurableLogLevel:
    """Tests for LOG_LEVEL environment variable handling in main()."""

    @patch("telegram_bot.bot.Application")
    @patch("telegram_bot.bot.build_application")
    @patch("telegram_bot.bot.load_config")
    @patch("telegram_bot.bot._check_claude_cli")
    def test_default_log_level_is_info(
        self, mock_cli, mock_config, mock_build, mock_app
    ):
        """Without LOG_LEVEL set, logging defaults to INFO."""
        mock_config.return_value = MagicMock(claude_path=None)
        mock_app_instance = MagicMock()
        mock_build.return_value = mock_app_instance

        env = os.environ.copy()
        env.pop("LOG_LEVEL", None)

        with patch.dict(os.environ, env, clear=True):
            with patch("logging.basicConfig") as mock_basic:
                # main() calls run_polling which blocks; mock it
                mock_app_instance.run_polling = MagicMock()
                main()
                mock_basic.assert_called_once()
                call_kwargs = mock_basic.call_args
                assert call_kwargs[1]["level"] == logging.INFO

    @patch("telegram_bot.bot.Application")
    @patch("telegram_bot.bot.build_application")
    @patch("telegram_bot.bot.load_config")
    @patch("telegram_bot.bot._check_claude_cli")
    def test_log_level_debug(self, mock_cli, mock_config, mock_build, mock_app):
        """LOG_LEVEL=DEBUG sets logging to DEBUG."""
        mock_config.return_value = MagicMock(claude_path=None)
        mock_app_instance = MagicMock()
        mock_build.return_value = mock_app_instance
        mock_app_instance.run_polling = MagicMock()

        with patch.dict(os.environ, {"LOG_LEVEL": "DEBUG"}):
            with patch("logging.basicConfig") as mock_basic:
                main()
                assert mock_basic.call_args[1]["level"] == logging.DEBUG

    @patch("telegram_bot.bot.Application")
    @patch("telegram_bot.bot.build_application")
    @patch("telegram_bot.bot.load_config")
    @patch("telegram_bot.bot._check_claude_cli")
    def test_log_level_warning(self, mock_cli, mock_config, mock_build, mock_app):
        """LOG_LEVEL=WARNING sets logging to WARNING."""
        mock_config.return_value = MagicMock(claude_path=None)
        mock_app_instance = MagicMock()
        mock_build.return_value = mock_app_instance
        mock_app_instance.run_polling = MagicMock()

        with patch.dict(os.environ, {"LOG_LEVEL": "WARNING"}):
            with patch("logging.basicConfig") as mock_basic:
                main()
                assert mock_basic.call_args[1]["level"] == logging.WARNING

    @patch("telegram_bot.bot.Application")
    @patch("telegram_bot.bot.build_application")
    @patch("telegram_bot.bot.load_config")
    @patch("telegram_bot.bot._check_claude_cli")
    def test_log_level_case_insensitive(
        self, mock_cli, mock_config, mock_build, mock_app
    ):
        """LOG_LEVEL=debug (lowercase) is normalised to DEBUG."""
        mock_config.return_value = MagicMock(claude_path=None)
        mock_app_instance = MagicMock()
        mock_build.return_value = mock_app_instance
        mock_app_instance.run_polling = MagicMock()

        with patch.dict(os.environ, {"LOG_LEVEL": "debug"}):
            with patch("logging.basicConfig") as mock_basic:
                main()
                assert mock_basic.call_args[1]["level"] == logging.DEBUG

    @patch("telegram_bot.bot.Application")
    @patch("telegram_bot.bot.build_application")
    @patch("telegram_bot.bot.load_config")
    @patch("telegram_bot.bot._check_claude_cli")
    def test_invalid_log_level_falls_back_to_info(
        self, mock_cli, mock_config, mock_build, mock_app
    ):
        """An invalid LOG_LEVEL falls back to INFO."""
        mock_config.return_value = MagicMock(claude_path=None)
        mock_app_instance = MagicMock()
        mock_build.return_value = mock_app_instance
        mock_app_instance.run_polling = MagicMock()

        with patch.dict(os.environ, {"LOG_LEVEL": "VERBOSE"}):
            with patch("logging.basicConfig") as mock_basic:
                main()
                assert mock_basic.call_args[1]["level"] == logging.INFO

    @patch("telegram_bot.bot.Application")
    @patch("telegram_bot.bot.build_application")
    @patch("telegram_bot.bot.load_config")
    @patch("telegram_bot.bot._check_claude_cli")
    def test_invalid_log_level_logs_warning(
        self, mock_cli, mock_config, mock_build, mock_app
    ):
        """An invalid LOG_LEVEL triggers a warning log."""
        mock_config.return_value = MagicMock(claude_path=None)
        mock_app_instance = MagicMock()
        mock_build.return_value = mock_app_instance
        mock_app_instance.run_polling = MagicMock()

        with patch.dict(os.environ, {"LOG_LEVEL": "VERBOSE"}):
            with patch("telegram_bot.bot.logger") as mock_logger:
                main()
                # Check that a warning was logged about the invalid value
                mock_logger.warning.assert_called()
                warning_msg = mock_logger.warning.call_args[0][0]
                assert "Invalid LOG_LEVEL" in warning_msg

    @patch("telegram_bot.bot.Application")
    @patch("telegram_bot.bot.build_application")
    @patch("telegram_bot.bot.load_config")
    @patch("telegram_bot.bot._check_claude_cli")
    def test_startup_logs_active_level(
        self, mock_cli, mock_config, mock_build, mock_app
    ):
        """The active log level is logged at INFO on startup."""
        mock_config.return_value = MagicMock(claude_path=None)
        mock_app_instance = MagicMock()
        mock_build.return_value = mock_app_instance
        mock_app_instance.run_polling = MagicMock()

        with patch.dict(os.environ, {"LOG_LEVEL": "DEBUG"}):
            with patch("telegram_bot.bot.logger") as mock_logger:
                main()
                # Find the info call about log level
                info_calls = [
                    call for call in mock_logger.info.call_args_list
                    if "Log level set to" in str(call)
                ]
                assert len(info_calls) >= 1
