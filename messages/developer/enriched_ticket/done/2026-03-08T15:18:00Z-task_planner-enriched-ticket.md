# Telegram Bot: Agent Discovery from pipeline.yaml

## Metadata
- **From**: task_planner
- **To**: developer
- **Type**: enriched-ticket
- **Created**: 2026-03-08T15:18:00Z

## Requirements

1. Create `telegram_bot/discovery.py` that reads `pipeline.yaml` from the project root
2. Extract all agents with `type: source` and return their names as a list of strings
3. Agents with `scheduled: false` must still be included (e.g., `operator`)
4. Return value should be a list of agent name strings (e.g., `["operator", "architect", "designer"]`)
5. Raise a clear error if `pipeline.yaml` is not found or cannot be parsed
6. Handle edge case: if no source agents are found, return an empty list (do not error)

## QA Steps

1. With the existing `pipeline.yaml` in the project, run discovery and verify it returns all source agents (`operator`, `architect`, `designer`)
2. Create a test `pipeline.yaml` with a mix of source and non-source agents; verify only source agents are returned
3. Create a test `pipeline.yaml` with a source agent that has `scheduled: false`; verify it is still included
4. Remove `pipeline.yaml` and verify a clear error is raised
5. Create a `pipeline.yaml` with no source agents; verify an empty list is returned

## Technical Context

### Relevant Files

| File | Status | Relevance |
|---|---|---|
| `pipeline.yaml` | Exists | The input file to parse. Contains an `agents` key with a list of agent objects. Each has `name` (str), `type` (str: `source`, `processing`, or `sink`), and optional `scheduled` (bool). Currently has 7 agents, 3 of which are `type: source`: `operator`, `architect`, `designer`. |
| `telegram_bot/discovery.py` | **To create** | The module this ticket implements. |
| `telegram_bot/__init__.py` | **To create** | Package init. A version already exists at `artifacts/developer/telegram_bot/__init__.py` with content `"""Telegram bot integration for Claude agent pipeline."""` — copy or replicate this. |
| `artifacts/designer/design.md` | Exists (read-only) | Design doc. Section "Agent Discovery" confirms: read `pipeline.yaml` at startup, extract `type: source` agents, `scheduled: false` agents are still eligible. Section "File Structure" confirms `discovery.py` belongs in `telegram_bot/`. |

### Patterns and Conventions

- **No existing Python code in project root** — the `telegram_bot/` directory does not exist yet. You are creating the first module. There are no pre-existing Python conventions to follow in this repo.
- **YAML is already used** — `pipeline.yaml` uses standard YAML. Use PyYAML (`import yaml`) for parsing, which is the standard Python YAML library.
- **pipeline.yaml structure** — Top-level key `agents` contains a list of dicts. Each dict has at minimum `name` and `type` keys. The `scheduled` key is optional (only `operator` has it set to `false`; other source agents omit it entirely, which is irrelevant since we include all source agents regardless of `scheduled`).

### Dependencies and Integration Points

- **PyYAML** — The `yaml` module is needed. Ensure it's available (it's a standard dependency, likely already in the environment or add to a future `requirements.txt`).
- **Downstream consumer** — Per the design doc, `bot.py` will call this module at startup to discover valid `/<agent_name>` commands. The function should have a clean, simple interface: take an optional path argument (defaulting to `pipeline.yaml` in the project root) and return `list[str]`.
- **Project root resolution** — The design doc says the bot runs from the project root. For robustness, resolve the path relative to the project root rather than relying on CWD. A reasonable approach: default to `Path(__file__).resolve().parent.parent / "pipeline.yaml"` (since `discovery.py` is at `telegram_bot/discovery.py`, two levels up is the project root).

### Implementation Notes

1. **Create the directory and files first**: `telegram_bot/__init__.py` and `telegram_bot/discovery.py`.

2. **Suggested function signature**:
   ```python
   def discover_source_agents(pipeline_path: Path | str | None = None) -> list[str]:
   ```
   - If `pipeline_path` is None, default to `<project_root>/pipeline.yaml`
   - Returns list of agent name strings where `type == "source"`

3. **Error handling**:
   - `FileNotFoundError` with a clear message if the file doesn't exist
   - `ValueError` (or a custom exception) if YAML parsing fails or the structure is unexpected (e.g., missing `agents` key)
   - Empty list (no error) if `agents` exists but none have `type: source`

4. **Parsing logic is straightforward**:
   ```python
   data = yaml.safe_load(f)
   agents = data.get("agents", [])
   return [a["name"] for a in agents if a.get("type") == "source"]
   ```
   Use `yaml.safe_load` (not `yaml.load`) for safety.

5. **Testing**: Write a simple test script or use pytest. Tests can create temporary YAML files with `tmp_path` fixture. The QA steps map directly to test cases.

## Design Context

Agent discovery enables the bot to dynamically register Telegram commands based on the pipeline configuration, rather than hardcoding agent names. This is used at bot startup. See `artifacts/designer/design.md`, section "Agent Discovery".
