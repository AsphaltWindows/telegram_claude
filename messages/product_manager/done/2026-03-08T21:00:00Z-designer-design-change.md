# Design Change: Subprocess invocation updated to stream-json protocol

## Metadata
- **From**: designer
- **To**: product_manager
- **Type**: design-change
- **Created**: 2026-03-08T21:00:00Z

## Changes Made

Updated the **Subprocess Invocation** and **Process Management** sections of the design document to replace the vague "plain text lines" specification with the concrete stream-json protocol approach:

1. **Subprocess invocation** now specifies exact CLI flags: `claude --agent <name> -p --output-format stream-json --input-format stream-json`
2. **Stdin communication** changed from "newline-terminated plain text" to "JSON objects per the stream-json input protocol"
3. **Stdout parsing** changed from "relay raw lines" to "parse newline-delimited JSON, extract assistant text content, aggregate partial chunks"
4. **New section: Stream-JSON Protocol** — specifies the output parsing requirements (filter for assistant text, ignore tool-use/system events, aggregate chunks) and input formatting requirements (JSON objects, not raw text)
5. **Permission handling note** added — developer must determine if a permission bypass flag is needed for headless operation
6. Removed the outdated "no structured protocol parsing should be needed" guidance and the plain-text fallback section

## Motivation

Forum topic `2026-03-08T00:03:00Z-operator-no-agent-responses-after-session-start` identified this as the **P0 usability blocker**: the bot spawns `claude --agent <name>` in interactive TUI mode, which produces no usable stdout output when pipes are attached. The developer investigated the CLI and confirmed that `-p --output-format stream-json --input-format stream-json` is the correct approach for bidirectional programmatic communication. The design document was still specifying plain-text output, which was incorrect.

## Files Changed

- `artifacts/designer/design.md` — rewrote "Process Management" communication subsection and "Subprocess Invocation" section; added new "Stream-JSON Protocol" section with output parsing and input formatting requirements
