# Telegram Bot — Ticket Backlog

## Tickets Created: 2026-03-08

All tickets created from design-change `2026-03-08T15:00:00Z-designer-design-change.md`.

### Ticket 1: Project Scaffolding & Configuration Loading
- **File**: `2026-03-08T15:10:00Z-product_manager-ticket.md`
- **Scope**: Package structure, `config.py`, `telegram_bot.yaml`, `requirements.txt`
- **Dependencies**: None (foundation ticket)

### Ticket 2: Agent Discovery from pipeline.yaml
- **File**: `2026-03-08T15:11:00Z-product_manager-ticket.md`
- **Scope**: `discovery.py` — read pipeline.yaml, extract source agents
- **Dependencies**: None (standalone)

### Ticket 3: Session Management & Process Lifecycle
- **File**: `2026-03-08T15:12:00Z-product_manager-ticket.md`
- **Scope**: `session.py` — spawn claude processes, stdin/stdout piping, idle timeout, graceful shutdown
- **Dependencies**: Ticket 1 (config values)

### Ticket 4: Bot Handlers, Authentication & Entry Point
- **File**: `2026-03-08T15:13:00Z-product_manager-ticket.md`
- **Scope**: `bot.py` — Telegram handlers, auth, message routing, message splitting, entry point
- **Dependencies**: Tickets 1, 2, 3

---

## Tickets Created: 2026-03-08 (Design Change: PIPELINE_YAML configurable path)

From design-change `2026-03-08T00-00-00Z-designer-design-change.md`.

### Ticket 5: Create `run_bot.sh` launcher script with PIPELINE_YAML support
- **File**: `2026-03-08T20:00:00Z-product_manager-ticket.md`
- **Scope**: `run_bot.sh` — launcher script with BOT_TOKEN placeholder, PIPELINE_YAML variable, path resolution, validation, exports
- **Dependencies**: None (standalone)

### Ticket 6: Use PIPELINE_YAML env var for agent discovery
- **File**: `2026-03-08T20:01:00Z-product_manager-ticket.md`
- **Scope**: Amend `config.py` and `discovery.py` to read `PIPELINE_YAML` env var instead of hardcoded path
- **Dependencies**: Amends Tickets 1 & 2; companion to Ticket 5

---

## Tickets Created: 2026-03-09 (Design Change: Non-interactive CLI invocation & diagnostic logging)

From design-change `2026-03-08T20:00:00Z-designer-design-change.md`. Motivated by forum topic `2026-03-08T00:03:00Z-operator-no-agent-responses-after-session-start`.

### Ticket 7: Fix subprocess invocation and output parsing for non-interactive claude CLI usage
- **File**: `2026-03-09T00:30:00Z-product_manager-ticket.md`
- **Scope**: Change subprocess invocation to use `--print` and correct output/input format flags; update `_read_stdout()` to parse structured output; update `send()` for input protocol
- **Priority**: P0 / Critical — bot is non-functional without this
- **Dependencies**: Amends Ticket 3 (session management)

### Ticket 8: Add diagnostic logging to stdout reader
- **File**: `2026-03-09T00:31:00Z-product_manager-ticket.md`
- **Scope**: Add INFO/DEBUG log lines in `_read_stdout()` for start, each received line, and exit with reason
- **Priority**: P1 — aids debugging, independently implementable
- **Dependencies**: None (can be done before or after Ticket 7)

## Recommended Implementation Order

1. Ticket 1 (scaffolding) and Ticket 2 (discovery) — can be done in parallel
2. Ticket 5 (run_bot.sh) and Ticket 6 (PIPELINE_YAML integration) — can be done alongside or after Tickets 1 & 2
3. Ticket 3 (session management) — after Ticket 1
4. Ticket 4 (bot handlers) — after all others
5. **Ticket 7 (P0 fix: CLI invocation)** — highest priority, amends Ticket 3
6. Ticket 8 (diagnostic logging) — can be done alongside Ticket 7

---

## Tickets Created: 2026-03-08 (Design Change: Install script for deploying bot to other projects)

From design-change `2026-03-08T23:50:00Z-designer-design-change.md`.

### Ticket 9: Create `install_telegram_bot.sh` deployment script
- **File**: `2026-03-08T23:55:00Z-product_manager-ticket.md`
- **Scope**: Shell script in project root that copies the telegram_bot package, generates `run_bot.sh` and `telegram_bot.yaml` with blanked credentials, runs pip install, validates target project
- **Dependencies**: Requires Tickets 1-4 to be implemented (the bot code must exist to be copied)
- **Priority**: P2 — deployment tooling, not blocking core functionality

---

## Tickets Created: 2026-03-20 (Bug Fix: Idle timer reset on agent stdout)

From forum discussion `forum/closed/2026-03-19-operator-idle-timer-kills-active-agents.md`, escalated in `forum/open/2026-03-20-operator-agent-unresponsive-during-tool-use.md`.

### Ticket 10: Fix idle timer reset on agent stdout output
- **Slug**: `fix-idle-timer-agent-output`
- **Scope**: Add `self.last_activity = time.monotonic()` and `self._reset_idle_timer()` in `_read_stdout()` after the empty-line guard (line 383) in `telegram_bot/session.py`
- **Priority**: P0 / Critical — causes complete session death during normal agent operation
- **Dependencies**: None (2-line bug fix in existing code)
- **Status**: Ticket sent to task_planner 2026-03-20

### Ticket 11: Session timeout user notification and recovery
- **Slug**: `session-timeout-user-notification`
- **Scope**: Notify user via Telegram when session is killed by idle timeout; ensure new messages after timeout correctly start a new session; harden on_end callback error handling
- **Priority**: P1 — UX bug, bot goes silent after timeout with no user feedback
- **Dependencies**: Can be developed independently of Ticket 10, but both address the same incident
- **Status**: Ticket sent to task_planner 2026-03-20
