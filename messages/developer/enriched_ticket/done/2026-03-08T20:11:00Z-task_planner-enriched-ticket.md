# Use PIPELINE_YAML env var for agent discovery instead of hardcoded path

## Metadata
- **From**: task_planner
- **To**: developer
- **Type**: enriched-ticket
- **Created**: 2026-03-08T20:11:00Z

## Requirements

1. In `telegram_bot/config.py`, read the `PIPELINE_YAML` environment variable. It is required — the bot must raise a clear error at startup if it is not set.
2. In `telegram_bot/discovery.py`, use the path from `PIPELINE_YAML` (via config) to locate and read the pipeline config file, instead of assuming a hardcoded `pipeline.yaml` path.
3. If the file at the `PIPELINE_YAML` path does not exist or cannot be parsed, raise a clear error with the path included in the message.
4. This is an amendment to the scope of existing tickets (Ticket 1: config.py, Ticket 2: discovery.py). If those tickets have not yet been implemented, incorporate these requirements into their implementation. If already implemented, update accordingly.

## QA Steps

1. Set `PIPELINE_YAML` to a valid pipeline.yaml path — verify the bot reads and discovers source agents from it.
2. Set `PIPELINE_YAML` to a nonexistent path — verify the bot fails at startup with a clear error message including the bad path.
3. Unset `PIPELINE_YAML` entirely — verify the bot fails at startup with an error indicating the env var is required.
4. Set `PIPELINE_YAML` to a file that exists but is not valid YAML — verify a parse error is raised with the path in the message.

## Technical Context

### Relevant Files

- **`artifacts/developer/telegram_bot/config.py`** — Already implemented. Currently reads `TELEGRAM_BOT_TOKEN` from env and loads `telegram_bot.yaml` for bot settings. **Needs a new field** `pipeline_yaml: Path` on `BotConfig` and logic in `load_config()` to read the `PIPELINE_YAML` env var, validate it, and include it in the returned config object.
- **`artifacts/developer/telegram_bot/discovery.py`** — Already implemented. Currently has `_DEFAULT_PIPELINE_PATH` as a fallback and accepts an optional `pipeline_path` parameter. **Needs updating** so that when called without an argument, it reads from the `PIPELINE_YAML` env var (or better: `bot.py` should pass the path from config).
- **`artifacts/developer/telegram_bot/bot.py`** — `build_application()` on line 298 calls `discover_source_agents()` with no arguments. **Needs updating** to pass `config.pipeline_yaml` to `discover_source_agents()`.
- **`artifacts/developer/tests/test_config.py`** — Existing tests for config. **Needs new tests** for the `PIPELINE_YAML` env var requirement.
- **`artifacts/developer/telegram_bot/tests/test_discovery.py`** — Existing tests for discovery. May need minor updates if the function signature or default behavior changes.

### Patterns and Conventions

- **Config pattern**: Environment variables are read in `load_config()` using `os.environ.get()`. Required vars raise `ValueError` if missing. Follow this same pattern for `PIPELINE_YAML`.
- **BotConfig dataclass**: All config values are fields on the `BotConfig` dataclass. Add `pipeline_yaml: Path` as a required field.
- **Discovery function signature**: `discover_source_agents()` already accepts an optional `pipeline_path` parameter. Keep this — the change is that `bot.py` will now always pass it explicitly from config, rather than relying on the internal default.
- **Error messages**: Include the variable name or file path in error messages (e.g., `"PIPELINE_YAML environment variable is required but not set."`).
- **Test style**: Tests use `pytest`, `tmp_path` fixture, `monkeypatch` for env vars, grouped in classes by behavior category.

### Dependencies and Integration Points

- **`run_bot.sh`** (companion ticket) — The launcher script is responsible for setting `PIPELINE_YAML` as an absolute path in the environment before starting Python. This ticket's code can assume the env var contains an absolute path, but should still handle the case where it's not set.
- **`bot.py` → `config.py` → `discovery.py`** — The data flow is: `load_config()` reads `PIPELINE_YAML` from env → stores it in `BotConfig.pipeline_yaml` → `build_application()` passes `config.pipeline_yaml` to `discover_source_agents(pipeline_path=...)`.
- **`_DEFAULT_PIPELINE_PATH` in `discovery.py`** — Can be kept as a fallback or removed. Since the requirement says `PIPELINE_YAML` is required, the default is less important now. Recommend keeping the parameter optional on `discover_source_agents()` for testability (tests pass explicit paths), but removing `_DEFAULT_PIPELINE_PATH` as a default-if-env-not-set fallback.

### Implementation Notes

1. **`config.py` changes**:
   - Add `pipeline_yaml: Path` field to `BotConfig` (no default — it's required).
   - In `load_config()`, after reading `TELEGRAM_BOT_TOKEN`, read `PIPELINE_YAML` from env:
     ```python
     pipeline_yaml_str = os.environ.get("PIPELINE_YAML")
     if not pipeline_yaml_str:
         raise ValueError("PIPELINE_YAML environment variable is required but not set.")
     pipeline_yaml = Path(pipeline_yaml_str)
     ```
   - Include `pipeline_yaml=pipeline_yaml` in the `BotConfig(...)` constructor call.
   - No need to check file existence here — `discovery.py` already does that with a good error message.

2. **`bot.py` changes**:
   - In `build_application()`, change line 298 from:
     ```python
     agents = discover_source_agents()
     ```
     to:
     ```python
     agents = discover_source_agents(pipeline_path=config.pipeline_yaml)
     ```

3. **`discovery.py` changes**:
   - Minimal changes needed. The function already accepts `pipeline_path` and handles missing files / parse errors with path in the message. The `_DEFAULT_PIPELINE_PATH` constant can remain for backward compatibility but won't be exercised in production since `bot.py` will always pass the path.

4. **Test updates for `test_config.py`**:
   - Add a `_set_pipeline_yaml` fixture using `monkeypatch.setenv("PIPELINE_YAML", str(some_path))`.
   - Update existing `_set_token` fixture usage — tests that call `load_config()` will now also need `PIPELINE_YAML` set.
   - Add test: missing `PIPELINE_YAML` raises `ValueError`.
   - Add test: `PIPELINE_YAML` value is stored as `Path` on `BotConfig`.

5. **Ordering**: Implement `config.py` changes first, then `bot.py`, then update tests. `discovery.py` needs no changes if you only pass the path from `bot.py`.

## Design Context

The `PIPELINE_YAML` environment variable replaces the previously hardcoded `pipeline.yaml` reference in agent discovery. It is exported by `run_bot.sh` (see companion ticket). See `artifacts/designer/design.md`, "Configuration > Environment Variables" table and "Agent Discovery" section.
