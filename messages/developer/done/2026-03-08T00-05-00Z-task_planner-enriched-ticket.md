# Create `run_bot.sh` launcher script

## Metadata
- **From**: task_planner
- **To**: developer
- **Type**: enriched-ticket
- **Created**: 2026-03-08T00:05:00Z

## Requirements

1. Create a file `run_bot.sh` at the project root
2. The script must have a clearly marked placeholder variable at the top: `BOT_TOKEN="YOUR_TOKEN_HERE"`
3. The script must export `TELEGRAM_BOT_TOKEN` from the `BOT_TOKEN` variable
4. The script must `cd` to the project root directory, derived from the script's own location (e.g., using `$(dirname "$0")` or `BASH_SOURCE`), so that `claude` agent commands resolve correctly regardless of where the script is invoked from
5. The script must check whether `BOT_TOKEN` is still set to the placeholder value `YOUR_TOKEN_HERE` and refuse to start if so, printing a clear error message telling the user to edit the script and set their token
6. The script must run `python -m telegram_bot` after validation passes
7. The file must be executable (`chmod +x run_bot.sh`)
8. The script should use `#!/usr/bin/env bash` as the shebang line

## QA Steps

1. Verify `run_bot.sh` exists at the project root and is executable (`ls -la run_bot.sh` shows `x` permission bits)
2. Run `./run_bot.sh` without modifying the placeholder token — verify it prints an error message about the token needing to be set and exits with a non-zero status code
3. Read the script and verify it contains `BOT_TOKEN="YOUR_TOKEN_HERE"` near the top
4. Read the script and verify it exports `TELEGRAM_BOT_TOKEN` from `BOT_TOKEN`
5. Read the script and verify it `cd`s to the directory containing the script itself (not hardcoded, but derived from the script's location)
6. Read the script and verify it invokes `python -m telegram_bot`
7. Set `BOT_TOKEN` to a real value and run — verify it attempts to start the bot (it will fail if dependencies aren't installed, but it should get past the token check and attempt `python -m telegram_bot`)

## Technical Context

### Relevant Files
- **`run_bot.sh`** (to be created) — the new launcher script at the project root `/home/iv/dev/telegram_claude/run_bot.sh`
- **`scripts/run_scheduler.sh`** — existing bash script in the project; use as a reference for conventions (shebang, `set -euo pipefail`, directory resolution pattern)
- **`artifacts/developer/telegram_bot/__main__.py`** — the Python entry point that `python -m telegram_bot` invokes; calls `main()` from `telegram_bot.bot`
- **`artifacts/developer/telegram_bot/bot.py`** — the bot's main module, reads `TELEGRAM_BOT_TOKEN` from the environment
- **`artifacts/developer/telegram_bot/config.py`** — config loading; confirms `TELEGRAM_BOT_TOKEN` is the expected env var name

### Patterns and Conventions
- **Shebang**: The project uses `#!/usr/bin/env bash` (see `scripts/run_scheduler.sh`)
- **Safety flags**: Existing scripts use `set -euo pipefail` — the new script should follow this convention
- **Directory resolution**: The scheduler script uses `ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"` to resolve the project root from `scripts/`. Since `run_bot.sh` is at the project root itself, the pattern should be `cd "$(dirname "$0")"` or equivalently `cd "$(dirname "${BASH_SOURCE[0]}")"` — no need for the `..` parent traversal
- **File location**: The script goes at the project root (`/home/iv/dev/telegram_claude/run_bot.sh`), not inside `scripts/`

### Dependencies and Integration Points
- **Environment variable**: The bot code expects `TELEGRAM_BOT_TOKEN` to be set. The script bridges the gap between the user-facing `BOT_TOKEN` variable and this env var via `export TELEGRAM_BOT_TOKEN="$BOT_TOKEN"`
- **`python -m telegram_bot`**: This invokes `telegram_bot/__main__.py`, which calls `main()` from `telegram_bot.bot`. The `telegram_bot/` package must be on the Python path — running from the project root ensures this
- **Working directory matters**: The bot spawns `claude --agent <name>` subprocesses that need to run from the project root. The `cd` in the script ensures this regardless of where the user invokes the script from

### Implementation Notes
- This is a straightforward single-file creation task. No existing files need modification.
- After writing the file, run `chmod +x run_bot.sh` to make it executable.
- Suggested script structure:
  1. Shebang line
  2. `set -euo pipefail`
  3. `BOT_TOKEN="YOUR_TOKEN_HERE"` placeholder
  4. `cd` to script's directory
  5. Token validation check (compare `$BOT_TOKEN` to `"YOUR_TOKEN_HERE"`, print error to stderr, `exit 1`)
  6. `export TELEGRAM_BOT_TOKEN="$BOT_TOKEN"`
  7. `exec python -m telegram_bot` (using `exec` is optional but clean — replaces the shell process with Python)
- The error message for the placeholder check should be user-friendly, e.g.: `"Error: BOT_TOKEN is not set. Edit run_bot.sh and replace YOUR_TOKEN_HERE with your Telegram bot token."`

## Design Context

The user wants a simple entry point where they can paste in their Telegram bot token and run the bot without needing to manually export environment variables or remember the Python module invocation. See `artifacts/designer/design.md`, section "Launcher Script: `run_bot.sh`".
