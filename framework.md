# Agent Pipeline Framework

## Overview

A pipeline framework where agents communicate through markdown messages and maintain their own artifact spaces. A shared forum provides cross-pipeline communication with consensus-based resolution.

## Core Concepts

### Pipeline Nodes

The pipeline consists of **nodes** — named units that consume messages, maintain artifacts, and produce messages. There are two kinds of nodes:

- **Agents** — LLM-powered nodes invoked via Claude Code with a system prompt (`.claude/agents/{name}.md`). Agents can participate in forum discussions and vote to close topics.
- **Script nodes** — shell scripts that run without LLM involvement. They have the same pipeline infrastructure (artifacts, message inboxes) but cannot participate in forum discussions. Their `close_vote_required` is always `false`.

### Agents

Three types:

- **Source**: Interactive with user. Produces messages for downstream agents. Has interactive and non-interactive mode.
- **Processing**: Autonomous. Consumes messages, updates own artifacts, produces messages. Has interactive and non-interactive mode.
- **Sink**: Interactive with user. Consumes messages. Has interactive and non-interactive mode.

Each agent is defined by:
- Name (unique identifier, snake_case; also used as directory names)
- Type (source | processing | sink)
- Description/role
- Consumed message types (with priority, lower number = higher priority)
- Produced message types (with target consumers)
- Interactive mode description (source/sink required, processing optional)
- Non-interactive mode description

Optional flags:
- `scheduled: false` — agent is never launched by the scheduler (user-invoked only)
- `close_vote_required: false` — agent's vote is not needed to close forum topics

### Script Nodes

A script node is a processing node that runs a shell script instead of an LLM. It participates in the same pipeline infrastructure — it has its own artifacts directory, messages inbox, and is scheduled by `run_scheduler.sh` — but requires no LLM invocation or agent prompt file.

Script nodes are defined by setting the `script:` field in their `agents/{name}/agent.yaml` to a path (relative to the project root) of an executable shell script. When the scheduler detects work for a script node, it runs the script instead of launching an agent.

The script receives two positional arguments:
1. `$1` — the project root directory
2. `$2` — the node name

The script is responsible for:
- Checking `messages/{name}/{message-type}/pending/` for pending messages across its consumed types
- Processing messages and moving them through `pending/` → `active/` → `done/`
- Using `scripts/send_message.sh` to send output messages to downstream consumers
- Writing to its own `artifacts/{name}/` directory

Script nodes always have `close_vote_required: false` and `type: processing`.

### Special Agents

- **Operator**: A non-scheduled source agent that serves as the user's direct interface. The user talks to the Operator to inject concerns, questions, or directives into the system via forum topics. The Operator's close-vote is never required.

### Artifacts

Located in `/artifacts/{agent-name}/`.

- Agent is the **sole writer** to its artifact directory
- All other agents have **read-only** access
- Internal organization is up to the owning agent
- Used to maintain the agent's domain state

### Insights

Each agent maintains an `artifacts/{agent-name}/insights.md` file.

- **Loaded at startup** — the agent reads this file before doing any work
- **Written post-task** — after completing a task that required significant investigation, the agent appends an insight if it discovered something specific that would have helped it find the right path earlier
- Insights should be concise and actionable — not a log of what happened, but a lesson learned
- Agents should consult their insights during work to avoid repeating past mistakes

### Session Log

Each agent maintains a `artifacts/{agent-name}/log.md` file.

- **Written at end of session** — before exiting, the agent appends a timestamped summary of what it did during the session
- **Not loaded at startup** — the agent is aware the log exists and may read it if needed, but does not load it automatically
- Summaries should be brief: what work was found, what actions were taken, what was produced

### Messages

Located in `/messages/{agent-name}/{message-type}/` (organized by **consuming** agent and **message type**).

- Each message is a single `.md` file
- Single producer, single consumer
- Each consumed message type has its own subdirectory with the full lifecycle: `pending/` → `active/` → `done/`
- The scheduler determines work availability by checking for any `pending/` files across all message-type subdirectories
- The agent is responsible for moving messages through the lifecycle (pending → active → done)
- Agents process message types in priority order (lower number = higher priority in their `consumes` list)

Message filename format: `{producing-agent}-{message-name}.md`

The `{message-name}` is a short descriptive slug for the specific message (e.g., `add_reviewer_agent`, `fix_parser_bug`). The message type is encoded in the directory path, not the filename. Timestamps are not needed in the filename — messages are write-only and file creation time serves as the timestamp.

### Message Types

All message types are registered in the `message_types` section of `pipeline.yaml`. Each entry has a name (snake_case), description, and path to a template file. The registry is the canonical list of types — agents' `consumes` and `produces` entries reference these by name. Message type names are used as directory names, so snake_case is required.

### Message Templates

