# Use PIPELINE_YAML env var for agent discovery instead of hardcoded path

## Metadata
- **From**: product_manager
- **To**: task_planner
- **Type**: ticket
- **Created**: 2026-03-08T20:01:00Z

## Requirements

1. In `telegram_bot/config.py`, read the `PIPELINE_YAML` environment variable. It is required — the bot must raise a clear error at startup if it is not set.
2. In `telegram_bot/discovery.py`, use the path from `PIPELINE_YAML` (via config) to locate and read the pipeline config file, instead of assuming a hardcoded `pipeline.yaml` path.
3. If the file at the `PIPELINE_YAML` path does not exist or cannot be parsed, raise a clear error with the path included in the message.
4. This is an amendment to the scope of existing tickets (Ticket 1: config.py, Ticket 2: discovery.py). If those tickets have not yet been implemented, incorporate these requirements into their implementation. If already implemented, update accordingly.

## QA Steps

1. Set `PIPELINE_YAML` to a valid pipeline.yaml path — verify the bot reads and discovers source agents from it.
2. Set `PIPELINE_YAML` to a nonexistent path — verify the bot fails at startup with a clear error message including the bad path.
3. Unset `PIPELINE_YAML` entirely — verify the bot fails at startup with an error indicating the env var is required.
4. Set `PIPELINE_YAML` to a file that exists but is not valid YAML — verify a parse error is raised with the path in the message.

## Design Context

The `PIPELINE_YAML` environment variable replaces the previously hardcoded `pipeline.yaml` reference in agent discovery. It is exported by `run_bot.sh` (see companion ticket). See `artifacts/designer/design.md`, "Configuration > Environment Variables" table and "Agent Discovery" section.
