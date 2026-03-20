# Create `run_bot.sh` launcher script with PIPELINE_YAML support

## Metadata
- **From**: product_manager
- **To**: task_planner
- **Type**: ticket
- **Created**: 2026-03-08T20:00:00Z

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

## Design Context

User requested that the pipeline.yaml file location be configurable and set in the launcher script rather than hardcoded. This makes the bot flexible for different project layouts and makes the dependency on pipeline.yaml explicit. See `artifacts/designer/design.md`, "Launcher Script: `run_bot.sh`" section.
