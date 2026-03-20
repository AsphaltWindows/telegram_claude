# Telegram Bot: Agent Discovery from pipeline.yaml

## Metadata
- **From**: product_manager
- **To**: task_planner
- **Type**: ticket
- **Created**: 2026-03-08T15:11:00Z

## Requirements

1. Create `telegram_bot/discovery.py` that reads `pipeline.yaml` from the project root
2. Extract all agents with `type: source` and return their names as a list of strings
3. Agents with `scheduled: false` must still be included (e.g., `operator`)
4. Return value should be a list of agent name strings (e.g., `["operator", "architect", "designer"]`)
5. Raise a clear error if `pipeline.yaml` is not found or cannot be parsed
6. Handle edge case: if no source agents are found, return an empty list (do not error)

## QA Steps

1. With the existing `pipeline.yaml` in the project, run discovery and verify it returns all source agents (`operator`, `architect`, `designer`)
2. Create a test `pipeline.yaml` with a mix of source and non-source agents; verify only source agents are returned
3. Create a test `pipeline.yaml` with a source agent that has `scheduled: false`; verify it is still included
4. Remove `pipeline.yaml` and verify a clear error is raised
5. Create a `pipeline.yaml` with no source agents; verify an empty list is returned

## Design Context

Agent discovery enables the bot to dynamically register Telegram commands based on the pipeline configuration, rather than hardcoding agent names. This is used at bot startup. See `artifacts/designer/design.md`, section "Agent Discovery".
