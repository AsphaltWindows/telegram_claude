#!/usr/bin/env bash
set -euo pipefail

# ============================================================
# Install Telegram Bot into an agent-pipeline project
# Usage: ./install_telegram_bot.sh [--force] <target-directory>
# ============================================================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SOURCE_DIR="$SCRIPT_DIR/artifacts/developer"

# ------------------------------------------------------------------
# Usage
# ------------------------------------------------------------------
usage() {
    echo "Usage: $0 [--force] <target-project-directory>" >&2
    echo "" >&2
    echo "Installs the Telegram bot integration into a project that" >&2
    echo "already has the agent pipeline set up (pipeline.yaml)." >&2
    echo "" >&2
    echo "Options:" >&2
    echo "  --force    Overwrite existing telegram bot files if present" >&2
    exit 1
}

# ------------------------------------------------------------------
# Argument parsing
# ------------------------------------------------------------------
FORCE=false
TARGET=""

while [[ $# -gt 0 ]]; do
    case "$1" in
        --force) FORCE=true; shift ;;
        -*) echo "Error: Unknown option '$1'" >&2; usage ;;
        *)
            if [ -n "$TARGET" ]; then
                echo "Error: Multiple target directories specified." >&2
                usage
            fi
            TARGET="$1"; shift
            ;;
    esac
done

if [ -z "$TARGET" ]; then
    usage
fi

# ------------------------------------------------------------------
# Pre-flight checks
# ------------------------------------------------------------------

# Check target directory exists
if [ ! -d "$TARGET" ]; then
    echo "Error: '$TARGET' is not a directory or does not exist." >&2
    exit 1
fi

# Resolve to absolute path
TARGET="$(cd "$TARGET" && pwd)"

# Check pipeline.yaml exists
if [ ! -f "$TARGET/pipeline.yaml" ]; then
    echo "Error: $TARGET/pipeline.yaml not found — is this an agent pipeline project?" >&2
    exit 1
fi

# Check for existing files (unless --force)
if [ "$FORCE" = false ]; then
    EXISTING=()
    [ -d "$TARGET/telegram_bot" ] && EXISTING+=("$TARGET/telegram_bot/")
    [ -f "$TARGET/run_bot.sh" ] && EXISTING+=("$TARGET/run_bot.sh")
    [ -f "$TARGET/telegram_bot.yaml" ] && EXISTING+=("$TARGET/telegram_bot.yaml")

    if [ ${#EXISTING[@]} -gt 0 ]; then
        echo "Error: The following files already exist:" >&2
        for f in "${EXISTING[@]}"; do
            echo "  - $f" >&2
        done
        echo "" >&2
        echo "Use --force to overwrite." >&2
        exit 1
    fi
fi

# Check pip is available
if ! command -v pip &>/dev/null; then
    echo "Error: pip is not available. Please install pip first." >&2
    exit 1
fi

# ------------------------------------------------------------------
# Install Python dependencies
# ------------------------------------------------------------------
echo "Installing Python dependencies..."
pip install python-telegram-bot pyyaml

# ------------------------------------------------------------------
# Copy telegram_bot/ Python package (recursive, .py files only)
# ------------------------------------------------------------------
echo "Copying telegram_bot/ Python package..."
mkdir -p "$TARGET/telegram_bot"

# Use find to copy .py files recursively, excluding tests/ and __pycache__/
cd "$SOURCE_DIR/telegram_bot"
find . -name "*.py" \
    -not -path "./tests/*" \
    -not -path "./__pycache__/*" \
    -not -path "./.pytest_cache/*" \
    -not -name "*.pyc" \
    -print0 | while IFS= read -r -d '' file; do
    dir="$(dirname "$file")"
    mkdir -p "$TARGET/telegram_bot/$dir"
    cp "$SOURCE_DIR/telegram_bot/$file" "$TARGET/telegram_bot/$file"
done
cd "$SCRIPT_DIR"

# ------------------------------------------------------------------
# Generate run_bot.sh
# ------------------------------------------------------------------
echo "Generating run_bot.sh..."
cat <<'EOF' > "$TARGET/run_bot.sh"
#!/usr/bin/env bash
set -euo pipefail

# ============================================================
# Telegram Bot Launcher
# Edit the BOT_TOKEN below with your actual Telegram bot token
# ============================================================
BOT_TOKEN="YOUR_TOKEN_HERE"

# Path to the pipeline YAML file (relative to project root, or absolute)
PIPELINE_YAML="pipeline.yaml"

# Change to the project root (where this script lives)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

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

exec python -m telegram_bot
EOF
chmod +x "$TARGET/run_bot.sh"

# ------------------------------------------------------------------
# Generate telegram_bot.yaml
# ------------------------------------------------------------------
echo "Generating telegram_bot.yaml..."
cat <<'EOF' > "$TARGET/telegram_bot.yaml"
# Telegram user IDs allowed to interact with the bot
allowed_users:
  - 000000000

# Idle timeout in seconds before auto-ending a session
idle_timeout: 600

# Graceful shutdown message sent to agent on /end or timeout
shutdown_message: "Record the product of this conversation as appropriate for your role and exit."

# Optional: absolute path to the claude CLI binary.
# Use this when claude is not on PATH (e.g. when running from systemd/cron
# and nvm sourcing alone is insufficient, or when multiple versions are
# installed and you want to pin a specific one).
# If unset, the bot resolves "claude" from PATH.
# claude_path: "/home/user/.nvm/versions/node/v22.14.0/bin/claude"
EOF

# ------------------------------------------------------------------
# Post-install message
# ------------------------------------------------------------------
echo ""
echo "Telegram bot installed to $TARGET"
echo ""
echo "Next steps:"
echo "  1. Edit run_bot.sh and set your BOT_TOKEN"
echo "  2. Edit telegram_bot.yaml and set your allowed_users (Telegram user IDs)"
echo "  3. Run: ./run_bot.sh"
