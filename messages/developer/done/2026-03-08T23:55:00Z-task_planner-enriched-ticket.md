# Create `install_telegram_bot.sh` script for deploying bot to other projects

## Metadata
- **From**: task_planner
- **To**: developer
- **Type**: enriched-ticket
- **Created**: 2026-03-08T23:55:00Z

## Requirements

1. Create `install_telegram_bot.sh` in the project root (next to `pipeline.yaml`), executable (`chmod +x`).
2. The script accepts one positional argument: the path to the target project directory.
3. **Pre-flight checks** (abort with clear error message if any fail):
   - Argument is provided; print usage if missing.
   - Target directory exists and is a directory.
   - Target directory contains a `pipeline.yaml` file.
4. If `telegram_bot/` already exists in the target directory, print a warning but continue (overwrite).
5. **Copy files** from this repo to the target project root:
   - `artifacts/developer/telegram_bot/` → `<target>/telegram_bot/` (all `.py` files, recursive; exclude `__pycache__/` and `.pytest_cache/`).
   - `artifacts/developer/run_bot.sh` → `<target>/run_bot.sh` (with modifications per req 6–8).
   - `artifacts/developer/telegram_bot.yaml` → `<target>/telegram_bot.yaml` (with modifications per req 9).
6. In the copied `run_bot.sh`, replace the `BOT_TOKEN="<actual value>"` line with `BOT_TOKEN="YOUR_TOKEN_HERE"`.
7. In the copied `run_bot.sh`, change the working-directory (`cd`) logic so the script `cd`s to its own directory (the target project root) instead of navigating `../../` from `artifacts/developer/`.
8. In the copied `run_bot.sh`, remove or simplify the `PYTHONPATH` export since `telegram_bot/` will be at the project root.
9. In the copied `telegram_bot.yaml`, replace the `allowed_users` list entries with a single placeholder entry `- 000000000`.
10. **Dependency installation**: attempt `pip install python-telegram-bot pyyaml`. If `pip` is not available, print a warning with manual install instructions instead.
11. Make the copied `run_bot.sh` executable in the target.
12. **Post-install message**: print the target path and next-steps instructions (edit token, edit allowed_users, run the bot).
13. Do NOT copy `artifacts/developer/tests/`, `artifacts/developer/requirements.txt`, or any cache directories.

## QA Steps

1. Run `./install_telegram_bot.sh` with no arguments — verify it prints usage and exits non-zero.
2. Run `./install_telegram_bot.sh /nonexistent/path` — verify it errors about missing directory.
3. Run against a directory that exists but has no `pipeline.yaml` — verify it errors about missing pipeline config.
4. Run against a valid target directory containing `pipeline.yaml`:
   - Verify `telegram_bot/` directory is created with all `.py` files (no `__pycache__`).
   - Verify `run_bot.sh` exists, is executable, contains `BOT_TOKEN="YOUR_TOKEN_HERE"`, does NOT contain the real bot token, and has corrected `cd`/`PYTHONPATH` logic.
   - Verify `telegram_bot.yaml` exists and its `allowed_users` contains only `000000000`, not real user IDs.
   - Verify `tests/` and `requirements.txt` were NOT copied.
   - Verify the post-install message is printed with correct next steps.
5. Run again against the same target (files already exist) — verify it prints an overwrite warning and completes successfully.
6. Verify the script itself is executable and has a proper shebang (`#!/usr/bin/env bash` or `#!/bin/bash`).

## Technical Context

### Relevant Files

| File | Role |
|---|---|
| `install_telegram_bot.sh` (NEW) | The script to create, in the project root at `/home/iv/dev/telegram_claude/` |
| `artifacts/developer/run_bot.sh` | Source launcher script — will be copied and modified. Contains real bot token on line 8, `cd "$SCRIPT_DIR/../.."` on line 16, and `PYTHONPATH="${SCRIPT_DIR}..."` on line 49 |
| `artifacts/developer/telegram_bot.yaml` | Source config — will be copied and modified. Contains real user ID `106830816` on line 3 |
| `artifacts/developer/telegram_bot/` | Python package directory — contains 6 `.py` files to copy: `__init__.py`, `__main__.py`, `bot.py`, `config.py`, `discovery.py`, `session.py` |
| `artifacts/developer/telegram_bot/tests/` | Test directory — must NOT be copied |
| `artifacts/developer/requirements.txt` | Lists `python-telegram-bot` and `pyyaml` — must NOT be copied, but these are the packages to `pip install` |
| `pipeline.yaml` | Exists at project root — used as the reference for where the new script goes |

