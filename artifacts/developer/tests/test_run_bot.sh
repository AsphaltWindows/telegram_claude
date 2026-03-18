#!/usr/bin/env bash
set -euo pipefail

# Test suite for run_bot.sh
# Uses a copy of the script with the exec line replaced to avoid actually starting the bot.

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
SCRIPT_UNDER_TEST="$PROJECT_ROOT/run_bot.sh"

PASS=0
FAIL=0
TEMP_DIR=""

setup() {
    TEMP_DIR="$(mktemp -d)"
    # Copy the script to a temp directory to test isolation
    cp "$SCRIPT_UNDER_TEST" "$TEMP_DIR/run_bot.sh"
    chmod +x "$TEMP_DIR/run_bot.sh"
    # Replace exec line with echo so we don't actually start the bot
    sed -i 's|^exec python -m telegram_bot|echo "WOULD_START_BOT"|' "$TEMP_DIR/run_bot.sh"
    # Create a dummy pipeline.yaml
    touch "$TEMP_DIR/pipeline.yaml"
}

teardown() {
    if [ -n "$TEMP_DIR" ] && [ -d "$TEMP_DIR" ]; then
        rm -rf "$TEMP_DIR"
    fi
}

assert_exit_code() {
    local expected="$1"
    local actual="$2"
    local test_name="$3"
    if [ "$actual" -eq "$expected" ]; then
        echo "PASS: $test_name"
        PASS=$((PASS + 1))
    else
        echo "FAIL: $test_name (expected exit $expected, got $actual)"
        FAIL=$((FAIL + 1))
    fi
}

assert_output_contains() {
    local expected="$1"
    local output="$2"
    local test_name="$3"
    if echo "$output" | grep -q "$expected"; then
        echo "PASS: $test_name"
        PASS=$((PASS + 1))
    else
        echo "FAIL: $test_name (expected output to contain '$expected')"
        echo "  Actual output: $output"
        FAIL=$((FAIL + 1))
    fi
}

# -------------------------------------------------------
# Test 1: Refuses to start with placeholder BOT_TOKEN
# -------------------------------------------------------
test_placeholder_token_rejected() {
    setup
    local output
    output="$(bash "$TEMP_DIR/run_bot.sh" 2>&1)" && local rc=$? || local rc=$?
    assert_exit_code 1 "$rc" "placeholder token: exits with code 1"
    assert_output_contains "BOT_TOKEN" "$output" "placeholder token: error mentions BOT_TOKEN"
    teardown
}

# -------------------------------------------------------
# Test 2: Refuses to start if PIPELINE_YAML file missing
# -------------------------------------------------------
test_missing_pipeline_yaml() {
    setup
    # Set a real token
    sed -i 's|BOT_TOKEN="YOUR_TOKEN_HERE"|BOT_TOKEN="test-token-12345"|' "$TEMP_DIR/run_bot.sh"
    # Point to nonexistent file
    sed -i 's|PIPELINE_YAML="pipeline.yaml"|PIPELINE_YAML="nonexistent.yaml"|' "$TEMP_DIR/run_bot.sh"
    local output
    output="$(bash "$TEMP_DIR/run_bot.sh" 2>&1)" && local rc=$? || local rc=$?
    assert_exit_code 1 "$rc" "missing pipeline yaml: exits with code 1"
    assert_output_contains "nonexistent.yaml" "$output" "missing pipeline yaml: error includes file path"
    teardown
}

# -------------------------------------------------------
# Test 3: Succeeds with valid token and pipeline file
# -------------------------------------------------------
test_successful_start() {
    setup
    # Set a real token
    sed -i 's|BOT_TOKEN="YOUR_TOKEN_HERE"|BOT_TOKEN="test-token-12345"|' "$TEMP_DIR/run_bot.sh"
    local output
    output="$(bash "$TEMP_DIR/run_bot.sh" 2>&1)" && local rc=$? || local rc=$?
    assert_exit_code 0 "$rc" "successful start: exits with code 0"
    assert_output_contains "WOULD_START_BOT" "$output" "successful start: reaches exec command"
    teardown
}

