# Create `install_telegram_bot.sh` deployment script

## Metadata
- **From**: task_planner
- **To**: developer
- **Type**: enriched-ticket
- **Created**: 2026-03-08T23:58:00Z

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

## Technical Context

### Relevant Files

| File | Purpose |
|------|---------|
| `install_telegram_bot.sh` (project root) | **The file to rewrite.** An existing v1 already exists — it uses copy+sed approach. Must be replaced entirely with the generate-fresh approach. |
| `artifacts/developer/run_bot.sh` | Source `run_bot.sh` — use as reference for the nvm sourcing block, token validation, PIPELINE_YAML resolution logic, and exec command. Do NOT copy this file; generate a new one. |
| `artifacts/developer/telegram_bot.yaml` | Source config — use as reference for field names, defaults, and comment text. Contains real user ID `106830816` that must NOT appear in generated output. |
| `artifacts/developer/telegram_bot/__init__.py` | Package init (to be copied) |
| `artifacts/developer/telegram_bot/__main__.py` | Entry point (to be copied) |
| `artifacts/developer/telegram_bot/bot.py` | Main bot logic (to be copied) |
| `artifacts/developer/telegram_bot/config.py` | Configuration loader (to be copied) |
| `artifacts/developer/telegram_bot/session.py` | Session management (to be copied) |
| `artifacts/developer/telegram_bot/discovery.py` | Agent discovery (to be copied) |
| `artifacts/developer/telegram_bot/tests/` | Test directory — must be EXCLUDED from copy |
| `artifacts/developer/telegram_bot/__pycache__/` | Cache directory — must be EXCLUDED from copy |

### Patterns and Conventions

- **Shebang and safety**: All shell scripts use `#!/usr/bin/env bash` and `set -euo pipefail`.
- **SCRIPT_DIR idiom**: `SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"` — used consistently for locating files relative to the script.
- **Source directory**: Source files live under `$SCRIPT_DIR/artifacts/developer/` — the install script is at project root alongside `pipeline.yaml`.
- **Error output**: Error messages go to `>&2`.
- **Post-install format**: The existing script uses a boxed format with `===` lines around the install-to path; the new requirements specify a simpler format — follow the requirements.

### Dependencies and Integration Points

- **Python package structure**: `telegram_bot/` is a proper Python package with `__init__.py` and `__main__.py`. It's invoked via `python -m telegram_bot`. When installed at target root, no `PYTHONPATH` is needed.
- **nvm sourcing**: The generated `run_bot.sh` must source nvm because `claude` (Node.js CLI) may be needed and won't be on PATH in non-login shells (systemd/cron). The exact block from the source is: `if [ -s "${NVM_DIR:-$HOME/.nvm}/nvm.sh" ]; then source "${NVM_DIR:-$HOME/.nvm}/nvm.sh"; fi`
- **Environment variables**: The bot expects `TELEGRAM_BOT_TOKEN` and `PIPELINE_YAML` as environment variables (exported in `run_bot.sh`).
- **Config file**: `telegram_bot.yaml` is loaded by `config.py` — the field names (`allowed_users`, `idle_timeout`, `shutdown_message`, `claude_path`) must match exactly.

### Implementation Notes

1. **This is a rewrite, not a new file.** `install_telegram_bot.sh` already exists at the project root. The existing version uses copy+sed (copies `run_bot.sh` then sed-replaces token/paths). The new version must **generate** `run_bot.sh` and `telegram_bot.yaml` using heredocs instead.

2. **Key difference from existing script — `--force` flag.** The existing script has no `--force` flag and just warns on overwrite. The new version must: (a) check all three targets (`telegram_bot/`, `run_bot.sh`, `telegram_bot.yaml`), (b) list which exist, (c) refuse without `--force`, (d) proceed with `--force`.

3. **Key difference — recursive .py copy with exclusions.** The existing script does `cp "$SOURCE_DIR/telegram_bot"/*.py` which is flat (top-level only). The new version must copy `.py` files recursively but exclude `tests/` and `__pycache__/`. Use `find` with appropriate filters and preserve directory structure, or use `rsync --include='*.py' --exclude='tests/' --exclude='__pycache__/' ...`.

4. **Suggested approach for copying .py files recursively:**
   ```bash
   rsync -a --include='*/' --include='*.py' --exclude='*' \
       --exclude='tests/' --exclude='__pycache__/' --exclude='.pytest_cache/' \
       "$SOURCE_DIR/telegram_bot/" "$TARGET/telegram_bot/"
   ```
   Alternatively, use `find` + `cp --parents` if rsync is not guaranteed available. Currently the only subdirs are `tests/` and `__pycache__/`, so flat copy would work in practice, but the requirement says recursive.

5. **Generating `run_bot.sh` — use a heredoc.** Write the entire file content inline using `cat <<'EOF' > "$TARGET/run_bot.sh"`. Use the source `run_bot.sh` as the template but: change `cd` to `cd "$SCRIPT_DIR"`, remove the `PYTHONPATH` export line, set `BOT_TOKEN="YOUR_TOKEN_HERE"`.

6. **Generating `telegram_bot.yaml` — use a heredoc.** Write inline. The `shutdown_message` value from source is: `"Record the product of this conversation as appropriate for your role and exit."`. The `claude_path` comment block should match the source formatting.

7. **Credential safety**: The existing script has a post-copy check for leaked real token (`8727225239`) and user ID (`106830816`). Since the new version generates fresh files rather than copying, these checks are no longer necessary — but you could keep them as a safety net if desired. The requirements don't mention them.

8. **Argument parsing order**: `--force` must be parsed before the positional argument. A simple approach:
   ```bash
   FORCE=false
   while [[ $# -gt 0 ]]; do
       case "$1" in
           --force) FORCE=true; shift ;;
           *) TARGET="$1"; shift ;;
       esac
   done
   ```

9. **pip check timing**: Requirements say pip check can be before or after copying. Doing it early (before any file operations) is cleaner — fail fast.

## Design Context

This script enables deploying the Telegram bot integration to any project that has an agent pipeline. The key design decision is that `run_bot.sh` and `telegram_bot.yaml` are generated fresh rather than copied-and-sed'd, because the installed layout (files at project root) differs from the source layout (files nested under `artifacts/developer/`). This eliminates the `PYTHONPATH` hack and `../../` path navigation.

See `artifacts/designer/install-script-design.md` for full design specification.
