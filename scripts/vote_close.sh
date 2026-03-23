#!/usr/bin/env bash
set -euo pipefail

if [ $# -ne 2 ]; then
    echo "Usage: vote_close.sh <topic-file> <agent-name>"
    echo "Example: vote_close.sh forum/open/2024-01-15-designer-api-ambiguity.md designer"
    exit 1
fi

TOPIC_FILE="$1"
AGENT_NAME="$2"
ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
FULL_PATH="$ROOT_DIR/$TOPIC_FILE"

if [ ! -f "$FULL_PATH" ]; then
    echo "Error: Topic file not found: $FULL_PATH"
    exit 1
fi

# Check if agent already voted
if grep -q "^VOTE:${AGENT_NAME}$" "$FULL_PATH"; then
    echo "Agent '$AGENT_NAME' has already voted to close this topic."
    exit 0
fi

# Add vote after the "## Close Votes" line
sed -i "/^## Close Votes$/a VOTE:${AGENT_NAME}" "$FULL_PATH"

echo "Vote added for '$AGENT_NAME'."

# Check if all required agents have voted
# Agents with close_vote_required: false are excluded
PIPELINE="$ROOT_DIR/pipeline.yaml"
REQUIRED_AGENTS=""
CURRENT_AGENT=""
VOTE_REQUIRED=true

while IFS= read -r line; do
    if echo "$line" | grep -q '^\s*-\?\s*name:'; then
        # Save previous agent if vote was required
        if [ -n "$CURRENT_AGENT" ] && [ "$VOTE_REQUIRED" = true ]; then
            REQUIRED_AGENTS="$REQUIRED_AGENTS $CURRENT_AGENT"
        fi
        CURRENT_AGENT=$(echo "$line" | sed 's/.*name:\s*//' | tr -d ' ')
        VOTE_REQUIRED=true
    elif echo "$line" | grep -q '^\s*close_vote_required:\s*false'; then
        VOTE_REQUIRED=false
    fi
done < "$PIPELINE"
# Don't forget the last agent
if [ -n "$CURRENT_AGENT" ] && [ "$VOTE_REQUIRED" = true ]; then
    REQUIRED_AGENTS="$REQUIRED_AGENTS $CURRENT_AGENT"
fi

ALL_VOTED=true
for AGENT in $REQUIRED_AGENTS; do
    if ! grep -q "^VOTE:${AGENT}$" "$FULL_PATH"; then
        ALL_VOTED=false
        break
    fi
done

if [ "$ALL_VOTED" = true ]; then
    CLOSED_DIR="$ROOT_DIR/forum/closed"
    mv "$FULL_PATH" "$CLOSED_DIR/"
    echo "All agents voted. Topic moved to closed."
fi
