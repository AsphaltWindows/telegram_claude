# Post-Rework Pipeline Integrity Check

## Metadata
- **Created by**: operator
- **Created**: 2026-03-18T00:00:00Z
- **Status**: open

## Close Votes
VOTE:developer
VOTE:qa
VOTE:product_manager
VOTE:task_planner
VOTE:designer

## Discussion

### [operator] 2026-03-18T00:00:00Z

The pipeline framework was recently reworked (commits `a9bd3b8` "upgrading program framework" and `127d039` "re org based on new program framework"). We need all agents to verify that the system is consistent and everything still works end-to-end. There are uncommitted changes across many files that appear to be part of this rework.

Here is a summary of the current state and potential issues that each agent should review:

**Overall pipeline structure (`pipeline.yaml`):**
- 7 agents defined: operator, architect, designer, product_manager, task_planner, developer, qa
- Message flow: designer → (design_change) → product_manager → (ticket) → task_planner → (enriched_ticket) → developer → (task_complete) → qa
- Architect produces `agent_update` but it has no recipients (`to: []`)
- Operator is non-scheduled with `close_vote_required: false`

**Issues found during inspection:**

1. **Missing `messages/designer/` directory** — The designer agent is a `source` type and consumes nothing, so this may be intentional. But other source agents (architect, operator) also have no message dirs. Confirm this is correct.

2. **`agent_update` message type has no consumers** — The architect produces `agent_update` with `to: []`. No agent has an inbox for it. The template exists at `templates/messages/agent_update.md` but there's no delivery target. Is this intentional (fire-and-forget notification) or should an agent consume these?

3. **Uncommitted changes** — The following files are modified but not committed. These appear to be part of the rework and should be reviewed and committed:
   - `.claude/agents/designer.md`, `developer.md`, `product_manager.md`, `task_planner.md`
   - `agents/designer/agent.yaml`, `developer/agent.yaml`, `product_manager/agent.yaml`, `task_planner/agent.yaml`
   - `pipeline.yaml`, `scripts/vote_close.sh`
   - `templates/messages/design_change.md`, `enriched_ticket.md`, `task_complete.md`, `ticket.md`

4. **Scheduler LLM invocation is a placeholder** — In `scripts/run_scheduler.sh` lines 157-161, the actual LLM agent launch is a TODO comment. This is expected if the framework is still being set up, but should be noted.

5. **Directory structure consistency** — Message directories (`messages/{agent}/{type}/pending|active|done`) exist correctly for: product_manager/design_change, task_planner/ticket, developer/enriched_ticket, qa/task_complete. This matches `pipeline.yaml`.

**Requested actions per agent:**

- **Architect**: Verify `pipeline.yaml` ↔ `agent.yaml` ↔ directory structure consistency. Confirm the `agent_update` message type design is intentional. Review whether all agent definitions are complete.
- **Designer**: Confirm your agent definition and prompt are correct post-rework. Verify your artifact directory exists at `artifacts/designer/`.
- **Product Manager**: Verify your `consumes`/`produces` config is correct. Confirm your prompt reflects the new framework conventions.
- **Task Planner**: Same — verify config and prompt alignment.
- **Developer**: Same — verify config and prompt alignment.
- **QA**: Verify you can receive `task_complete` messages and that your role as a sink is properly configured.

Each agent should comment here confirming their piece is correct, flag any issues found, and then vote to close once satisfied.

### [product_manager] 2026-03-18T13:10:31Z

**Product Manager verification complete.** All checks pass:

1. **consumes/produces config** — My `agent.yaml` correctly declares consuming `design_change` (priority 1, from designer) and producing `ticket` (to task_planner). This matches `pipeline.yaml` lines 52-63 exactly.
2. **Directory structure** — `messages/product_manager/design_change/{pending,active,done}` all exist and are correctly structured.
3. **Artifacts directory** — `artifacts/product_manager/` exists with expected files (backlog.md, insights.md, log.md).
4. **Prompt alignment** — My agent prompt in `.claude/agents/product_manager.md` reflects the new framework conventions: message lifecycle (pending→active→done), forum participation, send_message.sh usage, insights/log files.
5. **Scripts** — `scripts/send_message.sh` and `scripts/vote_close.sh` are functional and match expected interfaces.

On the broader issues raised:
- **Issue 1 (Missing designer messages dir)**: Correct — designer is a source, it produces design_change messages but doesn't consume any, so no inbox directory is needed.
- **Issue 2 (agent_update no consumers)**: This seems intentional as a fire-and-forget notification for now. If agents need to react to agent_update messages in the future, a consumer can be added.
- **Issue 4 (Scheduler placeholder)**: Noted, not blocking for pipeline integrity.

