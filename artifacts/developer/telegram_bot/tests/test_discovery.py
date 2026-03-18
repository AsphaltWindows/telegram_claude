"""Tests for telegram_bot.discovery module."""

from __future__ import annotations

import pytest
import yaml

from telegram_bot.discovery import discover_source_agents


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _write_pipeline(tmp_path, agents_list):
    """Write a pipeline.yaml with the given agents list and return its path."""
    path = tmp_path / "pipeline.yaml"
    path.write_text(yaml.dump({"agents": agents_list}), encoding="utf-8")
    return path


# ---------------------------------------------------------------------------
# Happy-path tests
# ---------------------------------------------------------------------------

class TestDiscoverSourceAgents:
    """Core discovery behaviour."""

    def test_returns_source_agents_only(self, tmp_path):
        agents = [
            {"name": "alpha", "type": "source"},
            {"name": "beta", "type": "processing"},
            {"name": "gamma", "type": "sink"},
            {"name": "delta", "type": "source"},
        ]
        path = _write_pipeline(tmp_path, agents)
        result = discover_source_agents(path)
        assert result == ["alpha", "delta"]

    def test_includes_scheduled_false_agents(self, tmp_path):
        agents = [
            {"name": "operator", "type": "source", "scheduled": False},
            {"name": "designer", "type": "source"},
            {"name": "worker", "type": "processing"},
        ]
        path = _write_pipeline(tmp_path, agents)
        result = discover_source_agents(path)
        assert result == ["operator", "designer"]

    def test_returns_empty_list_when_no_source_agents(self, tmp_path):
        agents = [
            {"name": "worker", "type": "processing"},
            {"name": "output", "type": "sink"},
        ]
        path = _write_pipeline(tmp_path, agents)
        result = discover_source_agents(path)
        assert result == []

    def test_returns_empty_list_when_agents_list_is_empty(self, tmp_path):
        path = _write_pipeline(tmp_path, [])
        result = discover_source_agents(path)
        assert result == []

    def test_accepts_string_path(self, tmp_path):
        agents = [{"name": "bot", "type": "source"}]
        path = _write_pipeline(tmp_path, agents)
        result = discover_source_agents(str(path))
        assert result == ["bot"]

    def test_with_real_pipeline_yaml(self):
        """Verify discovery against the actual project pipeline.yaml."""
        from telegram_bot.discovery import _DEFAULT_PIPELINE_PATH

        # Skip if not running from the project root context
        if not _DEFAULT_PIPELINE_PATH.exists():
            pytest.skip("pipeline.yaml not found at default location")

        result = discover_source_agents(_DEFAULT_PIPELINE_PATH)
        assert "operator" in result
        assert "architect" in result
        assert "designer" in result
        # Ensure non-source agents are excluded
        assert "product_manager" not in result
        assert "developer" not in result
        assert "qa" not in result


# ---------------------------------------------------------------------------
# Error-handling tests
# ---------------------------------------------------------------------------

class TestDiscoverSourceAgentsErrors:
    """Error conditions and edge cases."""

    def test_raises_file_not_found_when_missing(self, tmp_path):
        missing = tmp_path / "nonexistent.yaml"
        with pytest.raises(FileNotFoundError, match="not found"):
            discover_source_agents(missing)

    def test_raises_value_error_on_invalid_yaml(self, tmp_path):
        path = tmp_path / "pipeline.yaml"
        path.write_text("{{invalid yaml: [", encoding="utf-8")
        with pytest.raises(ValueError, match="Failed to parse"):
            discover_source_agents(path)

    def test_raises_value_error_when_empty_file(self, tmp_path):
        path = tmp_path / "pipeline.yaml"
        path.write_text("", encoding="utf-8")
        with pytest.raises(ValueError, match="empty"):
            discover_source_agents(path)

    def test_raises_value_error_when_agents_key_missing(self, tmp_path):
        path = tmp_path / "pipeline.yaml"
        path.write_text(yaml.dump({"other_key": []}), encoding="utf-8")
        with pytest.raises(ValueError, match="missing the required 'agents' key"):
            discover_source_agents(path)

    def test_raises_value_error_when_agents_is_not_a_list(self, tmp_path):
        path = tmp_path / "pipeline.yaml"
        path.write_text(yaml.dump({"agents": "not-a-list"}), encoding="utf-8")
        with pytest.raises(ValueError, match="must be a list"):
            discover_source_agents(path)

    def test_skips_malformed_agent_entries(self, tmp_path):
        """Non-dict entries in the agents list are silently skipped."""
        agents = [
            {"name": "good", "type": "source"},
            "just-a-string",
            42,
            None,
            {"name": "also_good", "type": "source"},
        ]
        path = _write_pipeline(tmp_path, agents)
        result = discover_source_agents(path)
        assert result == ["good", "also_good"]
