"""Tests for telegram_bot.config module."""

import os
import textwrap
from pathlib import Path

import pytest

from telegram_bot.config import BotConfig, load_config


@pytest.fixture
def valid_yaml(tmp_path: Path) -> Path:
    """Create a valid telegram_bot.yaml in a temp directory."""
    cfg = tmp_path / "telegram_bot.yaml"
    cfg.write_text(
        textwrap.dedent("""\
            allowed_users:
              - 111
              - 222
            idle_timeout: 300
            shutdown_message: "Goodbye."
        """)
    )
    return cfg


@pytest.fixture
def minimal_yaml(tmp_path: Path) -> Path:
    """YAML with only the required field (allowed_users)."""
    cfg = tmp_path / "telegram_bot.yaml"
    cfg.write_text(
        textwrap.dedent("""\
            allowed_users:
              - 111
        """)
    )
    return cfg


@pytest.fixture
def _set_token(monkeypatch: pytest.MonkeyPatch) -> None:
    """Set TELEGRAM_BOT_TOKEN in the environment."""
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "test-token-123")


@pytest.fixture
def _unset_token(monkeypatch: pytest.MonkeyPatch) -> None:
    """Ensure TELEGRAM_BOT_TOKEN is not in the environment."""
    monkeypatch.delenv("TELEGRAM_BOT_TOKEN", raising=False)


