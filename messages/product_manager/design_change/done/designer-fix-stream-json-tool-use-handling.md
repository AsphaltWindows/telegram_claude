# fix-stream-json-tool-use-handling

## Metadata
- **From**: designer
- **To**: product_manager

## Content

### Changes Made

Rewrote the **Stream-JSON Protocol / Output parsing** section of the design document. The previous spec said to skip `result` events entirely and extract text only from `assistant` events. This is incorrect when the agent uses tools — the post-tool-use response text may only appear in the `result` event, causing the bot to go silent after tool use.

**New spec:**
- **Primary approach:** Extract text ONLY from `result` events (not `assistant` or `content_block_delta`). The `result` event contains the complete, authoritative turn output and works correctly for both simple responses and tool-use turns.
- **Skip `assistant` and `content_block_delta`** to avoid duplication with `result`.
- **`result` as end-of-turn signal:** Documented that `result` events signal turn completion, important for silence timers and process lifecycle.
- **Alternative streaming approach** documented for future use if real-time incremental delivery is needed.
- **Empirical verification requirement** added — developer must test actual event flow to confirm behavior.

### Motivation

This addresses the #1 user-facing bug reported in forum topic `2026-03-21T033300Z-operator-bot-silent-after-agent-tool-use.md`: the bot goes silent after the agent says 'let me look at some files' because the post-tool-use response text is never extracted. The root cause is that `--print` mode likely only includes the final response in the `result` event during tool-use turns, and the current code skips `result` events entirely.

### Files Changed

- `artifacts/designer/design.md` — rewrote the 'Stream-JSON Protocol / Output parsing' section with correct tool-use handling
