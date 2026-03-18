# QA Report: Add configurable claude_path config option and nvm sourcing in run_bot.sh

## Metadata
- **Ticket**: Add configurable claude_path config option and nvm sourcing in run_bot.sh
- **Tested**: 2026-03-09T01:45:00Z
- **Result**: PASS (automated checks only; manual integration steps require user validation)

## Steps

### Step 1: Set claude_path in config and verify it's used for version check and session spawning
- **Result**: PASS (code review)
- **Notes**: `main()` loads config early, passes `config.claude_path or "claude"` to `_check_claude_cli()`. `build_application()` passes `claude_command=config.claude_path or "claude"` to `SessionManager`. `SessionManager` uses `self._claude_command` in `create_subprocess_exec`. Test `test_start_session_uses_custom_claude_command` confirms `/opt/bin/claude` is used as positional arg. Test `test_custom_command_path` confirms `_check_claude_cli` uses the custom path. Requires manual validation with a real claude binary.

### Step 2: Leave claude_path unset and verify fallback to bare claude
- **Result**: PASS (code review + unit tests)
- **Notes**: `config.claude_path or "claude"` resolves to `"claude"` when `claude_path` is `None`. Tests `test_claude_path_default_is_none`, `test_claude_path_absent_is_none`, and `test_start_session_defaults_to_claude` all confirm the fallback behavior.

### Step 3: Set claude_path to non-existent path and verify fail-fast
- **Result**: PASS (code review + unit tests)
- **Notes**: `_check_claude_cli()` catches `FileNotFoundError` and calls `sys.exit(1)` with a descriptive log message including the command path. Test `test_file_not_found_exits` and `test_file_not_found_logs_descriptive_message` confirm this behavior.

### Step 4: Set claude_path to non-executable file and verify fail-fast
- **Result**: PASS (code review + unit tests)
- **Notes**: `_check_claude_cli()` catches `OSError` (which includes `PermissionError`) and calls `sys.exit(1)`. Test `test_os_error_exits` confirms this. Requires manual validation for the exact error message wording.

### Step 5: Verify nvm sourcing in run_bot.sh with valid NVM_DIR
- **Result**: PASS (code review)
- **Notes**: `run_bot.sh` sources `${NVM_DIR:-$HOME/.nvm}/nvm.sh` with a `-s` guard (file exists and has size > 0). The sourcing happens after `cd` and before token validation, which is the correct ordering. Requires manual validation on a system with nvm installed.

### Step 6: Verify run_bot.sh doesn't error with invalid/unset NVM_DIR
- **Result**: PASS (code review)
- **Notes**: The `if [ -s ... ]` guard ensures the source command only runs if the file exists. If NVM_DIR is unset, it falls back to `$HOME/.nvm/nvm.sh`. If that doesn't exist either, the block is skipped entirely. The script will not error. Requires manual validation.

### Step 7: Test full flow from clean systemd service
- **Result**: NOT TESTED (requires manual integration test)
- **Notes**: This step requires a systemd service environment where .bashrc is not sourced. Code review confirms the approach is correct: nvm is sourced early in run_bot.sh, and if claude_path is set, nvm sourcing is not even needed for finding claude.

## Test Coverage

All 133 tests pass (1 skipped — `test_with_real_pipeline_yaml` which requires a real pipeline file). The task-complete message reported 122 tests; the actual count is 133, suggesting additional tests were added by other changes.

New tests verified:
- `test_claude_path_default_is_none` - PASS
- `test_claude_path_loaded_from_yaml` - PASS
- `test_claude_path_absent_is_none` - PASS
- `test_empty_claude_path_raises` - PASS
- `test_non_string_claude_path_raises` - PASS
- `test_start_session_uses_custom_claude_command` - PASS
- `test_start_session_defaults_to_claude` - PASS
- `test_file_not_found_logs_descriptive_message` - PASS

## Summary

The implementation is solid. All automated checks pass. The code correctly:
1. Adds `claude_path` as an optional config field with proper validation (rejects empty strings, non-strings)
2. Threads `claude_path` through config -> bot -> session manager -> subprocess exec
3. Falls back to bare `"claude"` when unset
4. Fails fast at startup via `_check_claude_cli()` with descriptive error messages
5. Guards nvm sourcing in `run_bot.sh` so it's safe when nvm is absent
6. Documents the option in `telegram_bot.yaml` with a commented-out example

QA steps 1, 5, 6, and 7 require manual integration testing with a real environment (nvm, systemd, actual claude binary). The code review and unit tests give high confidence these will pass. No issues found.
