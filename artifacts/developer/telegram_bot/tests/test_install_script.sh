#!/usr/bin/env bash
set -euo pipefail

# ============================================================
# Tests for install_telegram_bot.sh
# ============================================================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$SCRIPT_DIR/../../../.."
INSTALL_SCRIPT="$PROJECT_ROOT/install_telegram_bot.sh"

PASS=0
FAIL=0
TESTS_RUN=0

pass() {
    PASS=$((PASS + 1))
    TESTS_RUN=$((TESTS_RUN + 1))
    echo "  ✓ $1"
}

fail() {
    FAIL=$((FAIL + 1))
    TESTS_RUN=$((TESTS_RUN + 1))
    echo "  ✗ $1"
    if [ -n "${2:-}" ]; then
        echo "    $2"
    fi
}

cleanup() {
    rm -rf "$TMPBASE"
}
trap cleanup EXIT

TMPBASE="$(mktemp -d)"

echo "=== Test 1: No-args invocation ==="
if "$INSTALL_SCRIPT" 2>/dev/null; then
    fail "Should exit non-zero with no args"
else
    pass "Exits non-zero with no args"
fi

echo ""
echo "=== Test 2: Non-existent target ==="
if "$INSTALL_SCRIPT" /tmp/nonexistent_dir_xyz_test_$$_9999 2>/dev/null; then
    fail "Should exit non-zero for non-existent target"
else
    pass "Exits non-zero for non-existent target"
fi

echo ""
echo "=== Test 3: Target without pipeline.yaml ==="
EMPTY_DIR="$TMPBASE/empty"
mkdir -p "$EMPTY_DIR"
if "$INSTALL_SCRIPT" "$EMPTY_DIR" 2>/dev/null; then
    fail "Should exit non-zero without pipeline.yaml"
else
    pass "Exits non-zero without pipeline.yaml"
fi

echo ""
echo "=== Test 4: Successful install ==="
GOOD_DIR="$TMPBASE/project"
mkdir -p "$GOOD_DIR"
touch "$GOOD_DIR/pipeline.yaml"

if "$INSTALL_SCRIPT" "$GOOD_DIR" 2>&1; then
    pass "Install exits zero"
else
    fail "Install should exit zero" "Exit code: $?"
fi

# Check telegram_bot/ exists with expected .py files
for pyfile in __init__.py bot.py config.py session.py discovery.py __main__.py; do
    if [ -f "$GOOD_DIR/telegram_bot/$pyfile" ]; then
        pass "telegram_bot/$pyfile exists"
    else
        fail "telegram_bot/$pyfile should exist"
    fi
done

# No tests/ directory
if [ -d "$GOOD_DIR/telegram_bot/tests" ]; then
    fail "telegram_bot/tests/ should NOT exist"
else
    pass "telegram_bot/tests/ excluded"
fi

# No __pycache__
if [ -d "$GOOD_DIR/telegram_bot/__pycache__" ]; then
    fail "telegram_bot/__pycache__/ should NOT exist"
else
    pass "__pycache__/ excluded"
fi

# No .pyc files
PYC_COUNT=$(find "$GOOD_DIR/telegram_bot/" -name "*.pyc" 2>/dev/null | wc -l)
if [ "$PYC_COUNT" -eq 0 ]; then
    pass "No .pyc files"
else
    fail "Should have no .pyc files" "Found $PYC_COUNT"
fi

# run_bot.sh checks
if [ -f "$GOOD_DIR/run_bot.sh" ]; then
    pass "run_bot.sh exists"
else
    fail "run_bot.sh should exist"
fi

if [ -x "$GOOD_DIR/run_bot.sh" ]; then
    pass "run_bot.sh is executable"
else
    fail "run_bot.sh should be executable"
fi

if grep -q 'YOUR_TOKEN_HERE' "$GOOD_DIR/run_bot.sh"; then
    pass "run_bot.sh contains YOUR_TOKEN_HERE placeholder"
else
    fail "run_bot.sh should contain YOUR_TOKEN_HERE"
fi

if grep -q 'PYTHONPATH' "$GOOD_DIR/run_bot.sh"; then
    fail "run_bot.sh should NOT contain PYTHONPATH"
else
    pass "run_bot.sh does not contain PYTHONPATH"
