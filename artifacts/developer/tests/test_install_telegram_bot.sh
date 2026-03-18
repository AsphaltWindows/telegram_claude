#!/usr/bin/env bash
set -euo pipefail

# ============================================================
# Tests for install_telegram_bot.sh
# Run from the project root: bash artifacts/developer/tests/test_install_telegram_bot.sh
# ============================================================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)"
INSTALL_SCRIPT="$PROJECT_ROOT/install_telegram_bot.sh"
PASS=0
FAIL=0
TMPDIR_BASE=""

setup() {
    TMPDIR_BASE="$(mktemp -d)"
}

teardown() {
    if [ -n "$TMPDIR_BASE" ] && [ -d "$TMPDIR_BASE" ]; then
        rm -rf "$TMPDIR_BASE"
    fi
}

pass() {
    echo "  PASS: $1"
    PASS=$((PASS + 1))
}

fail() {
    echo "  FAIL: $1"
    FAIL=$((FAIL + 1))
}

assert_exit_nonzero() {
    local desc="$1"
    shift
    if "$@" >/dev/null 2>&1; then
        fail "$desc (expected non-zero exit)"
    else
        pass "$desc"
    fi
}

assert_file_exists() {
    if [ -f "$1" ]; then
        pass "File exists: $1"
    else
        fail "File exists: $1"
    fi
}

assert_file_not_exists() {
    if [ ! -f "$1" ] && [ ! -d "$1" ]; then
        pass "Does not exist: $1"
    else
        fail "Does not exist: $1"
    fi
}

assert_file_contains() {
    if grep -q "$2" "$1" 2>/dev/null; then
        pass "File '$1' contains '$2'"
    else
        fail "File '$1' contains '$2'"
    fi
}

assert_file_not_contains() {
    if ! grep -q "$2" "$1" 2>/dev/null; then
        pass "File '$1' does not contain '$2'"
    else
        fail "File '$1' does not contain '$2'"
    fi
}

assert_executable() {
    if [ -x "$1" ]; then
        pass "File is executable: $1"
    else
        fail "File is executable: $1"
    fi
}

# ==============================================================
# Test 1: No arguments — prints usage and exits non-zero
# ==============================================================
echo "Test 1: No arguments"
assert_exit_nonzero "exits non-zero with no args" "$INSTALL_SCRIPT"

# Verify it prints usage
output=$("$INSTALL_SCRIPT" 2>&1 || true)
if echo "$output" | grep -qi "usage"; then
    pass "prints usage message"
else
    fail "prints usage message"
fi

# ==============================================================
# Test 2: Non-existent directory
# ==============================================================
echo "Test 2: Non-existent directory"
assert_exit_nonzero "exits non-zero for missing dir" "$INSTALL_SCRIPT" "/nonexistent/path/xyz"

output=$("$INSTALL_SCRIPT" "/nonexistent/path/xyz" 2>&1 || true)
if echo "$output" | grep -qi "not a directory\|does not exist"; then
    pass "prints directory error message"
else
    fail "prints directory error message"
fi

# ==============================================================
# Test 3: Directory without pipeline.yaml
# ==============================================================
echo "Test 3: Directory without pipeline.yaml"
setup
mkdir -p "$TMPDIR_BASE/no_pipeline"
assert_exit_nonzero "exits non-zero without pipeline.yaml" "$INSTALL_SCRIPT" "$TMPDIR_BASE/no_pipeline"

output=$("$INSTALL_SCRIPT" "$TMPDIR_BASE/no_pipeline" 2>&1 || true)
if echo "$output" | grep -qi "pipeline.yaml"; then
    pass "prints pipeline.yaml error"
else
    fail "prints pipeline.yaml error"
fi
teardown

# ==============================================================
# Test 4: Successful install to a valid target
# ==============================================================
echo "Test 4: Successful install"
setup
TARGET="$TMPDIR_BASE/test_project"
mkdir -p "$TARGET"
touch "$TARGET/pipeline.yaml"

