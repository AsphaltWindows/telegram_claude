# Fix wrong subprocess working directory — use Path.cwd() instead of __file__ path arithmetic

## Metadata
- **From**: developer
- **To**: qa
- **Type**: task-complete
- **Created**: 2026-03-09T03:10:00Z

## Summary of Changes

Replaced the fragile `Path(__file__).resolve().parent.parent` computation of `_PROJECT_ROOT` with `Path.cwd()` in all three modules that defined it. Added a configurable `project_root` option to `BotConfig` that takes precedence over `Path.cwd()` when set. Wired the config value through `bot.py` to `SessionManager`.

## Files Changed

- `artifacts/developer/telegram_bot/session.py` — Changed `_PROJECT_ROOT` from `Path(__file__).resolve().parent.parent` to `Path.cwd()`. Updated comment.
- `artifacts/developer/telegram_bot/config.py` — Changed `_PROJECT_ROOT` to `Path.cwd()`. Added `project_root: Optional[Path] = None` field to `BotConfig`. Added parsing/validation of `project_root` in `load_config()`.
- `artifacts/developer/telegram_bot/discovery.py` — Changed `_PROJECT_ROOT` to `Path.cwd()`. Updated comment.
- `artifacts/developer/telegram_bot/bot.py` — Added `project_root=config.project_root` to the `SessionManager` constructor call in `build_application()`.
- `artifacts/developer/telegram_bot/tests/test_project_root.py` — New test file with 13 tests covering all changes.

## Requirements Addressed

1. **Replace `_PROJECT_ROOT` with `Path.cwd()`** — Done in all three files (`session.py`, `config.py`, `discovery.py`).
2. **Support configurable `project_root` from config** — Added `project_root` field to `BotConfig`, parsed from YAML with directory validation, wired through `bot.py` to `SessionManager`. Falls back to `Path.cwd()` when not set.
3. **Do NOT use `__file__` parent-counting** — Removed from all three files.
4. **`cwd` parameter in `asyncio.create_subprocess_exec()` uses corrected value** — `SessionManager` already used `self._project_root` which falls back to the module-level `_PROJECT_ROOT`, now correctly set to `Path.cwd()`.
5. **Subprocess runs in actual project root** — Verified via tests that the `cwd` kwarg matches the configured/default project root.

## QA Steps

1. Start the bot via `run_bot.sh` and start a session.
2. Verify (via logs or process inspection) that the Claude subprocess's working directory is the project root, not `artifacts/developer/`.
3. Within a session, ask the agent to perform a file operation that uses a relative path (e.g., reading `pipeline.yaml` or writing to `messages/`). Verify the operation succeeds and targets the correct file at the project root.
4. Verify the bot still starts correctly and sessions function normally after the change.
5. If the configurable `project_root` option was implemented, test with an explicit value and verify it takes precedence over `Path.cwd()`.

## Test Coverage

13 new tests in `test_project_root.py`:

- **TestProjectRootIsCwd** (4 tests) — Verifies all three modules' `_PROJECT_ROOT` equals `Path.cwd()`, and proves via module reload in a temp directory that it follows cwd, not `__file__`.
- **TestSessionManagerProjectRoot** (3 tests) — Default is cwd, explicit overrides default, subprocess `cwd` kwarg uses the project root.
- **TestConfigProjectRoot** (4 tests) — Default is None, reads from YAML, rejects nonexistent directory, rejects empty string.
- **TestBotProjectRootWiring** (2 tests) — `build_application` passes `project_root` to `SessionManager` (both when set and when None).

Run: `python -m pytest artifacts/developer/telegram_bot/tests/test_project_root.py -v`

All 74 tests pass (61 existing + 13 new).

## Notes

- The `SessionManager.__init__` already accepted an optional `project_root` parameter and fell back to the module-level `_PROJECT_ROOT`. No changes were needed in `SessionManager` itself beyond fixing the module-level constant.
- The `_PROJECT_ROOT` in `discovery.py` is largely dead code in normal operation (the bot always passes an explicit `pipeline_path`), but was fixed for consistency and for the default-path fallback case.
- The misleading comments about `__file__` parent-counting have been replaced with accurate comments about `Path.cwd()` and the launcher script expectation.