### Patterns and Conventions

- The project uses `#!/usr/bin/env bash` with `set -euo pipefail` (see `run_bot.sh` line 1–2). Follow this pattern for the new script.
- Existing shell scripts in `scripts/` (e.g., `add_comment.sh`, `vote_close.sh`) can be referenced for style, but `run_bot.sh` is the closest analog.
- Color output: the project doesn't appear to use colored terminal output in its shell scripts, so plain `echo` is fine.

### Dependencies and Integration Points

- The script operates entirely on the filesystem — no runtime dependencies beyond `bash`, `cp`, `mkdir`, `sed`, and optionally `pip`.
- The `telegram_bot/` Python package has no sub-packages (flat structure with 6 `.py` files), so a simple file copy is sufficient — no need for `find -type d` recursion for nested packages.
- The `tests/` directory is a subdirectory of `telegram_bot/` (at `artifacts/developer/telegram_bot/tests/`), so the copy must explicitly exclude it. A simple approach: copy `telegram_bot/*.py` rather than doing a recursive copy of the whole directory.

### Implementation Notes

1. **Script location**: Create at `/home/iv/dev/telegram_claude/install_telegram_bot.sh`.

2. **Determining source directory**: Use `SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"` to find the install script's own location, then reference source files relative to it (e.g., `$SCRIPT_DIR/artifacts/developer/...`).

3. **Copying `.py` files (req 5, 13)**: Since the package is flat (no sub-packages), you can:
   ```bash
   mkdir -p "$TARGET/telegram_bot"
   cp "$SOURCE/telegram_bot"/*.py "$TARGET/telegram_bot/"
   ```
   This naturally excludes `tests/` (a subdirectory) and `__pycache__/` (a directory). No need for `find` or `rsync`.

4. **Modifying `run_bot.sh` (req 6–8)**: Use `sed` on the copied file. Three transformations:
   - **Line 8** — Token: `sed -i 's/^BOT_TOKEN=".*"/BOT_TOKEN="YOUR_TOKEN_HERE"/'`
   - **Line 16** — cd logic: Replace `cd "$SCRIPT_DIR/../.."` with `cd "$SCRIPT_DIR"` (since the script now lives at the project root, `SCRIPT_DIR` IS the project root)
   - **Line 49** — PYTHONPATH: Remove or simplify. The current line is `export PYTHONPATH="${SCRIPT_DIR}${PYTHONPATH:+:$PYTHONPATH}"`. Since `telegram_bot/` is at the project root and we're already `cd`'d there, this can be removed entirely or replaced with a no-op. Simplest: delete the line.

5. **Modifying `telegram_bot.yaml` (req 9)**: Use `sed` to replace the `allowed_users` block. The current file has:
   ```yaml
   allowed_users:
     - 106830816
   ```
   Replace with:
   ```yaml
   allowed_users:
     - 000000000
   ```
   A targeted `sed` replacing the user ID line is safest: `sed -i 's/^  - [0-9]\+$/  - 000000000/' "$TARGET/telegram_bot.yaml"`.

6. **Credential safety**: The real bot token is `8727225239:AAFBEyRFy8gwm_QdpRiyL3YWj4VIjn2_iI8` and the real user ID is `106830816`. The script MUST NOT leak these into the target. Verify sed replacements work correctly — consider using `grep` after to confirm.

7. **Overwrite warning (req 4)**: Check `[ -d "$TARGET/telegram_bot" ]` before copying and print a warning if it exists.

8. **pip install (req 10)**: Use `command -v pip` to check availability. If available, run `pip install python-telegram-bot pyyaml`. If not, print manual instructions.

9. **Suggested script structure**:
   ```
   shebang + set -euo pipefail
   SCRIPT_DIR resolution
   usage function
   pre-flight checks (args, dir exists, pipeline.yaml exists)
   overwrite warning
   copy telegram_bot/*.py
   copy + modify run_bot.sh
   copy + modify telegram_bot.yaml
   chmod +x run_bot.sh
   pip install (or warning)
   post-install message
   ```

## Design Context

The user wants a single command to install the Telegram bot integration into any project that already has the agent pipeline set up. The script must strip real credentials so the distributed copy is safe to share. See `artifacts/designer/install-script-design.md` for the full specification.
