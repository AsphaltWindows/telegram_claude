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
# Discover agents from agents/*/agent.yaml files
# Agents with close_vote_required: false are excluded
REQUIRED_AGENTS=""

for AGENT_YAML in "$ROOT_DIR"/agents/*/agent.yaml; do
    [ -f "$AGENT_YAML" ] || continue
    AGENT_DIR_NAME=$(basename "$(dirname "$AGENT_YAML")")
    # Check if close_vote_required is explicitly set to false
    if grep -q '^\s*close_vote_required:\s*false' "$AGENT_YAML"; then
        continue
    fi
    REQUIRED_AGENTS="$REQUIRED_AGENTS $AGENT_DIR_NAME"
done

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
