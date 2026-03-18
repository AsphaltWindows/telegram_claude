"""Agent discovery from pipeline.yaml.

Reads the pipeline configuration and extracts agents with ``type: source``,
enabling the bot to dynamically register Telegram commands at startup.
"""

from __future__ import annotations

from pathlib import Path
from typing import List, Optional, Union

import yaml


# Project root — inherited from the process working directory.
# The launcher script (run_bot.sh) is expected to cd to the project root
# before starting the bot, making Path.cwd() the correct value.
_PROJECT_ROOT = Path.cwd()
_DEFAULT_PIPELINE_PATH = _PROJECT_ROOT / "pipeline.yaml"


def discover_source_agents(
    pipeline_path: Optional[Union[Path, str]] = None,
) -> List[str]:
    """Discover source agents from the pipeline configuration.

    Reads ``pipeline.yaml`` and returns the names of all agents whose
    ``type`` is ``"source"``.  Agents with ``scheduled: false`` are still
    included — the ``scheduled`` flag does not affect discovery.

    Parameters
    ----------
    pipeline_path:
        Optional path to the pipeline YAML file.  Defaults to
        ``pipeline.yaml`` in the project root.

    Returns
    -------
    list[str]
        Agent names where ``type == "source"``.  May be empty if no
        source agents are defined.

    Raises
    ------
    FileNotFoundError
        If the pipeline file does not exist at the resolved path.
    ValueError
        If the file cannot be parsed as YAML or has an unexpected
        structure (e.g. missing ``agents`` key, or ``agents`` is not a list).
    """
    path = Path(pipeline_path) if pipeline_path is not None else _DEFAULT_PIPELINE_PATH

    if not path.exists():
        raise FileNotFoundError(
            f"Pipeline configuration file not found: {path}"
        )

    with open(path, "r", encoding="utf-8") as fh:
        try:
            data = yaml.safe_load(fh)
        except yaml.YAMLError as exc:
            raise ValueError(
                f"Failed to parse pipeline YAML at {path}: {exc}"
            ) from exc

    if data is None or not isinstance(data, dict):
        raise ValueError(
            f"Pipeline file at {path} is empty or not a YAML mapping."
        )

    if "agents" not in data:
        raise ValueError(
            f"Pipeline file at {path} is missing the required 'agents' key."
        )

    agents = data["agents"]
    if not isinstance(agents, list):
        raise ValueError(
            f"'agents' in {path} must be a list, got {type(agents).__name__}."
        )

    return [
        agent["name"]
        for agent in agents
        if isinstance(agent, dict) and agent.get("type") == "source"
    ]
