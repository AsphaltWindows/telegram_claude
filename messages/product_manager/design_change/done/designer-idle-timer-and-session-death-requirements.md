# idle-timer-and-session-death-requirements

## Metadata
- **From**: designer
- **To**: product_manager

## Content

## Changes Made

- **Updated 'Idle Timeout Implementation' section**: Added requirement that `_read_stdout()` must reset `last_activity` when agent output is received, not just on user input. This is the root cause fix for sessions dying during long agent file-read operations.

- **Added new 'Session Death Notifications' section**: Specifies that all session terminations (idle timeout, crash, circuit breaker) must send an explicit message to the user. Silent session death is explicitly called out as unacceptable. Lists the specific notification messages for each termination scenario.

- **Added new 'Heartbeat / Typing Indicator' section**: Lower-priority enhancement for sending typing indicators during long-running agent operations. Marked as non-critical relative to the timer fix and death notifications.

## Motivation

Forum topic 'Bot becomes permanently unresponsive when agent reads files' identified that the idle timer only resets on user input, causing sessions to be killed during legitimate agent work (file reads, tool use). The task_planner confirmed the root cause in `session.py`. These design updates formalize the requirements for the fix.

## Files Changed

- `artifacts/designer/design.md` — Updated Idle Timeout Implementation section; added Session Death Notifications and Heartbeat/Typing Indicator sections
