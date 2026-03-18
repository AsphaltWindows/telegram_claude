#!/usr/bin/env bash
set -euo pipefail

# ============================================================
# Telegram Bot Launcher
# Edit the BOT_TOKEN below with your actual Telegram bot token
# ============================================================
BOT_TOKEN="8727225239:AAFBEyRFy8gwm_QdpRiyL3YWj4VIjn2_iI8"

# Path to the pipeline YAML file (relative to project root, or absolute)
PIPELINE_YAML="pipeline.yaml"

# Change to the project root (two levels up from this script, which lives
# in artifacts/developer/).
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR/../.."

# ============================================================
# Source nvm if available — needed when running from systemd/cron
# where the user's shell profile isn't loaded
# ============================================================
if [ -s "${NVM_DIR:-$HOME/.nvm}/nvm.sh" ]; then
    source "${NVM_DIR:-$HOME/.nvm}/nvm.sh"
fi

# Validate that the user has set their bot token
if [ "$BOT_TOKEN" = "YOUR_TOKEN_HERE" ]; then
    echo "Error: BOT_TOKEN is not set. Edit run_bot.sh and replace YOUR_TOKEN_HERE with your Telegram bot token." >&2
    exit 1
fi

# Resolve PIPELINE_YAML to an absolute path
if [[ "$PIPELINE_YAML" != /* ]]; then
    PIPELINE_YAML="$(pwd)/$PIPELINE_YAML"
fi

# Validate that the pipeline YAML file exists
if [ ! -f "$PIPELINE_YAML" ]; then
    echo "Error: Pipeline YAML file not found: $PIPELINE_YAML" >&2
    exit 1
fi

# Export environment variables for the bot process
export TELEGRAM_BOT_TOKEN="$BOT_TOKEN"
export PIPELINE_YAML

# Start the bot — add the bot source directory to PYTHONPATH so that
# ``python -m telegram_bot`` resolves correctly from the project root.
export PYTHONPATH="${SCRIPT_DIR}${PYTHONPATH:+:$PYTHONPATH}"
exec python -m telegram_bot
