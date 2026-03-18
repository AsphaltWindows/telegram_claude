# Fix wrong subprocess working directory — use Path.cwd() instead of __file__ path arithmetic

## Metadata
- **From**: task_planner
- **To**: developer
- **Type**: enriched-ticket
- **Created**: 2026-03-09T02:55:00Z

## Requirements

1. In `artifacts/developer/telegram_bot/session.py`, replace the `_PROJECT_ROOT` computation (line 24, currently `Path(__file__).resolve().parent.parent`) with `Path.cwd()`, which inherits the correct working directory from the `run_bot.sh` launcher script.
2. Alternatively, support a configurable `project_root` value from config, falling back to `Path.cwd()` if not set. Priority order: explicit config value > `Path.cwd()`.
3. Do NOT use `__file__` parent-counting as the primary or fallback method — this is fragile and breaks when the code is relocated.
4. The `cwd` parameter passed to `asyncio.create_subprocess_exec()` in `SessionManager` must use the corrected project root value.
5. After the fix, the `claude --agent` subprocess must run with its working directory set to the actual project root (`/home/iv/dev/telegram_claude/` or equivalent), not `artifacts/developer/`.

## QA Steps

1. Start the bot via `run_bot.sh` and start a session.
2. Verify (via logs or process inspection) that the Claude subprocess's working directory is the project root, not `artifacts/developer/`.
3. Within a session, ask the agent to perform a file operation that uses a relative path (e.g., reading `pipeline.yaml` or writing to `messages/`). Verify the operation succeeds and targets the correct file at the project root.
4. Verify the bot still starts correctly and sessions function normally after the change.
5. If the configurable `project_root` option was implemented, test with an explicit value and verify it takes precedence over `Path.cwd()`.

## Technical Context

### Relevant Files

| File | Role | Action |
|---|---|---|
| `artifacts/developer/telegram_bot/session.py` | **Primary target.** Defines `_PROJECT_ROOT` on line 24 and uses it as `cwd` for subprocess in `SessionManager.__init__` (line 494) and `start_session` (line 552). | **Modify** — replace `_PROJECT_ROOT` computation. |
| `artifacts/developer/telegram_bot/config.py` | Config loader. Also has its own `_PROJECT_ROOT` on line 18 used to locate `telegram_bot.yaml`. | **Modify** — replace `_PROJECT_ROOT` computation; optionally add `project_root` field to `BotConfig`. |
| `artifacts/developer/telegram_bot/discovery.py` | Agent discovery. Has its own `_PROJECT_ROOT` on line 17 used to build `_DEFAULT_PIPELINE_PATH`. | **Modify** — replace `_PROJECT_ROOT` computation. |
| `artifacts/developer/telegram_bot/bot.py` | Wires config, discovery, and SessionManager together in `build_application()`. Currently does NOT pass `project_root` to `SessionManager` (line 388-392). | **Modify** — if adding `project_root` to `BotConfig`, pass it through to `SessionManager`. |
| `artifacts/designer/design.md` | Design spec — "Project Directory" section (lines 206-214) documents the intended approach. | **Read only** — reference for correct behavior. |

### Patterns and Conventions

- **Module-level constants** use `_UPPER_SNAKE_CASE` with leading underscore (private).
- **Dataclass config** — `BotConfig` in `config.py` is a `@dataclass` with typed fields. If adding `project_root`, follow the same pattern: `project_root: Optional[Path] = None`.
- **Optional config fields** in `config.py` follow the pattern: read from `data.get("key")`, validate type if present, default to `None` in the dataclass.
- **SessionManager** already accepts `project_root: Optional[Path] = None` in its `__init__` (line 489). It falls back to the module-level `_PROJECT_ROOT` (line 494: `self._project_root = project_root or _PROJECT_ROOT`). So once `_PROJECT_ROOT` is fixed, the fallback also becomes correct.
- `discovery.py`'s `_DEFAULT_PIPELINE_PATH` is only used when no explicit path is given, and in practice the bot always passes an explicit `pipeline_path` from `config.pipeline_yaml` (set from `PIPELINE_YAML` env var). So the `_PROJECT_ROOT` in discovery.py is largely dead code in normal operation, but should still be fixed for consistency and for the default-path fallback case.
- `config.py`'s `_PROJECT_ROOT` is used to locate `telegram_bot.yaml` as `_CONFIG_FILE = _PROJECT_ROOT / "telegram_bot.yaml"`. In practice `load_config()` uses `_CONFIG_FILE` as the default (line 82: `path = config_path or _CONFIG_FILE`). This path WILL break if not fixed — `telegram_bot.yaml` lives at the project root, not at `artifacts/developer/`.

### Dependencies and Integration Points

- **`bot.py:build_application()`** (line 388-392) creates `SessionManager` without passing `project_root`. If adding the configurable option, this is where to wire `config.project_root` → `SessionManager(project_root=...)`.
- **`bot.py:main()`** calls `load_config()` first, then `build_application(config=config)`. No changes needed here.
- **`__main__.py`** just calls `main()` — no changes needed.
- **`run_bot.sh`** (not yet created per design, but referenced) is expected to `cd` to the project root before running `python -m telegram_bot`, making `Path.cwd()` correct.

### Implementation Notes

1. **Three files need the same fix.** All three modules (`session.py`, `config.py`, `discovery.py`) have identical `_PROJECT_ROOT = Path(__file__).resolve().parent.parent` lines. Replace all three with `_PROJECT_ROOT = Path.cwd()`.

2. **Minimal viable fix** (if skipping the configurable option): Just change the three `_PROJECT_ROOT` lines. The `SessionManager` already falls back to `_PROJECT_ROOT` when no explicit `project_root` is passed, so the subprocess `cwd` will automatically use the corrected value. No other wiring changes needed.

3. **If adding configurable `project_root` to `BotConfig`:**
   - Add `project_root: Optional[Path] = None` to the `BotConfig` dataclass.
   - In `load_config()`, read `data.get("project_root")`, convert to `Path` if present, validate it's a directory.
   - In `bot.py:build_application()`, pass `project_root=config.project_root` to the `SessionManager` constructor.
   - The `SessionManager` already supports this parameter — no changes needed there beyond fixing the fallback `_PROJECT_ROOT`.

4. **Update comments.** Remove the misleading comments like `# Project root is two levels up from this file:` and `# artifacts/developer/telegram_bot/session.py -> artifacts/developer/` from all three files. Replace with something like `# Project root — inherited from the process working directory.`

5. **Order of changes:** Fix `session.py` first (the primary target with the subprocess `cwd`), then `config.py` (the config file path), then `discovery.py` (the pipeline path default), then optionally wire through `bot.py`.

6. **Testing note:** The existing test directory at `artifacts/developer/telegram_bot/tests/` may have tests that mock or reference `_PROJECT_ROOT`. Check for imports or patches of `_PROJECT_ROOT` before finalizing changes.

## Design Context

The `_PROJECT_ROOT` variable was computed by counting parent directories from `__file__`, but the code lives at `artifacts/developer/telegram_bot/session.py` (3 levels below project root) while the code only went 2 levels up, landing at `artifacts/developer/`. This caused the Claude subprocess to run with the wrong cwd, breaking all relative file operations. The design now specifies: use `Path.cwd()` (inherited from launcher) or an explicit config value — never `__file__` path arithmetic. See `artifacts/designer/design.md`, "Project Directory" section.
