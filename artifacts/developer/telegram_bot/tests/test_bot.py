"""Tests for telegram_bot.bot module."""

from __future__ import annotations

import asyncio
import subprocess
from mock import AsyncMock, MagicMock, patch

import pytest

from telegram_bot.bot import (
    _check_claude_cli,
    agent_command_handler,
    auth_required,
    end_handler,
    help_handler,
    plain_text_handler,
    send_long_message,
    split_message,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_update(
    user_id: int = 100,
    chat_id: int = 100,
    text: str = "",
) -> MagicMock:
    """Create a mock ``Update`` object."""
    update = MagicMock()
    update.effective_user = MagicMock()
    update.effective_user.id = user_id
    update.effective_chat = MagicMock()
    update.effective_chat.id = chat_id
    update.message = MagicMock()
    update.message.text = text
    update.message.reply_text = AsyncMock()
    return update


def _make_context(
    agents=None,
    allowed_users=None,
    session_manager=None,
    bot=None,
) -> MagicMock:
    """Create a mock ``ContextTypes.DEFAULT_TYPE`` object."""
    context = MagicMock()
    bot_data = {
        "agents": agents or ["operator", "architect", "designer"],
        "allowed_users": allowed_users or {100, 200},
        "session_manager": session_manager or MagicMock(),
    }
    context.bot_data = bot_data
    context.bot = bot or MagicMock()
    return context


def _make_session_manager(has_session: bool = False, agent_name: str = "operator"):
    """Create a mock ``SessionManager``."""
    sm = MagicMock()
    sm.has_session = MagicMock(return_value=has_session)
    sm.start_session = AsyncMock()
    sm.send_message = AsyncMock()
    sm.end_session = AsyncMock()
    if has_session:
        session = MagicMock()
        session.agent_name = agent_name
        sm._sessions = {100: session}
    else:
        sm._sessions = {}
    return sm


# ---------------------------------------------------------------------------
# split_message tests
# ---------------------------------------------------------------------------


class TestSplitMessage:
    """Tests for the ``split_message`` utility."""

    def test_empty_string(self):
        assert split_message("") == [""]

    def test_short_message_unchanged(self):
        assert split_message("hello") == ["hello"]

    def test_exactly_max_length(self):
        text = "a" * 4096
        result = split_message(text)
        assert result == [text]

    def test_split_at_paragraph_break(self):
        part1 = "a" * 2000
        part2 = "b" * 2000
        text = part1 + "\n\n" + part2
        result = split_message(text, max_length=2500)
        assert result == [part1, part2]

    def test_split_at_line_break(self):
        part1 = "a" * 2000
        part2 = "b" * 2000
        text = part1 + "\n" + part2
        result = split_message(text, max_length=2500)
        assert result == [part1, part2]

    def test_hard_split_when_no_break(self):
        text = "a" * 5000
        result = split_message(text, max_length=2000)
        assert len(result) == 3
        assert result[0] == "a" * 2000
        assert result[1] == "a" * 2000
        assert result[2] == "a" * 1000

    def test_prefers_paragraph_over_line_break(self):
        # Both \n\n and \n present — should split at \n\n first
        text = "aaa\nbbb\n\nccc"
        result = split_message(text, max_length=10)
        assert result[0] == "aaa\nbbb"
        assert result[1] == "ccc"

    def test_multiple_splits(self):
        parts = ["x" * 100 for _ in range(5)]
        text = "\n\n".join(parts)
        result = split_message(text, max_length=150)
        assert len(result) == 5

    def test_custom_max_length(self):
        text = "a" * 10
        result = split_message(text, max_length=3)
        assert result == ["aaa", "aaa", "aaa", "a"]


# ---------------------------------------------------------------------------
# send_long_message tests
# ---------------------------------------------------------------------------


class TestSendLongMessage:
    """Tests for send_long_message splitting + sending."""

    @pytest.mark.asyncio
    async def test_sends_short_message_as_one(self):
        bot = MagicMock()
        bot.send_message = AsyncMock()

        await send_long_message(bot, 123, "short")

        assert bot.send_message.call_count == 1

    @pytest.mark.asyncio
    async def test_sends_long_message_as_multiple(self):
        bot = MagicMock()
        bot.send_message = AsyncMock()

        text = ("a" * 4000) + "\n\n" + ("b" * 4000)
        await send_long_message(bot, 123, text)

        assert bot.send_message.call_count == 2

    @pytest.mark.asyncio
    async def test_sends_as_plain_text_no_parse_mode(self):
        """Messages are sent as plain text — no parse_mode parameter."""
        bot = MagicMock()
        bot.send_message = AsyncMock()

        await send_long_message(bot, 123, "hello")

        bot.send_message.assert_called_once_with(chat_id=123, text="hello")

    @pytest.mark.asyncio
    async def test_special_characters_sent_without_error(self):
        """Special characters that would break MarkdownV2 are sent fine."""
        bot = MagicMock()
        bot.send_message = AsyncMock()

        text = "Hello. It's a (test) - with *special* _chars_ and `code`!"
        await send_long_message(bot, 123, text)

        bot.send_message.assert_called_once_with(chat_id=123, text=text)

    @pytest.mark.asyncio
    async def test_each_chunk_sent_as_plain_text(self):
        """Each chunk of a long message is sent as plain text."""
        bot = MagicMock()
        bot.send_message = AsyncMock()

        text = ("a" * 4000) + "\n\n" + ("b" * 4000)
        await send_long_message(bot, 123, text)

        assert bot.send_message.call_count == 2
        for call in bot.send_message.call_args_list:
            # Verify no parse_mode keyword argument
            assert "parse_mode" not in call.kwargs


# ---------------------------------------------------------------------------
# auth_required tests
# ---------------------------------------------------------------------------


class TestAuthRequired:
    """Tests for the authentication decorator."""

    @pytest.mark.asyncio
    async def test_allows_authorised_user(self):
        handler = AsyncMock()
        wrapped = auth_required(handler)

        update = _make_update(user_id=100)
        context = _make_context(allowed_users={100})

        await wrapped(update, context)
        handler.assert_called_once()

    @pytest.mark.asyncio
    async def test_rejects_unauthorised_user(self):
        handler = AsyncMock()
        wrapped = auth_required(handler)

        update = _make_update(user_id=999)
        context = _make_context(allowed_users={100})

        await wrapped(update, context)
        handler.assert_not_called()
        # Silently ignored — no reply sent.
        update.message.reply_text.assert_not_called()

    @pytest.mark.asyncio
    async def test_rejects_when_no_effective_user(self):
        handler = AsyncMock()
        wrapped = auth_required(handler)

        update = _make_update()
        update.effective_user = None
        context = _make_context(allowed_users={100})

        await wrapped(update, context)
        handler.assert_not_called()

    @pytest.mark.asyncio
    async def test_logs_debug_on_rejected_user(self):
        handler = AsyncMock()
        wrapped = auth_required(handler)

        update = _make_update(user_id=999)
        context = _make_context(allowed_users={100})

        with patch("telegram_bot.bot.logger") as mock_logger:
            await wrapped(update, context)
            mock_logger.debug.assert_called_once_with(
                "Rejected message from unauthorized user %s", 999
            )

    @pytest.mark.asyncio
    async def test_logs_debug_unknown_when_no_effective_user(self):
        handler = AsyncMock()
        wrapped = auth_required(handler)

        update = _make_update()
        update.effective_user = None
        context = _make_context(allowed_users={100})

        with patch("telegram_bot.bot.logger") as mock_logger:
            await wrapped(update, context)
            mock_logger.debug.assert_called_once_with(
                "Rejected message from unauthorized user %s", "unknown"
            )


# ---------------------------------------------------------------------------
# agent_command_handler tests
# ---------------------------------------------------------------------------


class TestAgentCommandHandler:
    """Tests for /<agent_name> command routing."""

    @pytest.mark.asyncio
    async def test_starts_session_for_valid_agent(self):
        sm = _make_session_manager(has_session=False)
        session = MagicMock()
        session.send = AsyncMock()
        sm.start_session.return_value = session

        update = _make_update(user_id=100, chat_id=100, text="/operator")
        context = _make_context(session_manager=sm)

        await agent_command_handler.__wrapped__(update, context)

        sm.start_session.assert_called_once()
        call_kwargs = sm.start_session.call_args
        assert call_kwargs.kwargs["chat_id"] == 100
        assert call_kwargs.kwargs["agent_name"] == "operator"

    @pytest.mark.asyncio
    async def test_forwards_first_message(self):
        sm = _make_session_manager(has_session=False)
        session = MagicMock()
        session.send = AsyncMock()
        sm.start_session.return_value = session

        update = _make_update(user_id=100, chat_id=100, text="/operator hello world")
        context = _make_context(session_manager=sm)

        await agent_command_handler.__wrapped__(update, context)

        session.send.assert_called_once_with("hello world")

    @pytest.mark.asyncio
    async def test_sends_confirmation_message_without_first_message(self):
        sm = _make_session_manager(has_session=False)
        session = MagicMock()
        session.send = AsyncMock()
        sm.start_session.return_value = session

        update = _make_update(user_id=100, chat_id=100, text="/operator")
        context = _make_context(session_manager=sm)

        await agent_command_handler.__wrapped__(update, context)

        reply = update.message.reply_text.call_args[0][0]
        assert reply == "Starting session with `operator`\u2026"

    @pytest.mark.asyncio
    async def test_sends_confirmation_message_with_first_message(self):
        sm = _make_session_manager(has_session=False)
        session = MagicMock()
        session.send = AsyncMock()
        sm.start_session.return_value = session

        update = _make_update(user_id=100, chat_id=100, text="/architect hello")
        context = _make_context(session_manager=sm)

        await agent_command_handler.__wrapped__(update, context)

        reply = update.message.reply_text.call_args[0][0]
        assert reply == "Starting session with `architect`\u2026"
        session.send.assert_called_once_with("hello")

    @pytest.mark.asyncio
    async def test_confirmation_sent_before_first_message(self):
        """Verify reply_text (confirmation) is called before session.send."""
        sm = _make_session_manager(has_session=False)
        session = MagicMock()

        call_order: list = []
        async def _track_reply(*args, **kwargs):
            call_order.append("reply_text")
        async def _track_send(*args, **kwargs):
            call_order.append("send")

        session.send = AsyncMock(side_effect=_track_send)
        sm.start_session.return_value = session

        update = _make_update(user_id=100, chat_id=100, text="/operator hi")
        update.message.reply_text = AsyncMock(side_effect=_track_reply)
        context = _make_context(session_manager=sm)

        await agent_command_handler.__wrapped__(update, context)

        assert call_order == ["reply_text", "send"]

    @pytest.mark.asyncio
    async def test_rejects_when_session_active(self):
        sm = _make_session_manager(has_session=True, agent_name="architect")

        update = _make_update(user_id=100, chat_id=100, text="/operator")
        context = _make_context(session_manager=sm)

        await agent_command_handler.__wrapped__(update, context)

        sm.start_session.assert_not_called()
        reply = update.message.reply_text.call_args[0][0]
        assert "active session" in reply.lower()
        assert "architect" in reply

    @pytest.mark.asyncio
    async def test_rejects_unknown_agent(self):
        sm = _make_session_manager(has_session=False)

        update = _make_update(user_id=100, chat_id=100, text="/invalid_agent")
        context = _make_context(
            agents=["operator", "architect", "designer"],
            session_manager=sm,
        )

        await agent_command_handler.__wrapped__(update, context)

        sm.start_session.assert_not_called()
        reply = update.message.reply_text.call_args[0][0]
        assert "unknown agent" in reply.lower()
        assert "operator" in reply

    @pytest.mark.asyncio
    async def test_spawn_failure_file_not_found(self):
        """FileNotFoundError from start_session sends error reply."""
        sm = _make_session_manager(has_session=False)
        sm.start_session.side_effect = FileNotFoundError("claude not found")

        update = _make_update(user_id=100, chat_id=100, text="/operator")
        context = _make_context(session_manager=sm)

        with patch("telegram_bot.bot.logger") as mock_logger:
            await agent_command_handler.__wrapped__(update, context)

            mock_logger.error.assert_called_once()
            log_args = mock_logger.error.call_args[0]
            assert "operator" in log_args[0] % tuple(log_args[1:])

        reply = update.message.reply_text.call_args[0][0]
        assert "failed to start session" in reply.lower()
        assert "operator" in reply
        assert "claude" in reply.lower()

    @pytest.mark.asyncio
    async def test_spawn_failure_os_error(self):
        """OSError from start_session sends error reply."""
        sm = _make_session_manager(has_session=False)
        sm.start_session.side_effect = OSError("permission denied")

        update = _make_update(user_id=100, chat_id=100, text="/operator")
        context = _make_context(session_manager=sm)

        with patch("telegram_bot.bot.logger") as mock_logger:
            await agent_command_handler.__wrapped__(update, context)

            mock_logger.error.assert_called_once()

        reply = update.message.reply_text.call_args[0][0]
        assert "failed to start session" in reply.lower()

    @pytest.mark.asyncio
    async def test_spawn_failure_unexpected_exception(self):
        """Unexpected exception from start_session sends error reply and logs traceback."""
        sm = _make_session_manager(has_session=False)
        sm.start_session.side_effect = RuntimeError("something unexpected")

        update = _make_update(user_id=100, chat_id=100, text="/operator")
        context = _make_context(session_manager=sm)

        with patch("telegram_bot.bot.logger") as mock_logger:
            await agent_command_handler.__wrapped__(update, context)

            # Unexpected errors use logger.exception for traceback
            mock_logger.exception.assert_called_once()

        reply = update.message.reply_text.call_args[0][0]
        assert "failed to start session" in reply.lower()
        assert "operator" in reply

    @pytest.mark.asyncio
    async def test_spawn_failure_no_session_left_behind(self):
        """After spawn failure, no session state is left — a new start is possible."""
        sm = _make_session_manager(has_session=False)
        sm.start_session.side_effect = FileNotFoundError("claude not found")

        update = _make_update(user_id=100, chat_id=100, text="/operator")
        context = _make_context(session_manager=sm)

        await agent_command_handler.__wrapped__(update, context)

        # has_session should still return False (no stale session)
        assert sm.has_session(100) is False

    @pytest.mark.asyncio
    async def test_spawn_failure_no_first_message_sent(self):
        """On spawn failure, no first message is forwarded to the session."""
        sm = _make_session_manager(has_session=False)
        sm.start_session.side_effect = FileNotFoundError("claude not found")

        update = _make_update(user_id=100, chat_id=100, text="/operator hello")
        context = _make_context(session_manager=sm)

        await agent_command_handler.__wrapped__(update, context)

        # Confirmation message should NOT be sent — only the error reply
        reply = update.message.reply_text.call_args[0][0]
        assert "failed to start session" in reply.lower()
        # Only one reply (the error), not two (error + confirmation)
        assert update.message.reply_text.call_count == 1


# ---------------------------------------------------------------------------
# end_handler tests
# ---------------------------------------------------------------------------


class TestEndHandler:
    """Tests for the /end command."""

    @pytest.mark.asyncio
    async def test_ends_active_session(self):
        sm = _make_session_manager(has_session=True)

        update = _make_update(user_id=100, chat_id=100, text="/end")
        context = _make_context(session_manager=sm)

        await end_handler.__wrapped__(update, context)

        sm.end_session.assert_called_once_with(100)

    @pytest.mark.asyncio
    async def test_no_active_session(self):
        sm = _make_session_manager(has_session=False)

        update = _make_update(user_id=100, chat_id=100, text="/end")
        context = _make_context(session_manager=sm)

        await end_handler.__wrapped__(update, context)

        sm.end_session.assert_not_called()
        reply = update.message.reply_text.call_args[0][0]
        assert "no active session" in reply.lower()


# ---------------------------------------------------------------------------
# help_handler tests
# ---------------------------------------------------------------------------


class TestHelpHandler:
    """Tests for the /help command."""

    @pytest.mark.asyncio
    async def test_lists_all_agents(self):
        update = _make_update(user_id=100, chat_id=100, text="/help")
        context = _make_context(agents=["operator", "architect", "designer"])

        await help_handler.__wrapped__(update, context)

        reply = update.message.reply_text.call_args[0][0]
        assert "/operator" in reply
        assert "/architect" in reply
        assert "/designer" in reply
        assert "/end" in reply
        assert "/help" in reply


# ---------------------------------------------------------------------------
# plain_text_handler tests
# ---------------------------------------------------------------------------


class TestPlainTextHandler:
    """Tests for plain text (non-command) messages."""

    @pytest.mark.asyncio
    async def test_pipes_to_active_session(self):
        sm = _make_session_manager(has_session=True)

        update = _make_update(user_id=100, chat_id=100, text="hello agent")
        context = _make_context(session_manager=sm)

        await plain_text_handler.__wrapped__(update, context)

        sm.send_message.assert_called_once_with(100, "hello agent")

    @pytest.mark.asyncio
    async def test_no_active_session_error(self):
        sm = _make_session_manager(has_session=False)

        update = _make_update(user_id=100, chat_id=100, text="hello agent")
        context = _make_context(session_manager=sm)

        await plain_text_handler.__wrapped__(update, context)

        sm.send_message.assert_not_called()
        reply = update.message.reply_text.call_args[0][0]
        assert "no active session" in reply.lower()

    @pytest.mark.asyncio
    async def test_ignores_empty_text(self):
        sm = _make_session_manager(has_session=True)

        update = _make_update(user_id=100, chat_id=100, text="   ")
        context = _make_context(session_manager=sm)

        await plain_text_handler.__wrapped__(update, context)

        sm.send_message.assert_not_called()


# ---------------------------------------------------------------------------
# _check_claude_cli tests
# ---------------------------------------------------------------------------


class TestCheckClaudeCli:
    """Tests for the pre-flight claude CLI check."""

    def test_success_returns_version(self):
        """Successful check returns the version string."""
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "claude 1.2.3\n"
        mock_result.stderr = ""

        with patch("telegram_bot.bot.subprocess.run", return_value=mock_result):
            version = _check_claude_cli()

        assert version == "claude 1.2.3"

    def test_success_logs_version_at_info(self):
        """Successful check logs the version at INFO level."""
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "claude 1.2.3\n"
        mock_result.stderr = ""

        with patch("telegram_bot.bot.subprocess.run", return_value=mock_result):
            with patch("telegram_bot.bot.logger") as mock_logger:
                _check_claude_cli()
                mock_logger.info.assert_called_once_with(
                    "claude CLI version: %s", "claude 1.2.3"
                )

    def test_file_not_found_exits(self):
        """FileNotFoundError causes sys.exit(1)."""
        with patch(
            "telegram_bot.bot.subprocess.run",
            side_effect=FileNotFoundError("not found"),
        ):
            with pytest.raises(SystemExit) as exc_info:
                _check_claude_cli()

        assert exc_info.value.code == 1

    def test_timeout_exits(self):
        """Timeout causes sys.exit(1)."""
        with patch(
            "telegram_bot.bot.subprocess.run",
            side_effect=subprocess.TimeoutExpired("claude", 10),
        ):
            with pytest.raises(SystemExit) as exc_info:
                _check_claude_cli()

        assert exc_info.value.code == 1

    def test_os_error_exits(self):
        """OSError causes sys.exit(1)."""
        with patch(
            "telegram_bot.bot.subprocess.run",
            side_effect=OSError("permission denied"),
        ):
            with pytest.raises(SystemExit) as exc_info:
                _check_claude_cli()

        assert exc_info.value.code == 1

    def test_nonzero_exit_code_exits(self):
        """Non-zero exit code from claude --version causes sys.exit(1)."""
        mock_result = MagicMock()
        mock_result.returncode = 1
        mock_result.stdout = ""
        mock_result.stderr = "Unsupported Node.js version"

        with patch("telegram_bot.bot.subprocess.run", return_value=mock_result):
            with pytest.raises(SystemExit) as exc_info:
                _check_claude_cli()

        assert exc_info.value.code == 1

    def test_nonzero_exit_logs_stderr_snippet(self):
        """Non-zero exit should log the stderr snippet."""
        mock_result = MagicMock()
        mock_result.returncode = 1
        mock_result.stdout = ""
        mock_result.stderr = "Unsupported Node.js version"

        with patch("telegram_bot.bot.subprocess.run", return_value=mock_result):
            with patch("telegram_bot.bot.logger") as mock_logger:
                with pytest.raises(SystemExit):
                    _check_claude_cli()

        mock_logger.error.assert_called_once()
        error_msg = str(mock_logger.error.call_args)
        assert "Unsupported Node.js version" in error_msg

    def test_custom_command_path(self):
        """Custom command path should be used."""
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "claude 2.0.0\n"
        mock_result.stderr = ""

        with patch("telegram_bot.bot.subprocess.run", return_value=mock_result) as mock_run:
            _check_claude_cli("/usr/local/bin/claude")

        mock_run.assert_called_once_with(
            ["/usr/local/bin/claude", "--version"],
            capture_output=True,
            text=True,
            timeout=10,
        )

    def test_file_not_found_logs_descriptive_message(self):
        """FileNotFoundError should log a message mentioning the command path."""
        with patch(
            "telegram_bot.bot.subprocess.run",
            side_effect=FileNotFoundError("not found"),
        ):
            with patch("telegram_bot.bot.logger") as mock_logger:
                with pytest.raises(SystemExit):
                    _check_claude_cli("/custom/path/claude")

        error_msg = str(mock_logger.error.call_args)
        assert "/custom/path/claude" in error_msg


# ---------------------------------------------------------------------------
# on_end callback with stderr tests
# ---------------------------------------------------------------------------


class TestOnEndWithStderr:
    """Tests for on_end callback stderr surfacing in crash messages."""

    @pytest.mark.asyncio
    async def test_crash_message_includes_stderr(self):
        """On crash with stderr, the message should include diagnostics."""
        sm = _make_session_manager(has_session=False)
        session = MagicMock()
        session.send = AsyncMock()
        sm.start_session.return_value = session

        update = _make_update(user_id=100, chat_id=100, text="/operator")
        bot = MagicMock()
        bot.send_message = AsyncMock()
        context = _make_context(session_manager=sm, bot=bot)

        # Start session to capture the on_end callback.
        await agent_command_handler.__wrapped__(update, context)

        # Extract the on_end callback that was passed to start_session.
        on_end = sm.start_session.call_args.kwargs["on_end"]

        # Invoke it with a crash reason and stderr.
        await on_end(100, "operator", "crash", stderr_tail="node: command not found")

        # Verify the message contains stderr diagnostics.
        bot.send_message.assert_called()
        sent_text = bot.send_message.call_args.kwargs["text"]
        assert "ended unexpectedly" in sent_text
        assert "node: command not found" in sent_text

    @pytest.mark.asyncio
    async def test_crash_message_without_stderr(self):
        """On crash without stderr, message should not have diagnostics section."""
        sm = _make_session_manager(has_session=False)
        session = MagicMock()
        session.send = AsyncMock()
        sm.start_session.return_value = session

        update = _make_update(user_id=100, chat_id=100, text="/operator")
        bot = MagicMock()
        bot.send_message = AsyncMock()
        context = _make_context(session_manager=sm, bot=bot)

        await agent_command_handler.__wrapped__(update, context)
        on_end = sm.start_session.call_args.kwargs["on_end"]

        await on_end(100, "operator", "crash", stderr_tail="")

        bot.send_message.assert_called()
        sent_text = bot.send_message.call_args.kwargs["text"]
        assert "ended unexpectedly" in sent_text
        assert "Diagnostics" not in sent_text

    @pytest.mark.asyncio
    async def test_shutdown_message_no_stderr(self):
        """Normal shutdown should not include diagnostics even if stderr is provided."""
        sm = _make_session_manager(has_session=False)
        session = MagicMock()
        session.send = AsyncMock()
        sm.start_session.return_value = session

        update = _make_update(user_id=100, chat_id=100, text="/operator")
        bot = MagicMock()
        bot.send_message = AsyncMock()
        context = _make_context(session_manager=sm, bot=bot)

        await agent_command_handler.__wrapped__(update, context)
        on_end = sm.start_session.call_args.kwargs["on_end"]

        await on_end(100, "operator", "shutdown", stderr_tail="some stderr")

        bot.send_message.assert_called()
        sent_text = bot.send_message.call_args.kwargs["text"]
        assert "ended" in sent_text.lower()
        assert "Diagnostics" not in sent_text
