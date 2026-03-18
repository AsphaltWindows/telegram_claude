# QA Report: Fix wrong subprocess working directory — use Path.cwd() instead of __file__ path arithmetic

## Metadata
- **Ticket**: Fix wrong subprocess working directory — use Path.cwd() instead of __file__ path arithmetic
- **Tested**: 2026-03-09T03:30:00Z
- **Result**: PASS

## Steps

### Step 1: Code review — _PROJECT_ROOT replaced with Path.cwd() in all three modules
- **Result**: PASS
- **Notes**: Verified `session.py`, `config.py`, and `discovery.py` all set `_PROJECT_ROOT = Path.cwd()` with correct comments explaining the launcher script contract. No residual `__file__`-based path arithmetic remains.

### Step 2: Code review — configurable project_root in BotConfig
- **Result**: PASS
- **Notes**: `config.py` adds `project_root: Optional[Path] = None` to `BotConfig`. `load_config()` parses it from YAML, validates it's a non-empty string pointing to an existing directory, and raises `ValueError` on invalid input.

### Step 3: Code review — bot.py wiring of project_root to SessionManager
- **Result**: PASS
- **Notes**: `build_application()` passes `project_root=config.project_root` to the `SessionManager` constructor. When `None`, `SessionManager` falls back to `_PROJECT_ROOT` (which is `Path.cwd()`).

### Step 4: Code review — subprocess cwd uses project_root
- **Result**: PASS
- **Notes**: `SessionManager.start_session()` passes `cwd=str(self._project_root)` to `asyncio.create_subprocess_exec()`. The `_project_root` is set to either the explicit config value or `Path.cwd()`.

### Step 5: Automated tests — 13 new tests all pass
- **Result**: PASS
- **Notes**: All 13 new tests in `test_project_root.py` pass. Tests cover: `_PROJECT_ROOT == Path.cwd()` in all three modules, reload-in-temp-dir proof that it follows cwd, `SessionManager` default and override behavior, subprocess `cwd` kwarg verification, config parsing (default None, from YAML, invalid directory, empty string), and `build_application` wiring (both set and None).

### Step 6: Full regression suite — 74 tests pass
- **Result**: PASS
- **Notes**: All 74 tests (61 existing + 13 new) pass with no regressions.

## Summary

All automated QA steps pass. The implementation correctly replaces the fragile `Path(__file__).resolve().parent.parent` computation with `Path.cwd()` across all three modules, adds a configurable `project_root` option in `BotConfig` with proper validation, and wires it through `bot.py` to `SessionManager`. Test coverage is thorough with 13 new tests covering all change vectors.

The remaining QA steps (1–5 from the ticket) are manual integration tests requiring a running bot instance and cannot be automated here. The code-level correctness is verified — the subprocess `cwd` kwarg will correctly receive either the configured `project_root` or `Path.cwd()`.
