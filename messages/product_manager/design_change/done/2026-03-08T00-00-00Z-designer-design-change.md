# Design Change: Make pipeline.yaml path configurable via run_bot.sh

## Metadata
- **From**: designer
- **To**: product_manager
- **Type**: design-change
- **Created**: 2026-03-08T00:00:00Z

## Changes Made

1. **Added `PIPELINE_YAML` environment variable** to the configuration table. It is required and specifies the absolute path to the pipeline config file used for agent discovery.

2. **Updated `run_bot.sh` launcher requirements**:
   - Must define a `PIPELINE_YAML` variable (defaulting to `pipeline.yaml` relative to project root), resolve it to an absolute path, and export it.
   - Must validate that the `PIPELINE_YAML` file exists before starting, refusing to start if it doesn't.

3. **Updated Agent Discovery section** to reference the `PIPELINE_YAML` environment variable instead of a hardcoded `pipeline.yaml` path.

## Motivation

User requested that the pipeline.yaml file location be configurable and set in the run_bot.sh script, rather than being hardcoded. This makes the bot more flexible for different project layouts and makes the dependency on pipeline.yaml explicit and visible in the launcher script.

## Files Changed

- `artifacts/designer/design.md` -- updated Configuration (environment variables table, launcher script requirements) and Agent Discovery sections
