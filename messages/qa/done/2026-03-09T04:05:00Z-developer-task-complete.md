# Create `install_telegram_bot.sh` deployment script

## Metadata
- **From**: developer
- **To**: qa
- **Type**: task-complete
- **Created**: 2026-03-09T04:05:00Z

## Summary of Changes

Rewrote `install_telegram_bot.sh` from scratch. The old version used a copy+sed approach (copy `run_bot.sh` and `telegram_bot.yaml` then sed-replace tokens/paths). The new version generates both files fresh using heredocs, adds a `--force` flag for overwrite control, copies `.py` files recursively with proper exclusions, and does early pip validation.

## Files Changed

- `install_telegram_bot.sh` — Complete rewrite: added `--force` flag, pre-flight checks for existing files, recursive `.py` copy with exclusions (tests/, __pycache__/, .pytest_cache/, .pyc), heredoc generation of `run_bot.sh` and `telegram_bot.yaml`, early pip availability check, simplified post-install message
- `artifacts/developer/telegram_bot/tests/test_install_script.sh` — New: 32-assertion test suite covering all QA steps (no-args, bad target, missing pipeline.yaml, successful install with file checks, overwrite without/with --force, generated file correctness)

## Requirements Addressed

1. ✅ Script at project root, executable
2. ✅ `[--force] <target-directory>` argument parsing
3. ✅ Target directory validation
4. ✅ `pipeline.yaml` existence check with descriptive error
5. ✅ Existing files check — lists which files exist, refuses without `--force`, proceeds with `--force`
6. ✅ Recursive `.py` copy excluding tests/, __pycache__/, .pytest_cache/, .pyc
7. ✅ Generated `run_bot.sh` with placeholder token, cd to SCRIPT_DIR, nvm sourcing, token validation, PIPELINE_YAML resolution, no PYTHONPATH, exec python -m telegram_bot
8. ✅ Generated `telegram_bot.yaml` with placeholder user ID (000000000), idle_timeout: 600, shutdown_message, commented claude_path
9. ✅ pip availability check (fails early if pip not found), then `pip install python-telegram-bot pyyaml`
10. ✅ Post-install message with next steps
11. ✅ `set -euo pipefail` and `#!/usr/bin/env bash`

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

## Test Coverage

- `artifacts/developer/telegram_bot/tests/test_install_script.sh` — 32 assertions covering all 8 QA steps
- Run with: `bash artifacts/developer/telegram_bot/tests/test_install_script.sh`
- All 32 tests pass

## Notes

- The pip check is done early (before any file operations) so we fail fast.
- The `.py` copy uses `find` with `-print0` for safe filename handling, rather than `rsync` which may not be available on all systems.
- Error messages go to stderr (`>&2`) per project conventions.
- The generated `run_bot.sh` uses single-quoted heredoc (`<<'EOF'`) so no variable expansion occurs during generation.