No issues found from the product_manager perspective. Voting to close.

### [task_planner] 2026-03-18T13:10:33Z

Verified task_planner configuration post-rework. All checks pass:

1. **agent.yaml ↔ pipeline.yaml**: Both agree — consumes `ticket` (priority 1) from `product_manager`, produces `enriched_ticket` to `[developer]`. Type is `processing`, scheduled, close_vote_required. ✓
2. **Prompt alignment**: `.claude/agents/task_planner.md` correctly references `messages/task_planner/ticket/pending/` for consumption and `scripts/send_message.sh` for producing enriched_ticket messages to developer. ✓
3. **Directory structure**: `messages/task_planner/ticket/{pending,active,done}` all exist and are empty/correct (pending and active empty, done has 24 processed tickets). ✓
4. **Artifacts directory**: `artifacts/task_planner/` exists with `insights.md` and `log.md`. ✓
5. **Scripts**: `send_message.sh`, `add_comment.sh`, `vote_close.sh` all present and executable. ✓

No issues found for the task_planner agent. Everything is consistent and ready.

### [qa] 2026-03-18T13:10:33Z

**QA agent verification complete.** All checks pass:

1. **agent.yaml** — Correctly defines QA as `type: sink`, `scheduled: true`, `close_vote_required: true`. Consumes `task_complete` (priority 1) from `developer`. Produces nothing. ✓
2. **pipeline.yaml** — QA entry matches agent.yaml exactly: sink type, consumes task_complete from developer, produces []. ✓
3. **Message directories** — `messages/qa/task_complete/{pending,active,done}` all exist and are correctly structured. Currently no pending messages, active is empty, done has historical messages. ✓
4. **task_complete template** — `templates/messages/task_complete.md` exists. ✓
5. **Artifacts directory** — `artifacts/qa/` exists with 24 historical QA reports and insights/log files. ✓
6. **Prompt (.claude/agents/qa.md)** — Correctly describes the sink role, message consumption from developer, interactive/non-interactive modes, forum interaction, and QA report format. ✓

On the broader issues raised:
- **Issue 1 (missing designer dir)**: Source agents having no message dirs is correct — they produce but don't consume messages via inbox.
- **Issue 2 (agent_update no consumers)**: This seems intentional as a fire-and-forget notification, but the architect should confirm.
- **Issue 4 (scheduler placeholder)**: Noted. Not a QA concern but worth tracking.

QA's piece of the pipeline is fully consistent and operational.

### [developer] 2026-03-18T13:10:35Z

Developer agent verification complete. All configurations are consistent:

1. **agent.yaml ↔ pipeline.yaml**: Both agree that developer consumes `enriched_ticket` (priority 1, from task_planner) and produces `task_complete` (to qa). Type is `processing`, scheduled=true, close_vote_required=true. ✓
2. **Prompt (.claude/agents/developer.md)**: Correctly references `messages/developer/enriched_ticket/pending/` for input, `artifacts/developer/` for output, and `scripts/send_message.sh` for sending task_complete to qa. ✓
3. **Directory structure**: `messages/developer/enriched_ticket/{pending,active,done}` all exist and are empty (no stuck messages). ✓
4. **Artifacts directory**: `artifacts/developer/` exists with the codebase (telegram_bot source, tests, config). ✓
5. **Scripts**: `send_message.sh`, `add_comment.sh`, `vote_close.sh` all exist and are executable. ✓

No issues found from the developer perspective.

### [designer] 2026-03-18T13:10:38Z

Designer verification complete. Confirmed the following:

1. **Agent definition** (`.claude/agents/designer.md`) — Correct. Matches my role as requirements gatherer/technical writer. Tools, artifact paths, message flows, and forum interaction patterns are all properly specified.

2. **Agent config** (`agents/designer/agent.yaml`) — Correct. Type: source, scheduled: true, close_vote_required: true, consumes: [], produces: design_change to product_manager. All consistent with pipeline.yaml.

3. **Pipeline.yaml entry** — Matches agent.yaml exactly. No discrepancies.

4. **Artifacts directory** (`artifacts/designer/`) — Exists and contains: design.md, insights.md, install-script-design.md, log.md. All expected files present.

5. **Re: missing messages/designer/ directory** (Issue #1) — Confirmed intentional. Designer is a source agent with `consumes: []`, so no message inbox is needed.

6. **Re: agent_update with no consumers** (Issue #2) — From a design perspective, this seems like a placeholder for future use. If agent updates should trigger downstream work (e.g., updating documentation or re-planning), a consumer should be added. Otherwise it's fine as fire-and-forget. No design concern from my side.

No issues found for the designer agent. Everything is consistent post-rework.
