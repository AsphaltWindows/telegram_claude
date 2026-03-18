"""Tests for _PROJECT_ROOT computation across modules.

Verifies that _PROJECT_ROOT uses Path.cwd() instead of __file__-based
parent counting, and that the configurable project_root option works.
"""

from __future__ import annotations

import os
from pathlib import Path
from mock import AsyncMock, MagicMock, patch

import pytest
import yaml

from telegram_bot import config as config_mod
from telegram_bot import discovery as discovery_mod
from telegram_bot import session as session_mod


# ---------------------------------------------------------------------------
# _PROJECT_ROOT uses Path.cwd()
# ---------------------------------------------------------------------------


class TestProjectRootIsCwd:
    """All three modules should derive _PROJECT_ROOT from Path.cwd()."""

    def test_session_project_root_is_cwd(self):
        assert session_mod._PROJECT_ROOT == Path.cwd()

    def test_config_project_root_is_cwd(self):
        assert config_mod._PROJECT_ROOT == Path.cwd()

    def test_discovery_project_root_is_cwd(self):
        assert discovery_mod._PROJECT_ROOT == Path.cwd()

    def test_session_project_root_is_not_file_based(self):
        """Ensure _PROJECT_ROOT is NOT the __file__-based two-levels-up path."""
        file_based = Path(session_mod.__file__).resolve().parent.parent
        # They might coincidentally match if cwd IS that directory,
        # but the code should NOT use __file__ arithmetic.
        # We verify the actual source uses Path.cwd() via a reload check.
        import importlib
        import tempfile

        # Change to a temporary directory and reload to prove it follows cwd.
        original_cwd = os.getcwd()
        with tempfile.TemporaryDirectory() as tmpdir:
            try:
                os.chdir(tmpdir)
                importlib.reload(session_mod)
                assert session_mod._PROJECT_ROOT == Path(tmpdir)
            finally:
                os.chdir(original_cwd)
                importlib.reload(session_mod)


# ---------------------------------------------------------------------------
# SessionManager uses project_root for subprocess cwd
# ---------------------------------------------------------------------------


class TestSessionManagerProjectRoot:
    """SessionManager should use the correct project_root for subprocess cwd."""

    def test_default_project_root_is_cwd(self):
        sm = session_mod.SessionManager(
            idle_timeout=600,
            shutdown_message="exit",
        )
        assert sm._project_root == Path.cwd()

    def test_explicit_project_root_overrides_default(self, tmp_path):
        sm = session_mod.SessionManager(
            idle_timeout=600,
            shutdown_message="exit",
            project_root=tmp_path,
        )
        assert sm._project_root == tmp_path

    @pytest.mark.asyncio
    async def test_subprocess_cwd_uses_project_root(self, tmp_path):
        """The subprocess should be spawned with cwd=project_root."""
        sm = session_mod.SessionManager(
            idle_timeout=600,
            shutdown_message="exit",
            project_root=tmp_path,
        )

        mock_process = MagicMock()
        mock_process.pid = 12345
        mock_process.stdin = MagicMock()
        mock_process.stdout = MagicMock()
        mock_process.stderr = MagicMock()

        with patch("asyncio.create_subprocess_exec", new_callable=AsyncMock) as mock_exec:
            mock_exec.return_value = mock_process

            # We need to patch Session.start to avoid background tasks
            with patch.object(session_mod.Session, "start"):
                await sm.start_session(
                    chat_id=1,
                    agent_name="test-agent",
                    on_response=AsyncMock(),
                    on_end=AsyncMock(),
                )

            # Verify cwd was passed correctly
            call_kwargs = mock_exec.call_args
            assert call_kwargs.kwargs["cwd"] == str(tmp_path)


# ---------------------------------------------------------------------------
# BotConfig.project_root
# ---------------------------------------------------------------------------