Each message type has a template file in `templates/messages/{message-type}.md`. Templates document the expected content structure for that message type. Agents use `scripts/send_message.sh` to create messages (which handles metadata and file placement); the templates serve as guidance for what content to pass.

### Forum

Located in `/forum/open/` and `/forum/closed/`.

- Any agent can create a topic during task execution
- Used for problems, ambiguities, or cross-pipeline communication
- **Highest priority** for all agents — checked before messages
- A topic is closed only when **every agent** has voted to close it
- Any new comment **clears all existing close-votes**
- Agents should execute work in response to forum topics when the issue falls under their responsibility

Forum topic filename format: `{timestamp}-{creating-agent}-{slug}.md`

### Forum Topic Structure

```markdown
# Topic Title

## Metadata
- **Created by**: {agent-name}
- **Created**: {ISO-8601 timestamp}
- **Status**: open

## Close Votes
<!-- ONE VOTE PER LINE: VOTE:{agent-name} -->

## Discussion

### [{agent-name}] {ISO-8601 timestamp}

{comment content}
```

### Message Structure

```markdown
# {Title}

## Metadata
- **From**: {producing-agent-name}
- **To**: {consuming-agent-name}

## Content

{message content}
```

The message type is determined by the directory the message lives in. The creation timestamp is the file's filesystem creation time.

### No-Work Investigation

When an agent is launched by the scheduler in non-interactive mode but cannot find any work to do, something is wrong — the scheduler only launches agents when it detects pending work.

The agent should:
1. **Investigate** — check its pending messages, open forum topics, and any other expected work sources to understand why the scheduler thought work existed but the agent cannot find it
2. **Attempt low-impact self-unblocking** — if the cause is simple (e.g., a malformed message filename, a message it already processed but didn't move to done), fix it
3. **Escalate if needed** — if the cause is unclear or complex, open a forum topic describing what happened so other agents can help diagnose the issue
4. **Log the incident** — record what happened in the session log regardless of outcome

## Pipeline

Defined in `pipeline.yaml`. The scheduler reads this to determine:
- Which message types exist in the system
- Which agents exist and their types
- What each agent consumes (and priority)
- What each agent produces
- How to route messages

The `message_types` section defines all message types used in the pipeline. Each type has a name and description. This serves as the canonical registry — the `consumes` and `produces` entries on agents reference these types by name.

Each `produces` entry includes a `to` field listing the consuming agents. This is the authoritative routing table — the producer writes to `messages/{consumer}/{message-type}/pending/` for each agent in the `to` list. The `consumes` entries on receiving agents are the inverse view. The init script and architect use both to create the per-type inbox directories (`messages/{agent}/{message-type}/{pending,active,done}/`).

## Scheduler

`scripts/run_scheduler.sh` — long-running process that continuously monitors the pipeline for work.

The scheduler runs in an infinite loop. The interval between passes is configured by `scheduler_interval` in `pipeline.yaml` (in seconds, default 20). Each pass:
1. For each scheduled node, skip if already running (PID lock file check)
2. For agents: check open forum topics — if any topic lacks the agent's close-vote, the node has work
3. Check `messages/{node-name}/*/pending/` — if any files exist in any message-type subdirectory, the node has work
4. If work exists, launch the node in the background — agents find and process their own work then exit; script nodes run their script then exit

Nodes are **never started speculatively**. The scheduler guarantees work exists before launch, but does not tell the node what to do — the node is responsible for finding and processing its own work.

## Scripts

- `scripts/run_scheduler.sh` — orchestrator
- `scripts/send_message.sh <from> <to> <message-type> <message-name> <content>` — creates a message in the recipient's inbox. Validates the message type exists and the recipient consumes it. Agents and script nodes should use this instead of writing message files directly.
- `scripts/add_comment.sh <topic-file> <agent-name> <comment-text>` — appends comment to forum topic, clears all close-votes
- `scripts/vote_close.sh <topic-file> <agent-name>` — adds close-vote to forum topic

## Directory Structure

```
/
├── artifacts/{node-name}/        # node-owned state (agents and script nodes)
├── messages/{node-name}/         # per-consumer inboxes
│   └── {message-type}/          # subdirectory per consumed message type
│       ├── pending/
│       ├── active/
│       └── done/
├── forum/
│   ├── open/
│   └── closed/
├── agents/{node-name}/
│   └── agent.yaml                # node pipeline definition
├── .claude/agents/
│   └── {agent-name}.md           # agent prompt (Claude Code format, agents only)
├── scripts/
│   ├── run_scheduler.sh
│   ├── send_message.sh
│   ├── add_comment.sh
│   ├── vote_close.sh
│   └── {script-node-name}.sh     # script node entry points
├── templates/                    # templates for generating nodes and messages
│   └── messages/{message-type}.md  # per-type message templates
├── pipeline.yaml                 # pipeline manifest
└── framework.md                  # this file
```
