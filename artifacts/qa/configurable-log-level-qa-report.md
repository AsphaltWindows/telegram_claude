# QA Report: Configurable Log Level

## Metadata
- **Ticket**: configurable-log-level
- **Tested**: 2026-03-21T00:00:00Z
- **Result**: PASS (automated only)

## Steps

### Step 1: Default INFO level
- **Result**: PASS (code review + unit tests)
- **Notes**: `main()` defaults to INFO via `os.environ.get("LOG_LEVEL", "INFO")`. `test_default_log_level_is_info` confirms this. Startup log emits active level.

### Step 2: LOG_LEVEL=DEBUG
- **Result**: PASS (unit tests)
- **Notes**: `test_log_level_debug` verifies DEBUG level is correctly applied via `getattr(logging, ...)`.

### Step 3: LOG_LEVEL=WARNING
- **Result**: PASS (unit tests)
- **Notes**: `test_log_level_warning` verifies WARNING level suppresses INFO messages.

### Step 4: LOG_LEVEL=invalid
- **Result**: PASS (unit tests)
- **Notes**: `test_invalid_log_level_falls_back_to_info` and `test_invalid_log_level_logs_warning` verify fallback behavior. The `invalid_log_level` flag pattern ensures `basicConfig` is called before `logger.warning()`.

### Step 5: Case-insensitive LOG_LEVEL
- **Result**: PASS (unit tests)
- **Notes**: `test_log_level_case_insensitive` verifies `.upper()` normalization.

## Summary

All 7 tests pass. Implementation correctly handles all cases: default, valid levels, case normalization, invalid fallback with warning. Code review confirms `os` import was added and the flag-based pattern avoids calling `basicConfig` after `logger.warning()`.