fi

if grep -q '\.\./\.\.' "$GOOD_DIR/run_bot.sh"; then
    fail "run_bot.sh should NOT contain ../../"
else
    pass "run_bot.sh does not contain ../../"
fi

if grep -q 'exec python -m telegram_bot' "$GOOD_DIR/run_bot.sh"; then
    pass "run_bot.sh has exec python -m telegram_bot"
else
    fail "run_bot.sh should have exec python -m telegram_bot"
fi

# telegram_bot.yaml checks
if [ -f "$GOOD_DIR/telegram_bot.yaml" ]; then
    pass "telegram_bot.yaml exists"
else
    fail "telegram_bot.yaml should exist"
fi

if grep -q '000000000' "$GOOD_DIR/telegram_bot.yaml"; then
    pass "telegram_bot.yaml has placeholder user ID"
else
    fail "telegram_bot.yaml should have placeholder 000000000"
fi

if grep -q '106830816' "$GOOD_DIR/telegram_bot.yaml"; then
    fail "telegram_bot.yaml should NOT contain real user ID"
else
    pass "telegram_bot.yaml does not leak real user ID"
fi

if grep -q 'idle_timeout: 600' "$GOOD_DIR/telegram_bot.yaml"; then
    pass "telegram_bot.yaml has idle_timeout: 600"
else
    fail "telegram_bot.yaml should have idle_timeout: 600"
fi

if grep -q 'shutdown_message' "$GOOD_DIR/telegram_bot.yaml"; then
    pass "telegram_bot.yaml has shutdown_message"
else
    fail "telegram_bot.yaml should have shutdown_message"
fi

if grep -q '# claude_path' "$GOOD_DIR/telegram_bot.yaml"; then
    pass "telegram_bot.yaml has commented claude_path"
else
    fail "telegram_bot.yaml should have commented claude_path"
fi

echo ""
echo "=== Test 5: Overwrite without --force ==="
if "$INSTALL_SCRIPT" "$GOOD_DIR" 2>/dev/null; then
    fail "Should exit non-zero when files exist without --force"
else
    pass "Exits non-zero without --force when files exist"
fi

echo ""
echo "=== Test 6: Overwrite with --force ==="
if "$INSTALL_SCRIPT" --force "$GOOD_DIR" 2>&1; then
    pass "Install with --force exits zero"
else
    fail "Install with --force should exit zero" "Exit code: $?"
fi

echo ""
echo "=== Test 7: Generated run_bot.sh correctness ==="
# nvm sourcing
if grep -q 'nvm.sh' "$GOOD_DIR/run_bot.sh"; then
    pass "run_bot.sh has nvm sourcing"
else
    fail "run_bot.sh should have nvm sourcing"
fi

# Token validation
if grep -q 'BOT_TOKEN.*=.*YOUR_TOKEN_HERE' "$GOOD_DIR/run_bot.sh"; then
    pass "run_bot.sh has token validation check"
else
    fail "run_bot.sh should have token validation"
fi

# PIPELINE_YAML resolution
if grep -q 'PIPELINE_YAML' "$GOOD_DIR/run_bot.sh"; then
    pass "run_bot.sh has PIPELINE_YAML handling"
else
    fail "run_bot.sh should have PIPELINE_YAML handling"
fi

# cd to SCRIPT_DIR (not ../../)
if grep -q 'cd "$SCRIPT_DIR"' "$GOOD_DIR/run_bot.sh"; then
    pass "run_bot.sh cd's to SCRIPT_DIR"
else
    fail "run_bot.sh should cd to SCRIPT_DIR"
fi

echo ""
echo "=== Test 8: Generated telegram_bot.yaml correctness ==="
# All fields present with correct defaults - already checked above
# Check the shutdown_message content
if grep -q 'Record the product of this conversation' "$GOOD_DIR/telegram_bot.yaml"; then
    pass "telegram_bot.yaml has correct shutdown_message text"
else
    fail "telegram_bot.yaml should have correct shutdown_message text"
fi

echo ""
echo "============================================"
echo "Results: $PASS passed, $FAIL failed (of $TESTS_RUN)"
echo "============================================"

if [ "$FAIL" -gt 0 ]; then
    exit 1
fi
