# Add configurable claude_path config option and nvm sourcing in run_bot.sh

## Metadata
- **From**: task_planner
- **To**: developer
- **Type**: enriched-ticket
- **Created**: 2026-03-09T01:11:00Z

## Requirements

1. Add an optional `claude_path` field to the `telegram_bot.yaml` configuration spec. When set, the bot must use this path instead of bare `claude` for all subprocess invocations (both the pre-flight version check and `SessionManager.start_session()`).
2. When `claude_path` is unset or empty, the bot must fall back to resolving `claude` from PATH (current behavior).
3. If `claude_path` is set but the specified file does not exist or is not executable, the pre-flight check (from the related ticket) should catch this and fail fast with a clear error message.
4. Update `run_bot.sh` (the launcher script) to source `$NVM_DIR/nvm.sh` if the file exists, before launching the bot process. This ensures that nvm-managed Node.js and npm-installed binaries (including `claude`) are available on PATH even when invoked from systemd or cron.
5. The nvm sourcing in `run_bot.sh` must be guarded: only source if `$NVM_DIR/nvm.sh` exists, and do not fail if it doesn't (not all deployments use nvm).
6. Document the `claude_path` option in any existing config documentation or example config files with a comment explaining when and why to use it.

## QA Steps

1. Set `claude_path` in `telegram_bot.yaml` to the full path of the `claude` binary (e.g., `/home/user/.nvm/versions/node/v22.x/bin/claude`). Start the bot and verify it uses that path for the version check and session spawning.
2. Leave `claude_path` unset in config. Verify the bot falls back to bare `claude` from PATH and works normally.
3. Set `claude_path` to a non-existent path. Verify the bot fails fast at startup with a clear error message.
4. Set `claude_path` to a file that exists but is not executable. Verify the bot fails with a clear error.
5. In `run_bot.sh`, set `NVM_DIR` to a valid nvm installation directory and verify that after sourcing, `node` and `claude` are on PATH.
6. In `run_bot.sh`, unset `NVM_DIR` or point it to a non-existent directory. Verify the script does not error and the bot still attempts to start.
7. Test the full flow from a clean systemd service (where .bashrc is not sourced): verify that `run_bot.sh` correctly initializes nvm and the bot can find and run `claude`.

## Technical Context

### Relevant Files

| File | Purpose |
|---|---|
| `artifacts/developer/telegram_bot/config.py` | **Primary target.** Must add `claude_path: Optional[str]` to `BotConfig` dataclass (line 28) and parse it from YAML in `load_config()` (line 38). |
| `artifacts/developer/telegram_bot/session.py` | **Primary target.** `SessionManager.start_session()` (line 449) hardcodes `"claude"` as the executable in `create_subprocess_exec` (line 484). Must accept and use the configured claude_path. `SessionManager.__init__` (line 434) needs a new `claude_command` parameter. |
| `artifacts/developer/telegram_bot/bot.py` | Must pass `claude_path` from config to `SessionManager` in `build_application()` (line 334). If the pre-flight check from the companion ticket is already implemented, it also needs to use claude_path. |
| `artifacts/developer/run_bot.sh` | **Primary target.** Must add nvm sourcing block before the `exec python` line (currently line 38). |
| `artifacts/developer/telegram_bot.yaml` | Must add commented-out `claude_path` example with documentation comment. |

### Patterns and Conventions

- **Config dataclass**: `BotConfig` at config.py line 28 uses `@dataclass` with typed fields. Optional fields use defaults (see `idle_timeout` and `shutdown_message`). Follow the same pattern for `claude_path` with `Optional[str] = None`.
- **YAML parsing**: `load_config()` reads fields with `data.get("key", default)`. Optional fields don't raise on absence. Follow this pattern.
- **run_bot.sh style**: Uses `set -euo pipefail`, validates config before starting. Consistent comment style with `# ====` section headers.
- **SessionManager constructor**: Takes `idle_timeout`, `shutdown_message`, `project_root` — add `claude_command: str = "claude"` following the same pattern.

### Dependencies and Integration Points

1. **SessionManager ↔ config**: Currently `SessionManager` doesn't know about config — it receives individual settings as constructor args. Add `claude_command: str = "claude"` to `__init__` and use it in `start_session()` at line 484 where `"claude"` is hardcoded.

2. **Pre-flight check (companion ticket)**: If the pre-flight check from the companion ticket (`2026-03-09T01:10:00Z`) is implemented first, it will also need to use `claude_path`. If implementing this ticket second, update the pre-flight check to use `config.claude_path or "claude"`. If implementing first, the pre-flight check ticket can use bare `"claude"` and this ticket will update it.

3. **`create_subprocess_exec` call**: At session.py line 484, the first arg is the executable. Change from `"claude"` to `self._claude_command`. The rest of the args stay the same.

### Implementation Notes

**Part 1: Config changes (config.py)**

1. Add to `BotConfig`:
   ```python
   claude_path: Optional[str] = None
   ```
2. In `load_config()`, after the existing optional fields block (~line 103):
   ```python
   claude_path = data.get("claude_path")
   if claude_path is not None:
       if not isinstance(claude_path, str) or not claude_path.strip():
           raise ValueError("claude_path must be a non-empty string if set.")
   ```
3. Pass `claude_path=claude_path` to the `BotConfig` constructor.

**Part 2: SessionManager changes (session.py)**

1. Add `claude_command: str = "claude"` parameter to `SessionManager.__init__` and store as `self._claude_command`.
2. In `start_session()` at line 484, replace the hardcoded `"claude"` with `self._claude_command`.

**Part 3: Bot wiring (bot.py)**

1. In `build_application()` at line 334, pass the claude command to SessionManager:
   ```python
   claude_command=config.claude_path or "claude",
   ```

**Part 4: run_bot.sh nvm sourcing**

Add this block after the `cd` line (line 14) and before the token validation (line 17):

```bash
# Source nvm if available — needed when running from systemd/cron
# where the user's shell profile isn't loaded
if [ -s "${NVM_DIR:-$HOME/.nvm}/nvm.sh" ]; then
    source "${NVM_DIR:-$HOME/.nvm}/nvm.sh"
fi
```

**Part 5: telegram_bot.yaml documentation**

Add the commented-out `claude_path` example to the existing `telegram_bot.yaml` file, matching the format shown in the design doc.

**Ordering**: Implement config.py first, then session.py, then bot.py, then run_bot.sh and telegram_bot.yaml. This minimizes the chance of broken intermediate states.

## Design Context

When the bot runs as a systemd service or cron job, the user's shell profile (which initializes nvm) is not sourced, so `claude` may not be on PATH. This ticket provides two complementary mitigations: (1) a configurable `claude_path` that bypasses PATH resolution entirely, and (2) nvm sourcing in the launcher script for users who prefer the default PATH-based resolution. See `artifacts/designer/design.md`, sections "Subprocess Environment" and the `telegram_bot.yaml` config spec.
