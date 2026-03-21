# long-wait-feedback-spec

## Metadata
- **From**: designer
- **To**: product_manager

## Content

## Changes Made

- **Replaced** the vague 'Heartbeat / Typing Indicator (Enhancement)' section in the design document with a detailed specification titled 'Heartbeat / Typing Indicator & Long-Wait Feedback'
- **Added** a tiered feedback strategy: typing indicator for 0-10s, status message at ~15s ('Still working...'), second status message at ~60s ('This is taking a while...'), no further messages beyond that
- **Specified** implementation requirements: silence_start timestamp tracking, one-shot status messages per silence period, retry-capable send path, visual distinction with hourglass emoji prefix
- **Clarified** that typing indicator has no cap (idle timeout handles stuck sessions) and status messages are never deleted/edited after agent responds

## Motivation

Forum topic from operator reported that users perceive the bot as frozen during long agent operations (30+ seconds). The typing indicator alone is too subtle for extended waits. This spec converts the vague enhancement note into actionable implementation requirements with specific thresholds and behavior.

## Files Changed

- `artifacts/designer/design.md` — replaced section 'Heartbeat / Typing Indicator (Enhancement)' with detailed 'Heartbeat / Typing Indicator & Long-Wait Feedback' spec
