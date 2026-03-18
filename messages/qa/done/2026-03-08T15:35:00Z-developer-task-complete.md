# Telegram Bot: Agent Discovery from pipeline.yaml

## Metadata
- **From**: developer
- **To**: qa
- **Type**: task-complete
- **Created**: 2026-03-08T15:35:00Z

## Summary of Changes

Implemented the `discover_source_agents()` function in `telegram_bot/discovery.py`. This module reads `pipeline.yaml`, extracts all agents with `type: source`, and returns their names as a list of strings. It follows the same patterns established by `config.py` (project root resolution, YAML safe loading, clear error messages).

## Files Changed

- `artifacts/developer/telegram_bot/discovery.py` — New module implementing `discover_source_agents()` with full error handling and path resolution
- `artifacts/developer/telegram_bot/tests/__init__.py` — Package init for the tests directory
- `artifacts/developer/telegram_bot/tests/test_discovery.py` — 12 test cases covering happy paths, edge cases, and error conditions

## Requirements Addressed

1. ✅ Created `telegram_bot/discovery.py` that reads `pipeline.yaml` from the project root
2. ✅ Extracts all agents with `type: source` and returns their names as a list of strings
3. ✅ Agents with `scheduled: false` are included (tested explicitly)
4. ✅ Returns `list[str]` (e.g., `["operator", "architect", "designer"]`)
5. ✅ Raises `FileNotFoundError` if file missing; `ValueError` if unparseable or bad structure
6. ✅ Returns empty list if no source agents found (does not error)

## QA Steps

1. With the existing `pipeline.yaml` in the project, run discovery and verify it returns all source agents (`operator`, `architect`, `designer`)
2. Create a test `pipeline.yaml` with a mix of source and non-source agents; verify only source agents are returned
3. Create a test `pipeline.yaml` with a source agent that has `scheduled: false`; verify it is still included
4. Remove `pipeline.yaml` and verify a clear error is raised
5. Create a `pipeline.yaml` with no source agents; verify an empty list is returned

## Test Coverage

All QA steps are covered by automated tests in `telegram_bot/tests/test_discovery.py`. Run with:

```
cd artifacts/developer && python -m pytest telegram_bot/tests/test_discovery.py -v
```

Test classes:
- `TestDiscoverSourceAgents` — 6 tests: source-only filtering, scheduled:false inclusion, empty list cases, string path acceptance, real pipeline.yaml integration
- `TestDiscoverSourceAgentsErrors` — 6 tests: file not found, invalid YAML, empty file, missing agents key, agents not a list, malformed entries

Result: 11 passed, 1 skipped (integration test skips when pipeline.yaml not at default location).

## Notes

- Followed patterns from existing `config.py`: `__future__` annotations, `_PROJECT_ROOT` resolution via `Path(__file__)`, `yaml.safe_load`, explicit error messages.
- The function accepts `Path`, `str`, or `None` for the pipeline path, making it flexible for both production use and testing.
- Malformed entries in the agents list (non-dict items) are silently skipped rather than raising errors, providing resilience against partially broken configs.
