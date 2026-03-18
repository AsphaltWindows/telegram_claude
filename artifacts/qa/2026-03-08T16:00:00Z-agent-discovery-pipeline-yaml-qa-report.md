# QA Report: Telegram Bot Agent Discovery from pipeline.yaml

## Metadata
- **Ticket**: Agent Discovery from pipeline.yaml
- **Tested**: 2026-03-08T16:00:00Z
- **Result**: PASS

## Steps

### Step 1: Run discovery against existing pipeline.yaml and verify source agents
- **Result**: PASS
- **Notes**: `discover_source_agents('/home/iv/dev/telegram_claude/pipeline.yaml')` returned `['operator', 'architect', 'designer']` — matches the three source agents defined in `pipeline.yaml`.

### Step 2: Mix of source and non-source agents returns only source agents
- **Result**: PASS
- **Notes**: Covered by `test_returns_source_agents_only` — a pipeline with alpha(source), beta(processing), gamma(sink), delta(source) correctly returns `["alpha", "delta"]`.

### Step 3: Source agent with `scheduled: false` is still included
- **Result**: PASS
- **Notes**: Covered by `test_includes_scheduled_false_agents` — operator(source, scheduled=false) and designer(source) both returned. Also confirmed against real pipeline.yaml where operator has `scheduled: false`.

### Step 4: Missing pipeline.yaml raises a clear error
- **Result**: PASS
- **Notes**: Covered by `test_raises_file_not_found_when_missing` — raises `FileNotFoundError` with message containing "not found".

### Step 5: No source agents returns empty list
- **Result**: PASS
- **Notes**: Covered by `test_returns_empty_list_when_no_source_agents` and `test_returns_empty_list_when_agents_list_is_empty` — both return `[]` without error.

## Summary

All 5 QA steps pass. The implementation is clean, well-documented, and follows established project patterns. Test coverage is thorough with 12 test cases (11 passed, 1 skipped due to path resolution in the test environment — verified manually). Error handling covers all specified edge cases. The integration test against the real `pipeline.yaml` confirms correct behavior in production context.

Note: The `_PROJECT_ROOT` in discovery.py resolves relative to `artifacts/developer/`, which is correct for the current artifact structure. When this module is moved to its final location in the project, the path resolution will need to be adjusted accordingly.
