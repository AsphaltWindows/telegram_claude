# QA Report: Use PIPELINE_YAML env var for agent discovery instead of hardcoded path

## Metadata
- **Ticket**: Use PIPELINE_YAML env var for agent discovery instead of hardcoded path
- **Tested**: 2026-03-08T20:30:00Z
- **Result**: PASS

## Steps

### Step 1: Set PIPELINE_YAML to a valid pipeline.yaml path — verify the bot reads and discovers source agents from it.
- **Result**: PASS
- **Notes**: Code review confirms `bot.py` line 298 passes `config.pipeline_yaml` to `discover_source_agents(pipeline_path=...)`. The config module reads `PIPELINE_YAML` from the environment (line 73-78) and stores it as a `Path`. Test `test_pipeline_yaml_stored_as_path` validates this end-to-end.

### Step 2: Set PIPELINE_YAML to a nonexistent path — verify the bot fails at startup with a clear error message including the bad path.
- **Result**: PASS
- **Notes**: `discovery.py` line 52-55 raises `FileNotFoundError` with the path in the message: `"Pipeline configuration file not found: {path}"`. The path flows from config through bot.py to discovery.py correctly.

### Step 3: Unset PIPELINE_YAML entirely — verify the bot fails at startup with an error indicating the env var is required.
- **Result**: PASS
- **Notes**: `config.py` line 73-77 checks `os.environ.get("PIPELINE_YAML")` and raises `ValueError("PIPELINE_YAML environment variable is required but not set.")` when missing. Test `test_missing_pipeline_yaml_raises` validates this.

### Step 4: Set PIPELINE_YAML to a file that exists but is not valid YAML — verify a parse error is raised with the path in the message.
- **Result**: PASS
- **Notes**: `discovery.py` line 58-63 catches `yaml.YAMLError` and raises `ValueError(f"Failed to parse pipeline YAML at {path}: {exc}")`. The path is included in the error message. This behavior was pre-existing and unchanged.

## Summary

All QA steps pass. The implementation is clean and well-structured:

- `config.py` validates the `PIPELINE_YAML` env var early (before YAML config loading), with a clear error message.
- `bot.py` correctly passes `config.pipeline_yaml` to `discover_source_agents()`.
- `discovery.py` required no changes — it already accepted a `pipeline_path` parameter and had good error handling.
- All 14 tests pass, including 3 new tests covering the `PIPELINE_YAML` env var behavior.
- All existing tests were properly updated with the `_set_pipeline_yaml` fixture to avoid regressions.
- The empty-string case is handled correctly (treated the same as unset).
