# add-diagnostic-logging-enhancements

## Metadata
- **From**: designer
- **To**: product_manager

## Content

## Changes Made

- **Added INFO-level event logging requirements** to the Diagnostic Logging section: high-signal filtered events (tool_use, tool_result, error) must be logged at INFO level with brief summaries; extracted text logged with truncated preview; send success/failure logged explicitly.
- **Added silence period summary logging**: the typing heartbeat must log silence duration and filtered-event count at INFO level, turning the invisible heartbeat into actionable diagnostics.
- **Added configurable LOG_LEVEL env var**: replaces hardcoded INFO level with an environment variable (LOG_LEVEL, default INFO) so users can toggle to DEBUG without code changes. Added to the Environment Variables table.

## Motivation

Forum topic from operator identified a critical observability gap: during long agent operations, the bot logs raw stdout at DEBUG level but runs at INFO level, creating zero visibility into what the agent is doing. This makes it impossible to diagnose why the bot appears frozen (typing indicator fires but no messages sent). These changes provide the diagnostic logging needed to distinguish between agent silence, filtered events, and send failures.

## Files Changed

- `artifacts/designer/design.md` — updated Diagnostic Logging section with three new subsections (INFO-Level Event Logging, Silence Period Summary Logging, Configurable Log Level); added LOG_LEVEL to Environment Variables table.
