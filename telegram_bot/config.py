"""Configuration loading for the Telegram bot.

Loads settings from environment variables and telegram_bot.yaml.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

import yaml


# Project root — inherited from the process working directory.
# The launcher script (run_bot.sh) is expected to cd to the project root
# before starting the bot, making Path.cwd() the correct value.
_PROJECT_ROOT = Path.cwd()
_CONFIG_FILE = _PROJECT_ROOT / "telegram_bot.yaml"

_DEFAULT_IDLE_TIMEOUT = 600
_DEFAULT_SHUTDOWN_MESSAGE = (
    "Record the product of this conversation as appropriate for your role and exit."
)


@dataclass
class BotConfig:
    """Typed configuration for the Telegram bot."""

    telegram_bot_token: str
    pipeline_yaml: Path
    allowed_users: List[int]
    idle_timeout: int = _DEFAULT_IDLE_TIMEOUT
    shutdown_message: str = _DEFAULT_SHUTDOWN_MESSAGE
    claude_path: Optional[str] = None
    project_root: Optional[Path] = None


def load_config(
    *,
    config_path: Optional[Path] = None,
) -> BotConfig:
    """Load and validate bot configuration.

    Reads ``TELEGRAM_BOT_TOKEN`` from the environment and all other
    settings from ``telegram_bot.yaml`` (or the *config_path* override).

    Parameters
    ----------
    config_path:
        Optional override for the YAML config file location.
        Defaults to ``telegram_bot.yaml`` in the project root.

    Returns
    -------
    BotConfig
        A validated configuration object.

    Raises
    ------
    ValueError
        If a required configuration value is missing or invalid.
    FileNotFoundError
        If the YAML configuration file does not exist.
    """
    # --- Telegram bot token (from environment) ---
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    if not token:
        raise ValueError(
            "TELEGRAM_BOT_TOKEN environment variable is required but not set."
        )

    # --- Pipeline YAML path (from environment) ---
    pipeline_yaml_str = os.environ.get("PIPELINE_YAML")
    if not pipeline_yaml_str:
        raise ValueError(
            "PIPELINE_YAML environment variable is required but not set."
        )
    pipeline_yaml = Path(pipeline_yaml_str)

    # --- YAML config file ---
    path = config_path or _CONFIG_FILE
    if not path.exists():
        raise FileNotFoundError(f"Configuration file not found: {path}")

    with open(path, "r", encoding="utf-8") as fh:
        data = yaml.safe_load(fh) or {}

    # --- allowed_users (required) ---
    allowed_users = data.get("allowed_users")
    if not allowed_users:
        raise ValueError(
            "allowed_users is required in telegram_bot.yaml and must be a "
            "non-empty list of integer Telegram user IDs."
        )
    if not isinstance(allowed_users, list) or not all(
        isinstance(uid, int) for uid in allowed_users
    ):
        raise ValueError(
            "allowed_users must be a list of integers in telegram_bot.yaml."
        )

    # --- optional fields with defaults ---
    idle_timeout = data.get("idle_timeout", _DEFAULT_IDLE_TIMEOUT)
    if not isinstance(idle_timeout, int) or idle_timeout <= 0:
        raise ValueError("idle_timeout must be a positive integer.")

    shutdown_message = data.get("shutdown_message", _DEFAULT_SHUTDOWN_MESSAGE)
    if not isinstance(shutdown_message, str) or not shutdown_message.strip():
        raise ValueError("shutdown_message must be a non-empty string.")

    claude_path = data.get("claude_path")
    if claude_path is not None:
        if not isinstance(claude_path, str) or not claude_path.strip():
            raise ValueError("claude_path must be a non-empty string if set.")

    project_root: Optional[Path] = None
    raw_project_root = data.get("project_root")
    if raw_project_root is not None:
        if not isinstance(raw_project_root, str) or not raw_project_root.strip():
            raise ValueError("project_root must be a non-empty string if set.")
        project_root = Path(raw_project_root)
        if not project_root.is_dir():
            raise ValueError(
                f"project_root '{project_root}' is not an existing directory."
            )

    return BotConfig(
        telegram_bot_token=token,
        pipeline_yaml=pipeline_yaml,
        allowed_users=allowed_users,
        idle_timeout=idle_timeout,
        shutdown_message=shutdown_message,
        claude_path=claude_path,
        project_root=project_root,
    )
