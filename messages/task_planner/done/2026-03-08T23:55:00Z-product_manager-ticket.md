# Create `install_telegram_bot.sh` deployment script

## Metadata
- **From**: product_manager
- **To**: task_planner
- **Type**: ticket
- **Created**: 2026-03-08T23:55:00Z

## Requirements

1. Create `install_telegram_bot.sh` in the project root (next to `pipeline.yaml`). It must be executable (`chmod +x`).

2. **Argument parsing**: Accept `[--force] <target-directory>` — the `--force` flag is optional and may appear before the target directory argument. If no target directory is provided, print usage and exit with error.

3. **Pre-flight check — target directory**: Validate the target directory exists and is a directory. If not, print an error and exit.

4. **Pre-flight check — pipeline.yaml**: Validate `<target>/pipeline.yaml` exists. If not, print an error like `"Error: <target>/pipeline.yaml not found — is this an agent pipeline project?"` and exit.

5. **Pre-flight check — existing files**: If any of `<target>/telegram_bot/`, `<target>/run_bot.sh`, or `<target>/telegram_bot.yaml` already exist AND `--force` was NOT passed, print an error listing which files exist and instruct the user to use `--force` to overwrite. Exit with error. If `--force` IS passed, proceed (overwriting).

6. **Copy Python package**: Copy `artifacts/developer/telegram_bot/` to `<target>/telegram_bot/`, including only `.py` files (recursive). Exclude `__pycache__/`, `.pytest_cache/`, `.pyc` files, and the `tests/` subdirectory. The source path is relative to the install script's own location (i.e. `$SCRIPT_DIR/artifacts/developer/telegram_bot/`).

7. **Generate `run_bot.sh`**: Write a fresh `<target>/run_bot.sh` (do NOT copy the source `run_bot.sh`). The generated version must:
   - Set `BOT_TOKEN="YOUR_TOKEN_HERE"` (placeholder)
   - Set `PIPELINE_YAML="pipeline.yaml"`
   - `cd` to the script's own directory (the project root) — NOT `../../` like the source
   - Source nvm if available (same logic as source)
   - Validate token is not `YOUR_TOKEN_HERE`
   - Resolve `PIPELINE_YAML` to absolute path
   - Validate pipeline YAML exists
   - Export `TELEGRAM_BOT_TOKEN` and `PIPELINE_YAML`
   - Do NOT set or export `PYTHONPATH` — the package is at project root, so `python -m telegram_bot` works directly
   - `exec python -m telegram_bot`
   - Must be executable (`chmod +x`)

8. **Generate `telegram_bot.yaml`**: Write a fresh `<target>/telegram_bot.yaml` with the same structure as the source but with credentials blanked:
   - `allowed_users` list with single placeholder: `- 000000000`
   - `idle_timeout: 600` (same default)
   - `shutdown_message` (same default)
   - `claude_path` commented-out example (same as source)

9. **Dependency installation**: Run `pip install python-telegram-bot pyyaml`. If `pip` is not found (command not available), print an error and exit before copying any files (or after — design doesn't specify order strictly, but failing clearly is required).

10. **Post-install message**: After successful installation, print:
    ```
    Telegram bot installed to /path/to/target/project

    Next steps:
      1. Edit run_bot.sh and set your BOT_TOKEN
      2. Edit telegram_bot.yaml and set your allowed_users (Telegram user IDs)
      3. Run: ./run_bot.sh
    ```

11. Use `set -euo pipefail` at the top. Use `#!/usr/bin/env bash` shebang.

## QA Steps

1. **No-args invocation**: Run `./install_telegram_bot.sh` with no arguments. Verify it prints usage and exits non-zero.

2. **Non-existent target**: Run `./install_telegram_bot.sh /tmp/nonexistent_dir_xyz`. Verify error message and non-zero exit.

3. **Target without pipeline.yaml**: Create an empty temp directory, run the script targeting it. Verify it errors about missing `pipeline.yaml`.

4. **Successful install**: Create a temp directory with an empty `pipeline.yaml`, run the script. Verify:
   - `<target>/telegram_bot/` exists with `.py` files (check at least `__init__.py`, `bot.py`, `config.py`, `session.py`, `discovery.py`, `__main__.py`)
   - No `tests/` directory inside `<target>/telegram_bot/`
   - No `__pycache__` or `.pyc` files
   - `<target>/run_bot.sh` exists, is executable, contains `YOUR_TOKEN_HERE`, does NOT contain `PYTHONPATH`, does NOT contain `../../`
   - `<target>/telegram_bot.yaml` exists, contains `000000000`, does NOT contain real user IDs

5. **Overwrite without --force**: After a successful install, run the script again on the same target WITHOUT `--force`. Verify it errors and lists existing files.

6. **Overwrite with --force**: Run with `--force` on the same target. Verify it succeeds and files are overwritten.

7. **Generated run_bot.sh correctness**: Inspect the generated `run_bot.sh` — confirm it has the nvm sourcing block, token validation, PIPELINE_YAML resolution, and `exec python -m telegram_bot`.

8. **Generated telegram_bot.yaml correctness**: Inspect the generated config — confirm `idle_timeout`, `shutdown_message`, and commented `claude_path` are present with correct defaults.

## Design Context

This script enables deploying the Telegram bot integration to any project that has an agent pipeline. The key design decision is that `run_bot.sh` and `telegram_bot.yaml` are generated fresh rather than copied-and-sed'd, because the installed layout (files at project root) differs from the source layout (files nested under `artifacts/developer/`). This eliminates the `PYTHONPATH` hack and `../../` path navigation.

See `artifacts/designer/install-script-design.md` for full design specification.