# Run installer (skip pip install by mocking - we just capture output)
output=$("$INSTALL_SCRIPT" "$TARGET" 2>&1 || true)

# 4a: telegram_bot/ directory created with .py files
echo "  4a: Python files copied"
assert_file_exists "$TARGET/telegram_bot/__init__.py"
assert_file_exists "$TARGET/telegram_bot/__main__.py"
assert_file_exists "$TARGET/telegram_bot/bot.py"
assert_file_exists "$TARGET/telegram_bot/config.py"
assert_file_exists "$TARGET/telegram_bot/discovery.py"
assert_file_exists "$TARGET/telegram_bot/session.py"

# 4b: No __pycache__ copied
echo "  4b: No __pycache__"
assert_file_not_exists "$TARGET/telegram_bot/__pycache__"

# 4c: No tests/ copied
echo "  4c: No tests/ directory"
assert_file_not_exists "$TARGET/telegram_bot/tests"
assert_file_not_exists "$TARGET/tests"

# 4d: No requirements.txt copied
echo "  4d: No requirements.txt"
assert_file_not_exists "$TARGET/requirements.txt"

# 4e: run_bot.sh exists and is executable
echo "  4e: run_bot.sh"
assert_file_exists "$TARGET/run_bot.sh"
assert_executable "$TARGET/run_bot.sh"

# 4f: run_bot.sh has placeholder token, NOT real token
echo "  4f: Token replacement"
assert_file_contains "$TARGET/run_bot.sh" 'BOT_TOKEN="YOUR_TOKEN_HERE"'
assert_file_not_contains "$TARGET/run_bot.sh" '8727225239'
assert_file_not_contains "$TARGET/run_bot.sh" 'AAFBEyRFy8gwm_QdpRiyL3YWj4VIjn2_iI8'

# 4g: run_bot.sh has corrected cd logic
echo "  4g: cd logic"
assert_file_contains "$TARGET/run_bot.sh" 'cd "$SCRIPT_DIR"'
assert_file_not_contains "$TARGET/run_bot.sh" 'cd "$SCRIPT_DIR/../.."'

# 4h: run_bot.sh has no PYTHONPATH export
echo "  4h: PYTHONPATH removed"
assert_file_not_contains "$TARGET/run_bot.sh" 'export PYTHONPATH='

# 4i: telegram_bot.yaml exists with placeholder user ID
echo "  4i: telegram_bot.yaml"
assert_file_exists "$TARGET/telegram_bot.yaml"
assert_file_contains "$TARGET/telegram_bot.yaml" '000000000'
assert_file_not_contains "$TARGET/telegram_bot.yaml" '106830816'

# 4j: Post-install message
echo "  4j: Post-install message"
if echo "$output" | grep -q "Next steps"; then
    pass "prints next-steps message"
else
    fail "prints next-steps message"
fi

# ==============================================================
# Test 5: Overwrite warning on second run
# ==============================================================
echo "Test 5: Overwrite warning on re-run"
output=$("$INSTALL_SCRIPT" "$TARGET" 2>&1 || true)
if echo "$output" | grep -qi "already exists\|overwrite"; then
    pass "prints overwrite warning"
else
    fail "prints overwrite warning"
fi

teardown

# ==============================================================
# Test 6: Script has proper shebang
# ==============================================================
echo "Test 6: Shebang and executability"
assert_executable "$INSTALL_SCRIPT"
first_line=$(head -1 "$INSTALL_SCRIPT")
if [[ "$first_line" == "#!/usr/bin/env bash" ]] || [[ "$first_line" == "#!/bin/bash" ]]; then
    pass "has proper shebang: $first_line"
else
    fail "has proper shebang (got: $first_line)"
fi

# ==============================================================
# Summary
# ==============================================================
echo ""
echo "============================================================"
echo "Results: $PASS passed, $FAIL failed"
echo "============================================================"

if [ "$FAIL" -gt 0 ]; then
    exit 1
fi
