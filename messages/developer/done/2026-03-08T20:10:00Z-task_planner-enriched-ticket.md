# Create `run_bot.sh` launcher script with PIPELINE_YAML support

## Metadata
- **From**: task_planner
- **To**: developer
- **Type**: enriched-ticket
- **Created**: 2026-03-08T20:10:00Z

## Requirements

1. Create `run_bot.sh` at the project root as the single entry point for running the bot.
2. At the top of the script, define a clearly marked placeholder variable: `BOT_TOKEN="YOUR_TOKEN_HERE"`.
3. Define a `PIPELINE_YAML` variable with default value `pipeline.yaml` (relative to project root).
4. The script must resolve `PIPELINE_YAML` to an absolute path before exporting it.
5. Export `TELEGRAM_BOT_TOKEN` from the `BOT_TOKEN` variable.
6. Export `PIPELINE_YAML` so the bot process can read it.
7. The script must `cd` to the project root directory, derived from the script's own location (e.g., using `dirname` / `readlink`), so `claude` agent commands resolve correctly.
8. The script must refuse to start if `BOT_TOKEN` is still the placeholder value `"YOUR_TOKEN_HERE"`, printing a clear error message.
9. The script must refuse to start if the resolved `PIPELINE_YAML` file does not exist, printing a clear error message that includes the path it tried.
10. The script must run `python -m telegram_bot` as its final command.
11. The script must be executable (`chmod +x`).

## QA Steps

1. Run `run_bot.sh` without editing `BOT_TOKEN` — verify it exits with an error message about setting the token.
2. Set `BOT_TOKEN` to a real value but point `PIPELINE_YAML` to a nonexistent file — verify it exits with an error message naming the missing file.
3. Set `BOT_TOKEN` and ensure `pipeline.yaml` exists at project root — verify it resolves the path to absolute, exports both env vars, and attempts to run `python -m telegram_bot`.
4. Run the script from a different working directory (e.g., `cd /tmp && /path/to/run_bot.sh`) — verify it correctly `cd`s to the project root.
5. Set `PIPELINE_YAML` to a custom relative path (e.g., `config/my-pipeline.yaml`) and create that file — verify it resolves and works correctly.
6. Verify the script file has the executable permission bit set.

## Technical Context

### Relevant Files

- **`artifacts/developer/telegram_bot/run_bot.sh`** — An existing partial implementation of this script. It already has the shebang, `set -euo pipefail`, `BOT_TOKEN` (currently hardcoded to a real token that needs replacing with the placeholder), the `cd` logic, the token validation check, and `exec python -m telegram_bot`. **This file needs to be updated in place**, not created from scratch. It is missing `PIPELINE_YAML` support and the path-existence check.
- **`artifacts/developer/telegram_bot/__main__.py`** — The Python entry point invoked by `python -m telegram_bot`. Calls `main()` from `bot.py`.
- **`artifacts/developer/telegram_bot/bot.py`** — `build_application()` calls `discover_source_agents()` with no arguments (uses default path). The companion ticket will update this to use `PIPELINE_YAML`.

### Patterns and Conventions

- The existing `run_bot.sh` uses `#!/usr/bin/env bash` and `set -euo pipefail` — continue this pattern.
- The existing script uses `$(dirname "${BASH_SOURCE[0]}")` for path resolution. Note: the current `cd` does `/.."` which is wrong — the script is at `artifacts/developer/telegram_bot/run_bot.sh`, but the **final** location should be at the project root (`run_bot.sh`). The ticket says "at the project root", so the `cd` should resolve to the directory containing the script itself: `cd "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"`.
- Error messages are sent to stderr (`>&2`).
- The final command uses `exec` to replace the shell process.

### Dependencies and Integration Points

- **`PIPELINE_YAML` env var** — The companion ticket (enriched separately) will update `config.py` and `discovery.py` to read this env var. The launcher script is responsible for resolving the relative path to absolute and exporting it.
- **`pipeline.yaml`** — Already exists at the project root (`/home/iv/dev/telegram_claude/pipeline.yaml`). This is the default file the variable should point to.
- **`python -m telegram_bot`** — The script assumes the Python environment has `python-telegram-bot` and `pyyaml` installed.

### Implementation Notes

1. **Replace the hardcoded token**: The existing `run_bot.sh` has a real token on line 8. Replace it with `YOUR_TOKEN_HERE`.
2. **Add `PIPELINE_YAML` variable**: After `BOT_TOKEN`, add `PIPELINE_YAML="pipeline.yaml"`.
3. **Fix the `cd` command**: Since the script will live at the project root, use `cd "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"` to resolve symlinks and get the absolute directory.
4. **Resolve `PIPELINE_YAML` to absolute path**: After the `cd`, resolve with something like: `PIPELINE_YAML="$(cd "$(dirname "$PIPELINE_YAML")" && pwd)/$(basename "$PIPELINE_YAML")"` — or more simply, since we've already `cd`'d to the project root, use `PIPELINE_YAML="$(realpath "$PIPELINE_YAML")"` or `PIPELINE_YAML="$(pwd)/$PIPELINE_YAML"` if it's relative.
5. **Add file-existence check for `PIPELINE_YAML`**: After resolving, check `[ -f "$PIPELINE_YAML" ]` and error with the path if missing.
6. **Export `PIPELINE_YAML`**: Add `export PIPELINE_YAML` before the `exec` line.
7. **`chmod +x`**: After writing the file, run `chmod +x run_bot.sh`.
8. **Order of operations in the script**: (a) define variables, (b) `cd` to project root, (c) validate token, (d) resolve `PIPELINE_YAML` to absolute, (e) validate pipeline file exists, (f) export both vars, (g) `exec python -m telegram_bot`.

## Design Context

User requested that the pipeline.yaml file location be configurable and set in the launcher script rather than hardcoded. This makes the bot flexible for different project layouts and makes the dependency on pipeline.yaml explicit. See `artifacts/designer/design.md`, "Launcher Script: `run_bot.sh`" section.
