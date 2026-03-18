#!/usr/bin/env bash
set -euo pipefail

# Load nvm and use a compatible Node version
export NVM_DIR="$HOME/.nvm"
[ -s "$NVM_DIR/nvm.sh" ] && . "$NVM_DIR/nvm.sh"
nvm use node > /dev/null 2>&1

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
PIPELINE="$ROOT_DIR/pipeline.yaml"
LOCK_DIR="$ROOT_DIR/.locks"
INTERVAL="${1:-15}"

mkdir -p "$LOCK_DIR"

while true; do

# Parse scheduled agent names from pipeline.yaml (skip agents with scheduled: false)
AGENTS=""
CURRENT_AGENT=""
IS_SCHEDULED=true

while IFS= read -r line; do
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
if [ -n "$CURRENT_AGENT" ] && [ "$IS_SCHEDULED" = true ]; then
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
    WORK_TYPE=""
    WORK_TARGET=""

    # Priority 1: Check forum topics without this agent's close-vote
    for TOPIC in "$ROOT_DIR"/forum/open/*.md; do
        [ -f "$TOPIC" ] || continue
        if ! grep -q "^VOTE:${AGENT}$" "$TOPIC"; then
            HAS_WORK=true
            WORK_TYPE="forum"
            WORK_TARGET="$TOPIC"
            break
        fi
    done

    # Priority 2: Check pending messages
    if [ "$HAS_WORK" = false ]; then
        PENDING_DIR="$ROOT_DIR/messages/${AGENT}/pending"
        if [ -d "$PENDING_DIR" ]; then
            FIRST_MSG=$(ls -1t "$PENDING_DIR"/*.md 2>/dev/null | tail -1 || true)
            if [ -n "$FIRST_MSG" ]; then
                HAS_WORK=true
                WORK_TYPE="message"
                WORK_TARGET="$FIRST_MSG"
            fi
        fi
    fi

    if [ "$HAS_WORK" = false ]; then
        echo "[$AGENT] No pending work."
        continue
    fi

    echo "[$AGENT] Work found: $WORK_TYPE ($WORK_TARGET)"

    # Verify agent prompt exists in .claude/agents/
    PROMPT_FILE="$ROOT_DIR/.claude/agents/${AGENT}.md"

    if [ ! -f "$PROMPT_FILE" ]; then
        echo "[$AGENT] No .claude/agents/${AGENT}.md found, skipping."
        continue
    fi

    LOG_DIR="$ROOT_DIR/logs"
    mkdir -p "$LOG_DIR"
    LOG_FILE="$LOG_DIR/${AGENT}-$(date -u +%Y%m%dT%H%M%SZ).log"

    # Build the prompt based on work type
    if [ "$WORK_TYPE" = "forum" ]; then
        WORK_PROMPT="You have been launched by the scheduler. You have a forum topic to review: $WORK_TARGET"
    else
        WORK_PROMPT="You have been launched by the scheduler. You have a pending message to process: $WORK_TARGET"
    fi

    # Launch agent in background
    (
        echo "$BASHPID" > "$LOCK_FILE"

        echo "[$AGENT] Launching (work: $WORK_TYPE)..."

        claude -p \
            --agent "$AGENT" \
            --dangerously-skip-permissions \
            "$WORK_PROMPT" \
            >> "$LOG_FILE" 2>&1

        EXIT_CODE=$?
        echo "[$AGENT] Finished with exit code $EXIT_CODE (log: $LOG_FILE)"

        rm -f "$LOCK_FILE"
    ) &

done

echo "Scheduler pass complete. Sleeping ${INTERVAL}s..."
sleep "$INTERVAL"

done
