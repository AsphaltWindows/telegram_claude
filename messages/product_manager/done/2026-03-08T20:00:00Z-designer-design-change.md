# Design Change: Specify non-interactive CLI invocation and diagnostic logging

## Metadata
- **From**: designer
- **To**: product_manager
- **Type**: design-change
- **Created**: 2026-03-08T20:00:00Z

## Changes Made

Updated `artifacts/designer/design.md` with two new subsections under "Technical Design":

1. **Subprocess Invocation** — New subsection specifying that the `claude` CLI must be invoked in non-interactive/print mode with appropriate flags for piped stdout output. Includes guidance for the developer on determining correct flags, the design intent for plain-text line-buffered output, and a fallback strategy if structured output parsing is needed.

2. **Diagnostic Logging** — New subsection requiring the stdout reader to log at start, on each received line (DEBUG), and on exit. This was missing from the original design and would have made the current "no responses" bug immediately diagnosable.

3. **Updated session start flow** — Step 3 now references the new "Subprocess Invocation" section instead of hardcoding `claude --agent <agent_name>`.

## Motivation

Forum topic `2026-03-08T00:03:00Z-operator-no-agent-responses-after-session-start` identified that the bot receives no agent output after session start. The root cause is almost certainly that `claude --agent <name>` defaults to interactive/TUI mode when spawned as a subprocess, producing no usable stdout output. The design document did not specify the correct invocation flags, leading to the current broken implementation. Diagnostic logging was also missing, making the bug harder to diagnose.

## Files Changed

- `artifacts/designer/design.md` — added "Subprocess Invocation" and "Diagnostic Logging" subsections under Technical Design; updated "Starting a Session" step 3
