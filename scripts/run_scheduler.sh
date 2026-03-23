#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
PIPELINE="$ROOT_DIR/pipeline.yaml"
LOCK_DIR="$ROOT_DIR/.locks"

mkdir -p "$LOCK_DIR"

while true; do

# Parse scheduled agent names from pipeline.yaml (skip agents with scheduled: false)
# Only parse names under the 'agents:' section, not 'message_types:' or other sections
AGENTS=""
CURRENT_AGENT=""
IS_SCHEDULED=true
IN_AGENTS_SECTION=false

while IFS= read -r line; do
    # Detect top-level section headers (no leading whitespace, ends with colon)
    if echo "$line" | grep -q '^[a-z_]*:'; then
        if echo "$line" | grep -q '^agents:'; then
            IN_AGENTS_SECTION=true
        else
            # Entering a different section — flush any pending agent
            if [ "$IN_AGENTS_SECTION" = true ] && [ -n "$CURRENT_AGENT" ] && [ "$IS_SCHEDULED" = true ]; then
                AGENTS="$AGENTS $CURRENT_AGENT"
            fi
            IN_AGENTS_SECTION=false
            CURRENT_AGENT=""
        fi
        continue
    fi
    [ "$IN_AGENTS_SECTION" = true ] || continue
    if echo "$line" | grep -q '^\s*-\?\s*name:'; then
        if [ -n "$CURRENT_AGENT" ] && [ "$IS_SCHEDULED" = true ]; then
            AGENTS="$AGENTS $CURRENT_AGENT"
        fi
        CURRENT_AGENT=$(echo "$line" | sed 's/.*name:\s*//' | tr -d ' ')
        IS_SCHEDULED=true
    elif echo "$line" | grep -q '^\s*scheduled:\s*false'; then
        IS_SCHEDULED=false
    fi
done < "$PIPELINE"
if [ "$IN_AGENTS_SECTION" = true ] && [ -n "$CURRENT_AGENT" ] && [ "$IS_SCHEDULED" = true ]; then
    AGENTS="$AGENTS $CURRENT_AGENT"
fi

if [ -z "$AGENTS" ]; then
    echo "No agents defined in pipeline.yaml"
    exit 0
fi

for AGENT in $AGENTS; do
    LOCK_FILE="$LOCK_DIR/${AGENT}.pid"

    # Check if agent is already running
    if [ -f "$LOCK_FILE" ]; then
        PID=$(cat "$LOCK_FILE")
        if kill -0 "$PID" 2>/dev/null; then
            echo "[$AGENT] Already running (PID $PID), skipping."
            continue
        else
            echo "[$AGENT] Stale lock file found, removing."
            rm -f "$LOCK_FILE"
        fi
    fi

    HAS_WORK=false

    # Check if this is a script node (skip forum checks for script nodes)
    AGENT_SCRIPT_CHECK=$(grep '^\s*script:' "$ROOT_DIR/agents/${AGENT}/agent.yaml" 2>/dev/null || true)

    if [ -z "$AGENT_SCRIPT_CHECK" ]; then
        # Agent node — check forum topics without this agent's close-vote
        for TOPIC in "$ROOT_DIR"/forum/open/*.md; do
            [ -f "$TOPIC" ] || continue
            if ! grep -q "^VOTE:${AGENT}$" "$TOPIC"; then
                HAS_WORK=true
                break
            fi
        done
    fi

    # Check pending messages across all message-type subdirectories
    if [ "$HAS_WORK" = false ]; then
        AGENT_MSG_DIR="$ROOT_DIR/messages/${AGENT}"
        if [ -d "$AGENT_MSG_DIR" ]; then
            for TYPE_DIR in "$AGENT_MSG_DIR"/*/pending; do
                [ -d "$TYPE_DIR" ] || continue
                if ls "$TYPE_DIR"/*.md &>/dev/null; then
                    HAS_WORK=true
                    break
                fi
            done
        fi
    fi

    if [ "$HAS_WORK" = false ]; then
        echo "[$AGENT] No pending work."
        continue
    fi

    echo "[$AGENT] Work found, launching."

    # Read agent type and check for script runner
    AGENT_YAML="$ROOT_DIR/agents/${AGENT}/agent.yaml"
    AGENT_TYPE=$(grep '^\s*type:' "$AGENT_YAML" | sed 's/.*type:\s*//' | tr -d ' ')
    AGENT_SCRIPT=$(grep '^\s*script:' "$AGENT_YAML" 2>/dev/null | sed 's/.*script:\s*//' | tr -d ' ')

    if [ -n "$AGENT_SCRIPT" ]; then
        # Script-based node — run the script directly
        SCRIPT_PATH="$ROOT_DIR/$AGENT_SCRIPT"

        if [ ! -f "$SCRIPT_PATH" ]; then
            echo "[$AGENT] Script not found: $AGENT_SCRIPT, skipping."
            continue
        fi

        if [ ! -x "$SCRIPT_PATH" ]; then
            echo "[$AGENT] Script not executable: $AGENT_SCRIPT, skipping."
            continue
        fi

        # Launch script in background
        (
            echo "$$" > "$LOCK_FILE"
            echo "[$AGENT] Launching script (type: $AGENT_TYPE): $AGENT_SCRIPT"
            "$SCRIPT_PATH" "$ROOT_DIR" "$AGENT"
            rm -f "$LOCK_FILE"
        ) &
    else
        # LLM-based agent — use Claude Code prompt file
        PROMPT_FILE="$ROOT_DIR/.claude/agents/${AGENT}.md"

        if [ ! -f "$PROMPT_FILE" ]; then
            echo "[$AGENT] No .claude/agents/${AGENT}.md found, skipping."
            continue
        fi

        # Launch agent in background
        (
            echo "$$" > "$LOCK_FILE"

            echo "[$AGENT] Launching (type: $AGENT_TYPE)..."

            # --- AGENT LAUNCH COMMAND ---
            # Replace this with your LLM invocation.
            # The agent should receive:
            #   1. Its system prompt (.claude/agents/{name}.md)
            #   2. Access to the ROOT_DIR for reading artifacts, messages, and forum topics
            #
            # The agent is responsible for finding its own work:
            #   - Check forum/open/ for topics needing its attention
            #   - Check messages/{name}/{type}/pending/ for pending messages
            #   - Process work in priority order (forum first, then messages)
            #   - Move messages through pending/ -> active/ -> done/
            #
            # Example (placeholder):
            # your-llm-cli --system-prompt "$PROMPT_FILE" --root "$ROOT_DIR"
            echo "[$AGENT] TODO: Invoke LLM agent here with prompt=$PROMPT_FILE"

            rm -f "$LOCK_FILE"
        ) &
    fi

done

echo "Scheduler pass complete."
INTERVAL=$(grep '^\s*scheduler_interval:' "$PIPELINE" | sed 's/.*scheduler_interval:\s*//' | tr -d ' ')
INTERVAL="${INTERVAL:-20}"
sleep "$INTERVAL"
done
