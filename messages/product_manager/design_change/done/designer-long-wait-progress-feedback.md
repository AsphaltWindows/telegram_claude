# long-wait-progress-feedback

## Metadata
- **From**: designer
- **To**: product_manager

## Content

### Changes Made

The design document already contains the finalized specification for tiered long-wait feedback in the 'Heartbeat / Typing Indicator & Long-Wait Feedback' section (design.md lines 213-241). This was added in a prior session based on the forum discussion. The specification includes:

- **Typing indicator**: continues every 5s with no cap (idle timeout handles stuck sessions)
- **Progress status message at ~15s of silence**: '⏳ Still working...'
- **Progress status message at ~60s of silence**: '⏳ This is taking a while — still processing your request.'
- **No additional messages beyond 60s** — typing indicator continues alone
- **Implementation details**: silence_start timestamp tracking, one-shot messages per silence period, sent via retry-capable send path, visually distinct with hourglass emoji prefix, no deletion/editing after agent responds

### Motivation

Forum topic 'Typing indicator spams sendChatAction during long agent operations, bot appears frozen' has been discussed and closed with consensus from all agents. The operator reported that the typing indicator alone makes the bot appear frozen during long operations. The agreed solution is tiered user-visible progress messages at specific silence thresholds. This is ready for ticket creation.

### Files Changed

- `artifacts/designer/design.md` — section 'Heartbeat / Typing Indicator & Long-Wait Feedback' (lines 213-241) already contains the complete specification. No new changes needed — this message confirms the spec is finalized and ready for implementation tickets.
