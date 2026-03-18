# Agent Pipeline Framework

## Overview

A pipeline framework where agents communicate through markdown messages and maintain their own artifact spaces. A shared forum provides cross-pipeline communication with consensus-based resolution.

## Core Concepts

### Agents

Three types:

- **Source**: Interactive with user. Produces messages for downstream agents. Has interactive and non-interactive mode.
- **Processing**: Autonomous. Consumes messages, updates own artifacts, produces messages. Has interactive and non-interactive mode.
- **Sink**: Interactive with user. Consumes messages. Has interactive and non-interactive mode.

Each agent is defined by:
- Name (unique identifier, kebab-case)
- Type (source | processing | sink)
- Description/role
- Consumed message types (with priority, lower number = higher priority)
- Produced message types
- Interactive mode description (source/sink required, processing optional)
- Non-interactive mode description

Optional flags:
- `scheduled: false` — agent is never launched by the scheduler (user-invoked only)
- `close_vote_required: false` — agent's vote is not needed to close forum topics

### Special Agents

- **Operator**: A non-scheduled source agent that serves as the user's direct interface. The user talks to the Operator to inject concerns, questions, or directives into the system via forum topics. The Operator's close-vote is never required.

### Artifacts

Located in `/artifacts/{agent-name}/`.

- Agent is the **sole writer** to its artifact directory
- All other agents have **read-only** access
- Internal organization is up to the owning agent
- Used to maintain the agent's domain state

### Messages

Located in `/messages/{agent-name}/` (organized by **consuming** agent).

- Each message is a single `.md` file
- Single producer, single consumer
- Lifecycle: `pending/` → `active/` → `done/`
- The scheduler determines work availability by checking `pending/`
- The agent is responsible for moving messages through the lifecycle (pending → active → done)

Message filename format: `{timestamp}-{producing-agent}-{message-type}.md`

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
- **Type**: {message-type}
- **Created**: {ISO-8601 timestamp}

## Content

{message content}
```

## Pipeline

Defined in `pipeline.yaml`. The scheduler reads this to determine:
- Which agents exist and their types
- What each agent consumes (and priority)
- What each agent produces
- How to route messages

## Scheduler

`scripts/run_scheduler.sh` — run manually or via cron.

Logic per pass:
1. For each agent, skip if already running (PID lock file check)
2. Check open forum topics — if any topic lacks the agent's close-vote, the agent has work
3. Check `messages/{agent-name}/pending/` — if any files exist, the agent has work
4. If work exists, launch the agent to execute a single task, then exit

Agents are **never started speculatively**. The scheduler guarantees work exists before launch.

## Scripts

- `scripts/run_scheduler.sh` — orchestrator
- `scripts/add_comment.sh <topic-file> <agent-name> <comment-text>` — appends comment to forum topic, clears all close-votes
- `scripts/vote_close.sh <topic-file> <agent-name>` — adds close-vote to forum topic

## Directory Structure

```
/
├── artifacts/{agent-name}/       # agent-owned state
├── messages/{agent-name}/        # per-consumer inboxes
│   ├── pending/
│   ├── active/
│   └── done/
├── forum/
│   ├── open/
│   └── closed/
├── agents/{agent-name}/
│   └── agent.yaml                # agent pipeline definition
├── .claude/agents/
│   └── {agent-name}.md           # agent prompt (Claude Code format)
├── scripts/
│   ├── run_scheduler.sh
│   ├── add_comment.sh
│   └── vote_close.sh
├── templates/                    # templates for generating agents
├── pipeline.yaml                 # pipeline manifest
└── framework.md                  # this file
```
