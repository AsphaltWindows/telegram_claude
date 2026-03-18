#!/usr/bin/env bash
set -euo pipefail

if [ $# -lt 3 ]; then
    echo "Usage: add_comment.sh <topic-file> <agent-name> <comment-text>"
    echo "Example: add_comment.sh forum/open/2024-01-15-designer-api-ambiguity.md product-manager \"I agree, we need to clarify the API scope.\""
    exit 1
fi

TOPIC_FILE="$1"
AGENT_NAME="$2"
COMMENT_TEXT="$3"
ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
FULL_PATH="$ROOT_DIR/$TOPIC_FILE"
TIMESTAMP=$(date -u +"%Y-%m-%dT%H:%M:%SZ")

if [ ! -f "$FULL_PATH" ]; then
    echo "Error: Topic file not found: $FULL_PATH"
    exit 1
fi

# Clear all existing close votes (remove lines matching VOTE:*)
sed -i '/^VOTE:.\+$/d' "$FULL_PATH"

# Append comment to end of file
cat >> "$FULL_PATH" <<EOF

### [${AGENT_NAME}] ${TIMESTAMP}

${COMMENT_TEXT}
EOF

echo "Comment added by '$AGENT_NAME'. All close votes cleared."
