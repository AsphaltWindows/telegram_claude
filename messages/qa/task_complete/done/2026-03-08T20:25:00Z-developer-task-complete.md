# Use PIPELINE_YAML env var for agent discovery instead of hardcoded path

## Metadata
- **From**: developer
- **To**: qa
- **Type**: task-complete
- **Created**: 2026-03-08T20:25:00Z

## Summary of Changes

Updated the bot to read the `PIPELINE_YAML` environment variable for locating the pipeline configuration file, replacing the previously hardcoded default path. The config module now requires this env var at startup, stores it as a `Path` on `BotConfig`, and `bot.py` passes it explicitly to `discover_source_agents()`.

## Files Changed

- **`artifacts/developer/telegram_bot/config.py`** — Added `pipeline_yaml: Path` field to `BotConfig` dataclass; added env var reading and validation in `load_config()` that raises `ValueError` if `PIPELINE_YAML` is not set; included `pipeline_yaml` in the returned `BotConfig`.
- **`artifacts/developer/telegram_bot/bot.py`** — Changed `build_application()` to pass `config.pipeline_yaml` to `discover_source_agents(pipeline_path=...)` instead of calling it with no arguments.
- **`artifacts/developer/tests/test_config.py`** — Added `_set_pipeline_yaml` and `_unset_pipeline_yaml` fixtures; updated all existing tests to include `_set_pipeline_yaml` fixture; added `test_pipeline_yaml_stored_as_path`, `test_missing_pipeline_yaml_raises`, and `test_empty_pipeline_yaml_raises` tests.

## Requirements Addressed

1. **PIPELINE_YAML env var in config.py** — Implemented. `load_config()` reads `PIPELINE_YAML` from env, raises `ValueError` with clear message if not set.
2. **discovery.py uses path from config** — Implemented via `bot.py` passing `config.pipeline_yaml` to `discover_source_agents()`. No changes needed in `discovery.py` itself since it already accepts a `pipeline_path` parameter.
3. **Clear error on missing/unparseable file** — Already handled by `discovery.py`'s existing error handling (includes path in all error messages). The new config validation catches missing env var before discovery is called.
4. **Amendment to existing tickets** — Both files were already implemented; changes were applied as amendments.

## QA Steps

1. Set `PIPELINE_YAML` to a valid pipeline.yaml path — verify the bot reads and discovers source agents from it.
2. Set `PIPELINE_YAML` to a nonexistent path — verify the bot fails at startup with a clear error message including the bad path.
3. Unset `PIPELINE_YAML` entirely — verify the bot fails at startup with an error indicating the env var is required.
4. Set `PIPELINE_YAML` to a file that exists but is not valid YAML — verify a parse error is raised with the path in the message.

## Test Coverage

All tests pass (14/14). New tests added:

- `test_pipeline_yaml_stored_as_path` — Verifies the config stores the env var value as a `Path` instance.
- `test_missing_pipeline_yaml_raises` — Verifies `ValueError` is raised with "PIPELINE_YAML" in message when env var is unset.
- `test_empty_pipeline_yaml_raises` — Verifies `ValueError` is raised when env var is set to empty string.

All existing tests updated to set `PIPELINE_YAML` in the environment so they continue to pass.

Run tests with: `cd artifacts/developer && python -m pytest tests/test_config.py -v`

## Notes

- `discovery.py` required no changes — it already accepts `pipeline_path` as a parameter and handles file-not-found and parse errors with the path in the message. The `_DEFAULT_PIPELINE_PATH` constant is preserved for backward compatibility and testability.
- The `PIPELINE_YAML` validation in config does not check file existence — that responsibility stays with `discovery.py`, which already provides good error messages including the path.