# -------------------------------------------------------
# Test 4: Works from a different working directory
# -------------------------------------------------------
test_different_working_directory() {
    setup
    sed -i 's|BOT_TOKEN="YOUR_TOKEN_HERE"|BOT_TOKEN="test-token-12345"|' "$TEMP_DIR/run_bot.sh"
    local output
    output="$(cd /tmp && bash "$TEMP_DIR/run_bot.sh" 2>&1)" && local rc=$? || local rc=$?
    assert_exit_code 0 "$rc" "different cwd: exits with code 0"
    assert_output_contains "WOULD_START_BOT" "$output" "different cwd: reaches exec command"
    teardown
}

# -------------------------------------------------------
# Test 5: Custom relative PIPELINE_YAML path works
# -------------------------------------------------------
test_custom_pipeline_path() {
    setup
    sed -i 's|BOT_TOKEN="YOUR_TOKEN_HERE"|BOT_TOKEN="test-token-12345"|' "$TEMP_DIR/run_bot.sh"
    mkdir -p "$TEMP_DIR/config"
    touch "$TEMP_DIR/config/my-pipeline.yaml"
    sed -i 's|PIPELINE_YAML="pipeline.yaml"|PIPELINE_YAML="config/my-pipeline.yaml"|' "$TEMP_DIR/run_bot.sh"
    local output
    output="$(bash "$TEMP_DIR/run_bot.sh" 2>&1)" && local rc=$? || local rc=$?
    assert_exit_code 0 "$rc" "custom pipeline path: exits with code 0"
    assert_output_contains "WOULD_START_BOT" "$output" "custom pipeline path: reaches exec command"
    teardown
}

# -------------------------------------------------------
# Test 6: Script has executable permission
# -------------------------------------------------------
test_executable_permission() {
    if [ -x "$SCRIPT_UNDER_TEST" ]; then
        echo "PASS: script has executable permission"
        PASS=$((PASS + 1))
    else
        echo "FAIL: script does not have executable permission"
        FAIL=$((FAIL + 1))
    fi
}

# -------------------------------------------------------
# Test 7: PIPELINE_YAML is resolved to absolute path
# -------------------------------------------------------
test_pipeline_yaml_resolved_absolute() {
    setup
    sed -i 's|BOT_TOKEN="YOUR_TOKEN_HERE"|BOT_TOKEN="test-token-12345"|' "$TEMP_DIR/run_bot.sh"
    # Replace the exec line to print the PIPELINE_YAML value instead
    sed -i 's|echo "WOULD_START_BOT"|echo "PIPELINE_YAML=$PIPELINE_YAML"|' "$TEMP_DIR/run_bot.sh"
    local output
    output="$(bash "$TEMP_DIR/run_bot.sh" 2>&1)" && local rc=$? || local rc=$?
    # Check that the exported path starts with /
    local pipeline_val
    pipeline_val="$(echo "$output" | grep 'PIPELINE_YAML=' | sed 's/PIPELINE_YAML=//')"
    if [[ "$pipeline_val" == /* ]]; then
        echo "PASS: PIPELINE_YAML is resolved to absolute path ($pipeline_val)"
        PASS=$((PASS + 1))
    else
        echo "FAIL: PIPELINE_YAML is not absolute ($pipeline_val)"
        FAIL=$((FAIL + 1))
    fi
    teardown
}

# Run all tests
echo "=== run_bot.sh Test Suite ==="
echo ""
test_placeholder_token_rejected
test_missing_pipeline_yaml
test_successful_start
test_different_working_directory
test_custom_pipeline_path
test_executable_permission
test_pipeline_yaml_resolved_absolute
echo ""
echo "=== Results: $PASS passed, $FAIL failed ==="

if [ "$FAIL" -gt 0 ]; then
    exit 1
fi