class TestConfigProjectRoot:
    """Tests for the project_root config field."""

    def _write_config(self, tmp_path, extra=None):
        """Write a minimal telegram_bot.yaml and return its path."""
        data = {"allowed_users": [100]}
        if extra:
            data.update(extra)
        path = tmp_path / "telegram_bot.yaml"
        path.write_text(yaml.dump(data), encoding="utf-8")
        return path

    def test_project_root_default_is_none(self, tmp_path):
        config_path = self._write_config(tmp_path)
        with patch.dict(os.environ, {
            "TELEGRAM_BOT_TOKEN": "test-token",
            "PIPELINE_YAML": str(tmp_path / "pipeline.yaml"),
        }):
            cfg = config_mod.load_config(config_path=config_path)
        assert cfg.project_root is None

    def test_project_root_from_yaml(self, tmp_path):
        config_path = self._write_config(
            tmp_path, extra={"project_root": str(tmp_path)}
        )
        with patch.dict(os.environ, {
            "TELEGRAM_BOT_TOKEN": "test-token",
            "PIPELINE_YAML": str(tmp_path / "pipeline.yaml"),
        }):
            cfg = config_mod.load_config(config_path=config_path)
        assert cfg.project_root == tmp_path

    def test_project_root_invalid_directory_raises(self, tmp_path):
        nonexistent = tmp_path / "does_not_exist"
        config_path = self._write_config(
            tmp_path, extra={"project_root": str(nonexistent)}
        )
        with patch.dict(os.environ, {
            "TELEGRAM_BOT_TOKEN": "test-token",
            "PIPELINE_YAML": str(tmp_path / "pipeline.yaml"),
        }):
            with pytest.raises(ValueError, match="not an existing directory"):
                config_mod.load_config(config_path=config_path)

    def test_project_root_empty_string_raises(self, tmp_path):
        config_path = self._write_config(
            tmp_path, extra={"project_root": ""}
        )
        with patch.dict(os.environ, {
            "TELEGRAM_BOT_TOKEN": "test-token",
            "PIPELINE_YAML": str(tmp_path / "pipeline.yaml"),
        }):
            with pytest.raises(ValueError, match="non-empty string"):
                config_mod.load_config(config_path=config_path)


# ---------------------------------------------------------------------------
# bot.py wiring: project_root flows from config to SessionManager
# ---------------------------------------------------------------------------


class TestBotProjectRootWiring:
    """Verify build_application passes project_root to SessionManager."""

    def test_project_root_passed_to_session_manager(self, tmp_path):
        from telegram_bot.bot import build_application

        # Create a minimal pipeline.yaml
        pipeline_path = tmp_path / "pipeline.yaml"
        pipeline_path.write_text(
            yaml.dump({"agents": [{"name": "op", "type": "source"}]}),
            encoding="utf-8",
        )

        cfg = config_mod.BotConfig(
            telegram_bot_token="test-token",
            pipeline_yaml=pipeline_path,
            allowed_users=[100],
            project_root=tmp_path,
        )

        with patch("telegram_bot.bot.Application") as MockApp:
            mock_builder = MagicMock()
            mock_app = MagicMock()
            mock_app.bot_data = {}
            mock_builder.token.return_value.build.return_value = mock_app
            MockApp.builder.return_value = mock_builder

            with patch("telegram_bot.bot.SessionManager") as MockSM:
                build_application(config=cfg)
                call_kwargs = MockSM.call_args.kwargs
                assert call_kwargs["project_root"] == tmp_path

    def test_project_root_none_passed_when_not_configured(self, tmp_path):
        from telegram_bot.bot import build_application

        pipeline_path = tmp_path / "pipeline.yaml"
        pipeline_path.write_text(
            yaml.dump({"agents": [{"name": "op", "type": "source"}]}),
            encoding="utf-8",
        )

        cfg = config_mod.BotConfig(
            telegram_bot_token="test-token",
            pipeline_yaml=pipeline_path,
            allowed_users=[100],
            # project_root defaults to None
        )

        with patch("telegram_bot.bot.Application") as MockApp:
            mock_builder = MagicMock()
            mock_app = MagicMock()
            mock_app.bot_data = {}
            mock_builder.token.return_value.build.return_value = mock_app
            MockApp.builder.return_value = mock_builder

            with patch("telegram_bot.bot.SessionManager") as MockSM:
                build_application(config=cfg)
                call_kwargs = MockSM.call_args.kwargs
                assert call_kwargs["project_root"] is None
