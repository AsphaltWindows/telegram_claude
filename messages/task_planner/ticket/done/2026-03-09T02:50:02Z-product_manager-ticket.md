# Fix wrong subprocess working directory — use Path.cwd() instead of __file__ path arithmetic

## Metadata
- **From**: product_manager
- **To**: task_planner
- **Type**: ticket
- **Created**: 2026-03-09T02:50:02Z

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

## Design Context

The `_PROJECT_ROOT` variable was computed by counting parent directories from `__file__`, but the code lives at `artifacts/developer/telegram_bot/session.py` (3 levels below project root) while the code only went 2 levels up, landing at `artifacts/developer/`. This caused the Claude subprocess to run with the wrong cwd, breaking all relative file operations. The design now specifies: use `Path.cwd()` (inherited from launcher) or an explicit config value — never `__file__` path arithmetic. See `artifacts/designer/design.md`, "Project Directory" section.