@pytest.fixture
def _set_pipeline_yaml(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Set PIPELINE_YAML to a valid path in the environment."""
    monkeypatch.setenv("PIPELINE_YAML", str(tmp_path / "pipeline.yaml"))


@pytest.fixture
def _unset_pipeline_yaml(monkeypatch: pytest.MonkeyPatch) -> None:
    """Ensure PIPELINE_YAML is not in the environment."""
    monkeypatch.delenv("PIPELINE_YAML", raising=False)


# ── Happy-path tests ──────────────────────────────────────────────


class TestLoadConfigHappyPath:
    """Tests for successful configuration loading."""

    @pytest.mark.usefixtures("_set_token", "_set_pipeline_yaml")
    def test_loads_all_values(self, valid_yaml: Path) -> None:
        cfg = load_config(config_path=valid_yaml)

        assert cfg.telegram_bot_token == "test-token-123"
        assert cfg.allowed_users == [111, 222]
        assert cfg.idle_timeout == 300
        assert cfg.shutdown_message == "Goodbye."

    @pytest.mark.usefixtures("_set_token", "_set_pipeline_yaml")
    def test_defaults_applied(self, minimal_yaml: Path) -> None:
        cfg = load_config(config_path=minimal_yaml)

        assert cfg.idle_timeout == 600
        assert cfg.shutdown_message == (
            "Record the product of this conversation as appropriate "
            "for your role and exit."
        )

    @pytest.mark.usefixtures("_set_token", "_set_pipeline_yaml")
    def test_returns_bot_config_instance(self, valid_yaml: Path) -> None:
        cfg = load_config(config_path=valid_yaml)
        assert isinstance(cfg, BotConfig)

    @pytest.mark.usefixtures("_set_token", "_set_pipeline_yaml")
    def test_pipeline_yaml_stored_as_path(self, valid_yaml: Path, tmp_path: Path) -> None:
        cfg = load_config(config_path=valid_yaml)
        assert isinstance(cfg.pipeline_yaml, Path)
        assert cfg.pipeline_yaml == tmp_path / "pipeline.yaml"


# ── Missing required values ───────────────────────────────────────


class TestMissingRequired:
    """Tests for missing required configuration values."""

    @pytest.mark.usefixtures("_unset_token", "_set_pipeline_yaml")
    def test_missing_token_raises(self, valid_yaml: Path) -> None:
        with pytest.raises(ValueError, match="TELEGRAM_BOT_TOKEN"):
            load_config(config_path=valid_yaml)

    @pytest.mark.usefixtures("_set_token", "_set_pipeline_yaml")
    def test_missing_allowed_users_raises(self, tmp_path: Path) -> None:
        cfg_file = tmp_path / "telegram_bot.yaml"
        cfg_file.write_text("idle_timeout: 600\n")

        with pytest.raises(ValueError, match="allowed_users"):
            load_config(config_path=cfg_file)

    @pytest.mark.usefixtures("_set_token", "_set_pipeline_yaml")
    def test_empty_allowed_users_raises(self, tmp_path: Path) -> None:
        cfg_file = tmp_path / "telegram_bot.yaml"
        cfg_file.write_text("allowed_users: []\n")

        with pytest.raises(ValueError, match="allowed_users"):
            load_config(config_path=cfg_file)

    @pytest.mark.usefixtures("_set_token", "_set_pipeline_yaml")
    def test_missing_yaml_file_raises(self, tmp_path: Path) -> None:
        missing = tmp_path / "nonexistent.yaml"

        with pytest.raises(FileNotFoundError):
            load_config(config_path=missing)

    @pytest.mark.usefixtures("_set_token", "_unset_pipeline_yaml")
    def test_missing_pipeline_yaml_raises(self, valid_yaml: Path) -> None:
        with pytest.raises(ValueError, match="PIPELINE_YAML"):
            load_config(config_path=valid_yaml)

    @pytest.mark.usefixtures("_set_token")
    def test_empty_pipeline_yaml_raises(
        self, valid_yaml: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("PIPELINE_YAML", "")
        with pytest.raises(ValueError, match="PIPELINE_YAML"):
            load_config(config_path=valid_yaml)


# ── Validation edge cases ─────────────────────────────────────────


class TestValidation:
    """Tests for invalid configuration values."""

    @pytest.mark.usefixtures("_set_token", "_set_pipeline_yaml")
    def test_allowed_users_not_ints_raises(self, tmp_path: Path) -> None:
        cfg_file = tmp_path / "telegram_bot.yaml"
        cfg_file.write_text('allowed_users:\n  - "not_an_int"\n')

        with pytest.raises(ValueError, match="allowed_users.*list of integers"):
            load_config(config_path=cfg_file)

    @pytest.mark.usefixtures("_set_token", "_set_pipeline_yaml")
    def test_negative_idle_timeout_raises(self, tmp_path: Path) -> None:
        cfg_file = tmp_path / "telegram_bot.yaml"
        cfg_file.write_text("allowed_users:\n  - 111\nidle_timeout: -1\n")

        with pytest.raises(ValueError, match="idle_timeout"):
            load_config(config_path=cfg_file)

    @pytest.mark.usefixtures("_set_token", "_set_pipeline_yaml")
    def test_empty_shutdown_message_raises(self, tmp_path: Path) -> None:
        cfg_file = tmp_path / "telegram_bot.yaml"
        cfg_file.write_text('allowed_users:\n  - 111\nshutdown_message: "   "\n')

        with pytest.raises(ValueError, match="shutdown_message"):
            load_config(config_path=cfg_file)

    @pytest.mark.usefixtures("_set_token", "_set_pipeline_yaml")
    def test_empty_claude_path_raises(self, tmp_path: Path) -> None:
        cfg_file = tmp_path / "telegram_bot.yaml"
        cfg_file.write_text('allowed_users:\n  - 111\nclaude_path: "   "\n')

        with pytest.raises(ValueError, match="claude_path"):
            load_config(config_path=cfg_file)

    @pytest.mark.usefixtures("_set_token", "_set_pipeline_yaml")
    def test_non_string_claude_path_raises(self, tmp_path: Path) -> None:
        cfg_file = tmp_path / "telegram_bot.yaml"
        cfg_file.write_text("allowed_users:\n  - 111\nclaude_path: 123\n")

        with pytest.raises(ValueError, match="claude_path"):
            load_config(config_path=cfg_file)


# ── claude_path config option ─────────────────────────────────────


class TestClaudePath:
    """Tests for the optional claude_path configuration."""

    @pytest.mark.usefixtures("_set_token", "_set_pipeline_yaml")
    def test_claude_path_default_is_none(self, minimal_yaml: Path) -> None:
        cfg = load_config(config_path=minimal_yaml)
        assert cfg.claude_path is None

    @pytest.mark.usefixtures("_set_token", "_set_pipeline_yaml")
    def test_claude_path_loaded_from_yaml(self, tmp_path: Path) -> None:
        cfg_file = tmp_path / "telegram_bot.yaml"
        cfg_file.write_text(
            'allowed_users:\n  - 111\nclaude_path: "/usr/local/bin/claude"\n'
        )

        cfg = load_config(config_path=cfg_file)
        assert cfg.claude_path == "/usr/local/bin/claude"

    @pytest.mark.usefixtures("_set_token", "_set_pipeline_yaml")
    def test_claude_path_absent_is_none(self, tmp_path: Path) -> None:
        cfg_file = tmp_path / "telegram_bot.yaml"
        cfg_file.write_text("allowed_users:\n  - 111\n")

        cfg = load_config(config_path=cfg_file)
        assert cfg.claude_path is None


# ── Package importability ─────────────────────────────────────────


def test_package_importable() -> None:
    """Verify the telegram_bot package can be imported."""
    import telegram_bot  # noqa: F401
