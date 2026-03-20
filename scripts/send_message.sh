#!/usr/bin/env bash
set -euo pipefail

# Send a message from one agent to another.
# Usage: send_message.sh <from> <to> <message_type> <message_name> <content>
#
# Validates that the message type exists in pipeline.yaml and that the
# recipient consumes it, then writes the message file to the correct inbox.

if [ $# -lt 5 ]; then
    echo "Usage: send_message.sh <from> <to> <message_type> <message_name> <content>"
    exit 1
fi

FROM="$1"
TO="$2"
MESSAGE_TYPE="$3"
MESSAGE_NAME="$4"
CONTENT="$5"

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
PIPELINE="$ROOT_DIR/pipeline.yaml"

# Validate message type exists in pipeline.yaml message_types section
IN_MESSAGE_TYPES=false
TYPE_FOUND=false

while IFS= read -r line; do
    if echo "$line" | grep -q '^message_types:'; then
        IN_MESSAGE_TYPES=true
        continue
    fi
    if echo "$line" | grep -q '^[a-z_]*:' && ! echo "$line" | grep -q '^message_types:'; then
        [ "$IN_MESSAGE_TYPES" = true ] && break
    fi
    if [ "$IN_MESSAGE_TYPES" = true ]; then
        if echo "$line" | grep -q "^\s*-\?\s*name:\s*${MESSAGE_TYPE}\s*$"; then
            TYPE_FOUND=true
            break
        fi
    fi
done < "$PIPELINE"

if [ "$TYPE_FOUND" = false ]; then
    echo "Error: message type '${MESSAGE_TYPE}' not found in pipeline.yaml message_types"
    exit 1
fi

# Validate recipient agent consumes this message type
PENDING_DIR="$ROOT_DIR/messages/${TO}/${MESSAGE_TYPE}/pending"

if [ ! -d "$PENDING_DIR" ]; then
    echo "Error: agent '${TO}' does not have an inbox for message type '${MESSAGE_TYPE}'"
    echo "Expected directory: ${PENDING_DIR}"
    exit 1
fi

# Write the message
MESSAGE_FILE="${PENDING_DIR}/${FROM}-${MESSAGE_NAME}.md"

if [ -f "$MESSAGE_FILE" ]; then
    echo "Error: message file already exists: ${MESSAGE_FILE}"
    exit 1
fi

cat > "$MESSAGE_FILE" << EOF
# ${MESSAGE_NAME}

## Metadata
- **From**: ${FROM}
- **To**: ${TO}

## Content

${CONTENT}
EOF

echo "Message sent: ${MESSAGE_FILE}"
